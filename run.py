#!/usr/bin/env python3
"""Run script for the OCR Workflow application"""
import sys
import uvicorn
from config import settings

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )
