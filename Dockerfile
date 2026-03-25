FROM python:3.11-slim

# Set DEBIAN_FRONTEND to noninteractive
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies (more resilient)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    tesseract-ocr \
    poppler-utils \
    libpq-dev \
    gcc \
    g++ \
    wget \
    && \
    # Try to install Hebrew language pack (may fail gracefully)
    apt-get install -y --no-install-recommends tesseract-ocr-heb || true && \
    apt-get install -y --no-install-recommends tesseract-ocr-eng || true && \
    rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /workspace/ocr-workflow

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p uploads models

# Set Python path
ENV PYTHONPATH=/workspace/ocr-workflow

# Expose port
EXPOSE 8000

# Default command - Railway provides PORT env var
# Use shell form to expand environment variables
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT}
