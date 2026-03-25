"""Review queue and correction routes"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from ..database import get_db
from ..models import Document, ErrorRecord

router = APIRouter()


class CorrectionSubmit(BaseModel):
    error_id: str
    selected_correction: Optional[int] = None  # Index in suggestions array
    custom_correction: Optional[str] = None
    skipped: bool = False
    reviewed_by: Optional[str] = None


@router.get("/pending", response_model=List[dict])
async def get_pending_reviews(
    document_id: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """Get all pending errors across documents or for specific document"""
    query = db.query(ErrorRecord).filter(ErrorRecord.status == "pending")
    if document_id:
        query = query.filter(ErrorRecord.document_id == document_id)

    errors = query.order_by(ErrorRecord.id).offset(skip).limit(limit).all()

    return [
        {
            "error_id": error.id,
            "document_id": error.document_id,
            "original_word": error.original_word,
            "confidence": error.confidence,
            "context": error.context
        }
        for error in errors
    ]


@router.get("/document/{document_id}/next-error", response_model=dict)
async def get_next_error(document_id: str, db: Session = Depends(get_db)):
    """Get the next error to review for a document"""
    error = db.query(ErrorRecord).filter(
        ErrorRecord.document_id == document_id,
        ErrorRecord.status == "pending"
    ).order_by(ErrorRecord.position).first()

    if not error:
        # Check if document is fully reviewed
        document = db.query(Document).filter(Document.id == document_id).first()
        if document and db.query(ErrorRecord).filter(
            ErrorRecord.document_id == document_id,
            ErrorRecord.status == "pending"
        ).count() == 0:
            return {"status": "complete", "message": "All errors reviewed"}
        raise HTTPException(status_code=404, detail="No pending errors found")

    return {
        "error_id": error.id,
        "document_id": error.document_id,
        "original_word": error.original_word,
        "confidence": error.confidence,
        "context": error.context,
        "bbox": error.bbox,
        "suggestions": error.suggestions_list,
        "position": error.position
    }


@router.get("/document/{document_id}/summary", response_model=dict)
async def get_review_summary(document_id: str, db: Session = Depends(get_db)):
    """Get summary of review status for a document"""
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    total_errors = db.query(ErrorRecord).filter(ErrorRecord.document_id == document_id).count()
    pending = db.query(ErrorRecord).filter(
        ErrorRecord.document_id == document_id,
        ErrorRecord.status == "pending"
    ).count()
    corrected = db.query(ErrorRecord).filter(
        ErrorRecord.document_id == document_id,
        ErrorRecord.status == "corrected"
    ).count()
    approved = db.query(ErrorRecord).filter(
        ErrorRecord.document_id == document_id,
        ErrorRecord.status == "approved"
    ).count()
    skipped = db.query(ErrorRecord).filter(
        ErrorRecord.document_id == document_id,
        ErrorRecord.status == "skipped"
    ).count()

    return {
        "document_id": document_id,
        "filename": document.filename,
        "total_errors": total_errors,
        "pending": pending,
        "corrected": corrected,
        "approved": approved,
        "skipped": skipped,
        "completion_percentage": round(((total_errors - pending) / total_errors * 100) if total_errors > 0 else 100, 2)
    }


@router.post("/submit", response_model=dict)
async def submit_correction(correction: CorrectionSubmit, db: Session = Depends(get_db)):
    """Submit a correction for an error record"""
    error = db.query(ErrorRecord).filter(ErrorRecord.id == correction.error_id).first()
    if not error:
        raise HTTPException(status_code=404, detail="Error record not found")

    # Update error record
    if correction.skipped:
        error.status = "skipped"
    elif correction.custom_correction:
        error.status = "corrected"
        error.custom_correction = correction.custom_correction
        error.selected_correction = None
    elif correction.selected_correction is not None:
        error.status = "corrected"
        error.selected_correction = correction.selected_correction
    else:
        error.status = "approved"

    error.reviewed_at = datetime.utcnow()
    error.reviewed_by = correction.reviewed_by

    db.commit()

    # Update document's final text
    _apply_correction_to_document(error, db)

    return {
        "status": "success",
        "error_id": error.id,
        "new_status": error.status,
        "message": "Correction recorded successfully"
    }


@router.get("/document/{document_id}/errors", response_model=List[dict])
async def get_document_errors(
    document_id: str,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get all errors for a document, optionally filtered by status"""
    query = db.query(ErrorRecord).filter(ErrorRecord.document_id == document_id)
    if status:
        query = query.filter(ErrorRecord.status == status)

    errors = query.order_by(ErrorRecord.position).all()

    return [
        {
            "error_id": error.id,
            "original_word": error.original_word,
            "confidence": error.confidence,
            "context": error.context,
            "status": error.status,
            "position": error.position,
            "correction": error.custom_correction or error.selected_correction,
            "suggestions": error.suggestions_list
        }
        for error in errors
    ]


def _apply_correction_to_document(error: ErrorRecord, db: Session):
    """Apply a correction to the document's final text"""
    document = error.document
    if not document.ocr_text:
        return

    # Initialize final_text if not set
    if not document.final_text:
        document.final_text = document.ocr_text

    # Determine the correction to apply
    if error.status == "approved":
        corrected_word = error.original_word
    elif error.custom_correction:
        corrected_word = error.custom_correction
    elif error.selected_correction is not None and error.suggestions:
        corrected_word = error.suggestions[error.selected_correction]
    else:
        return

    # Apply correction (simple word replacement)
    # In production, you'd want more sophisticated text replacement
    # that respects word boundaries and context
    document.final_text = document.final_text.replace(error.original_word, corrected_word, 1)

    db.commit()
