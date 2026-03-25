"""Database Models for OCR Workflow"""
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, Text, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()


class Document(Base):
    """Represents a document being processed"""
    __tablename__ = "documents"

    id = Column(String, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    original_path = Column(String, nullable=False)
    upload_date = Column(DateTime, default=datetime.utcnow)
    status = Column(String, default="pending")  # pending, processing, ready, completed
    total_pages = Column(Integer)
    processed_pages = Column(Integer, default=0)
    ocr_text = Column(Text)
    final_text = Column(Text)
    overall_confidence = Column(Float)
    hebrew_percentage = Column(Float)

    # Relationships
    error_records = relationship("ErrorRecord", back_populates="document", cascade="all, delete-orphan")

    @property
    def progress_percentage(self) -> float:
        if self.total_pages is None or self.total_pages == 0:
            return 0.0
        return (self.processed_pages / self.total_pages) * 100


class ErrorRecord(Base):
    """Represents a potential OCR error requiring review"""
    __tablename__ = "error_records"

    id = Column(String, primary_key=True, index=True)
    document_id = Column(String, ForeignKey("documents.id"), nullable=False)
    original_word = Column(String, nullable=False)
    position = Column(Integer, nullable=False)
    confidence = Column(Float, nullable=False)
    context = Column(Text)
    bbox = Column(JSON)  # Store bounding box as [x1, y1, x2, y2]

    # Review status
    status = Column(String, default="pending")  # pending, approved, corrected, skipped
    selected_correction = Column(String)
    custom_correction = Column(Text)
    reviewed_at = Column(DateTime)
    reviewed_by = Column(String)  # User ID

    # Suggestions stored as JSON array
    suggestions = Column(JSON)

    # Relationships
    document = relationship("Document", back_populates="error_records")

    @property
    def suggestions_list(self) -> list:
        """Parse suggestions from JSON"""
        return self.suggestions if self.suggestions else []

    @property
    def is_corrected(self) -> bool:
        """Check if this error has been corrected"""
        return self.status in ["approved", "corrected"]
