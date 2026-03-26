"""OCR Workflow Configuration"""
import os
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "Hebrew OCR Post-Processor"
    VERSION: str = "1.0.0"
    DEBUG: bool = False

    # Server (PORT can be overridden by Railway)
    HOST: str = "0.0.0.0"
    PORT: int = int(os.getenv("PORT", 8000))

    # Database (Railway provides DATABASE_URL automatically)
    # Use /tmp for Railway (read-only filesystem elsewhere)
    DATABASE_URL: str = os.getenv("DATABASE_URL", f"sqlite:///{os.path.join(os.getenv('TMPDIR', '/tmp'), 'ocr_workflow.db')}")

    # Redis (Railway provides REDIS_URL automatically)
    REDIS_URL: str = "redis://localhost:6379/0"

    # OCR
    TESSERACT_CMD: str = "/usr/bin/tesseract"
    TESSERACT_LANG: str = "heb"  # Hebrew

    # AI Models
    DICTABERT_MODEL: str = "dicta-il/dictabert"
    DICTABERT_MORPH_MODEL: str = "dicta-il/dictabert-morph"
    HEBERT_MODEL: str = "avichr/heBERT"
    # Use /tmp for model cache on Railway (read-only filesystem elsewhere)
    MODEL_CACHE_DIR: str = os.path.join(os.getenv('TMPDIR', '/tmp'), 'models')

    # File Storage
    # Use /tmp for Railway (read-only filesystem elsewhere)
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", os.path.join(os.getenv('TMPDIR', '/tmp'), 'uploads'))
    MAX_FILE_SIZE: int = 50 * 1024 * 1024  # 50MB

    # Confidence Thresholds
    CONFIDENCE_LOW: float = 0.70
    CONFIDENCE_MEDIUM: float = 0.85

    # Queue
    OCR_QUEUE_NAME: str = "ocr-process"
    REVIEW_QUEUE_NAME: str = "review-queue"

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
