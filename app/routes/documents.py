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
from ocr_pipeline import OCRProcessor

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
    if _ocr_processor is None:
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
    """Upload a PDF document for OCR processing"""
    # Validate file type
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    # Generate document ID
    doc_id = str(uuid.uuid4())
    upload_path = os.path.join(settings.UPLOAD_DIR, f"{doc_id}.pdf")

    # Ensure upload directory exists
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

    # Save file
    with open(upload_path, "wb") as f:
        content = await file.read()
        if len(content) > settings.MAX_FILE_SIZE:
            raise HTTPException(status_code=400, detail="File too large")
        f.write(content)

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

    return {
        "document_id": doc_id,
        "filename": file.filename,
        "status": "pending",
        "message": "Document uploaded successfully. OCR processing started."
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
