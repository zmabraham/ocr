"""Document upload and management routes"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
import uuid
import os
from datetime import datetime

from ..database import get_db
from ..models import Document, ErrorRecord
from config import settings

# OCR processor (optional - may not be available in all deployments)
import logging
logger = logging.getLogger(__name__)

try:
    from ocr_pipeline import OCRProcessor
    OCR_AVAILABLE = True
    logger.info("OCR processor loaded successfully")
except Exception as e:
    OCR_AVAILABLE = False
    OCRProcessor = None
    logger.error(f"Failed to import OCR processor: {e}")

# ML imports (optional - may not be available in all deployments)
try:
    from ai_analysis import DictaBERTAnalyzer, CorrectionSuggester
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False
    DictaBERTAnalyzer = None
    CorrectionSuggester = None

router = APIRouter()

# Initialize processors (lazy initialization)
_ocr_processor = None
_dicta_analyzer = None
_correction_suggester = None


def get_ocr_processor():
    """Get or create OCR processor (lazy initialization)"""
    global _ocr_processor
    if _ocr_processor is None and OCR_AVAILABLE:
        _ocr_processor = OCRProcessor()
    return _ocr_processor


def get_dicta_analyzer():
    """Get or create DictaBERT analyzer (lazy initialization)"""
    global _dicta_analyzer
    if _dicta_analyzer is None and ML_AVAILABLE:
        _dicta_analyzer = DictaBERTAnalyzer()
    return _dicta_analyzer


def get_correction_suggester():
    """Get or create correction suggester (lazy initialization)"""
    global _correction_suggester
    if _correction_suggester is None and ML_AVAILABLE:
        _correction_suggester = CorrectionSuggester()
    return _correction_suggester


@router.post("/upload", response_model=dict)
async def upload_document(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db)
):
    """Upload a PDF document for OCR processing (streaming for large files)"""
    # Validate file type
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    # Generate document ID
    doc_id = str(uuid.uuid4())
    upload_path = os.path.join(settings.UPLOAD_DIR, f"{doc_id}.pdf")

    # Ensure upload directory exists
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

    # Stream file to disk (better for large files - avoids loading all into memory)
    size = 0
    chunk_size = 1024 * 1024  # 1MB chunks
    try:
        with open(upload_path, "wb") as f:
            while True:
                chunk = await file.read(chunk_size)
                if not chunk:
                    break
                size += len(chunk)
                if size > settings.MAX_FILE_SIZE:
                    # Remove partial file
                    if os.path.exists(upload_path):
                        os.remove(upload_path)
                    raise HTTPException(
                        status_code=400,
                        detail=f"File too large (max {settings.MAX_FILE_SIZE // (1024*1024)}MB)"
                    )
                f.write(chunk)
    except Exception as e:
        # Clean up on error
        if os.path.exists(upload_path):
            os.remove(upload_path)
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

    # Create document record
    document = Document(
        id=doc_id,
        filename=file.filename,
        original_path=upload_path,
        status="pending"
    )
    db.add(document)
    db.commit()

    # Queue OCR processing
    if background_tasks:
        background_tasks.add_task(process_document, doc_id, db)

    # Calculate estimated processing time
    size_mb = size / (1024 * 1024)
    estimated_minutes = max(3, (size_mb // 2) + 2)  # ~2MB/min + 2min overhead

    return {
        "document_id": doc_id,
        "filename": file.filename,
        "status": "pending",
        "size_bytes": size,
        "message": "Document uploaded successfully. OCR processing started.",
        "estimated_time_minutes": estimated_minutes,
        "is_large_file": size_mb > 10
    }


@router.post("/upload/chunked", response_model=dict)
async def upload_chunked_document(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db),
    chunk_index: int = 0,
    total_chunks: int = 1,
    upload_id: str = None
):
    """
    Upload document in chunks (for large files or unstable connections)

    Usage:
    1. Call with first chunk to get upload_id
    2. Subsequent chunks use the same upload_id
    3. After last chunk, document is queued for OCR
    """
    # Validate file type
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    # Generate or use upload ID
    if upload_id is None:
        upload_id = str(uuid.uuid4())

    upload_path = os.path.join(settings.UPLOAD_DIR, f"{upload_id}.pdf")
    chunk_path = os.path.join(settings.UPLOAD_DIR, f"{upload_id}.part{chunk_index}")

    # Ensure upload directory exists
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

    # Save chunk
    size = 0
    try:
        with open(chunk_path, "wb") as f:
            content = await file.read()
            size = len(content)
            if size > settings.MAX_FILE_SIZE:
                raise HTTPException(status_code=400, detail="File too large")
            f.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chunk upload failed: {str(e)}")

    # If this is the last chunk, combine all parts
    if chunk_index == total_chunks - 1:
        try:
            # Combine all chunks
            with open(upload_path, "wb") as f:
                for i in range(total_chunks):
                    part_path = os.path.join(settings.UPLOAD_DIR, f"{upload_id}.part{i}")
                    with open(part_path, "rb") as part:
                        f.write(part.read())
                    os.remove(part_path)  # Clean up chunk files

            # Create document record
            doc_id = str(uuid.uuid4())
            document = Document(
                id=doc_id,
                filename=file.filename,
                original_path=upload_path,
                status="pending"
            )
            db.add(document)
            db.commit()

            # Queue OCR processing
            if background_tasks:
                background_tasks.add_task(process_document, doc_id, db)

            size_mb = size / (1024 * 1024)
            estimated_minutes = max(3, (size_mb // 2) + 2)

            return {
                "document_id": doc_id,
                "upload_id": upload_id,
                "filename": file.filename,
                "status": "pending",
                "size_bytes": size,
                "chunk_index": chunk_index,
                "total_chunks": total_chunks,
                "is_complete": True,
                "estimated_time_minutes": estimated_minutes,
                "is_large_file": size_mb > 10,
                "message": "All chunks received. OCR processing started."
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to combine chunks: {str(e)}")
    else:
        # Not the last chunk
        return {
            "upload_id": upload_id,
            "chunk_index": chunk_index,
            "total_chunks": total_chunks,
            "is_complete": False,
            "message": f"Chunk {chunk_index + 1} of {total_chunks} received. Send next chunk."
        }


@router.get("/{document_id}", response_model=dict)
async def get_document(document_id: str, db: Session = Depends(get_db)):
    """Get document details and progress"""
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    return {
        "id": document.id,
        "filename": document.filename,
        "status": document.status,
        "upload_date": document.upload_date.isoformat(),
        "total_pages": document.total_pages,
        "processed_pages": document.processed_pages,
        "progress_percentage": document.progress_percentage,
        "overall_confidence": document.overall_confidence,
        "hebrew_percentage": document.hebrew_percentage,
        "ocr_text_preview": document.ocr_text[:500] if document.ocr_text else None
    }


@router.get("/", response_model=List[dict])
async def list_documents(
    skip: int = 0,
    limit: int = 50,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """List all documents with optional filtering"""
    query = db.query(Document)
    if status:
        query = query.filter(Document.status == status)
    documents = query.order_by(Document.upload_date.desc()).offset(skip).limit(limit).all()

    return [
        {
            "id": doc.id,
            "filename": doc.filename,
            "status": doc.status,
            "upload_date": doc.upload_date.isoformat(),
            "progress_percentage": doc.progress_percentage,
            "total_pages": doc.total_pages
        }
        for doc in documents
    ]


@router.delete("/{document_id}", response_model=dict)
async def delete_document(document_id: str, db: Session = Depends(get_db)):
    """Delete a document and all associated data"""
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    # Delete file from disk
    if os.path.exists(document.original_path):
        os.remove(document.original_path)

    # Delete database record (cascade deletes error records)
    db.delete(document)
    db.commit()

    return {"message": "Document deleted successfully"}


# Background task for processing
async def process_document(doc_id: str, db: Session):
    """Background task to process document through OCR and AI analysis"""
    document = db.query(Document).filter(Document.id == doc_id).first()
    if not document:
        return

    try:
        # Update status
        document.status = "processing"
        db.commit()

        # Get OCR processor (lazy initialization)
        ocr = get_ocr_processor()

        if not ocr:
            # OCR not available - mark as error for now
            document.status = "error"
            document.ocr_text = "OCR processing not available - ocr_pipeline module not installed"
            db.commit()
            return

        # Run OCR
        ocr_result = ocr.process_pdf(document.original_path)

        # Update document with OCR results
        document.total_pages = ocr_result.pages
        document.ocr_text = ocr_result.text
        document.overall_confidence = ocr_result.confidence
        document.processed_pages = ocr_result.pages
        document.status = "ready"
        db.commit()

        # Run AI analysis to detect errors (if available)
        dicta = get_dicta_analyzer()
        corrector = get_correction_suggester()

        if ML_AVAILABLE and dicta and corrector:
            analysis = dicta.analyze_text(ocr_result.text, ocr_result.words)
            document.hebrew_percentage = analysis.hebrew_percentage

            # Create error records for low-confidence words
            for error in analysis.errors:
                suggestions = corrector.suggest_corrections(
                    error.word,
                    error.context,
                    dicta_suggestions=error.suggestions
                )

                error_record = ErrorRecord(
                    id=str(uuid.uuid4()),
                    document_id=doc_id,
                    original_word=error.word,
                    position=error.position,
                    confidence=error.confidence,
                    context=error.context,
                    bbox=error.bbox,
                    suggestions=suggestions
                )
                db.add(error_record)
        else:
            # ML not available - mark as ready without error detection
            document.hebrew_percentage = 0.0

        document.status = "completed"
        db.commit()

    except Exception as e:
        document.status = "error"
        db.commit()
        raise
