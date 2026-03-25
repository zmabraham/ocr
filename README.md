# Hebrew/Yiddish/Aramaic OCR Post-Processor

A complete workflow for transforming OCR output from low-resolution Hebrew/Yiddish/Aramaic PDFs into clean, verified text through human review and AI-assisted correction.

## Features

- **OCR Processing**: Tesseract 5.0+ with Hebrew language support
- **AI Error Detection**: DictaBERT models for Hebrew text analysis
- **Human-in-the-Loop**: Review interface for verifying corrections
- **Hybrid Review Modes**: Split view (image + text) and overlay mode
- **Queue Management**: Redis-based job queue for processing
- **Export Options**: Download corrected text and correction logs

## Architecture

```
PDF Upload → OCR (Tesseract) → DictaBERT Analysis → Review Queue → Human Review → Clean Text
```

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL 15+
- Redis 7+
- Tesseract OCR with Hebrew language pack

### Installation

1. **Clone and navigate to project**:
```bash
cd /workspace/ocr-workflow
```

2. **Install Python dependencies**:
```bash
pip install -r requirements.txt
```

3. **Install Node.js dependencies**:
```bash
cd review_ui
npm install
```

4. **Install Tesseract with Hebrew**:
```bash
# Ubuntu/Debian
sudo apt-get install tesseract-ocr tesseract-ocr-heb

# macOS
brew install tesseract tesseract-lang
```

5. **Set up environment**:
```bash
cp .env.example .env
# Edit .env with your configuration
```

6. **Start services**:
```bash
# Terminal 1: Start PostgreSQL and Redis
docker-compose up postgres redis

# Terminal 2: Start FastAPI backend
python run.py

# Terminal 3: Start Vue.js frontend
cd review_ui && npm run dev
```

7. **Open browser**:
- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

## Docker Deployment

```bash
docker-compose up -d
```

## Usage

1. **Upload a PDF**: Navigate to the app and upload a Hebrew/Yiddish/Aramaic PDF
2. **Wait for Processing**: OCR and AI analysis run automatically
3. **Review Errors**: Each potential error is presented with:
   - Image context showing the word location
   - OCR confidence score
   - Ranked correction suggestions
4. **Make Corrections**: Accept suggestions or provide custom corrections
5. **Export**: Download the corrected text file

## API Endpoints

### Documents
- `POST /api/documents/upload` - Upload PDF for processing
- `GET /api/documents/{id}` - Get document details
- `GET /api/documents/` - List all documents
- `DELETE /api/documents/{id}` - Delete document

### Reviews
- `GET /api/reviews/document/{id}/next-error` - Get next error to review
- `GET /api/reviews/document/{id}/summary` - Get review summary
- `POST /api/reviews/submit` - Submit correction
- `GET /api/reviews/pending` - List pending reviews

### Export
- `GET /api/export/document/{id}/text` - Get corrected text
- `GET /api/export/document/{id}/download` - Download text file
- `GET /api/export/document/{id}/statistics` - Get document statistics

## Technology Stack

### Backend
- **FastAPI** - Modern async Python web framework
- **SQLAlchemy** - Database ORM
- **Tesseract OCR** - OCR engine with Hebrew support
- **DictaBERT** - Hebrew BERT models for text analysis
- **Redis** - Queue and caching

### Frontend
- **Vue.js 3** - Progressive JavaScript framework
- **PrimeVue** - UI component library
- **Pinia** - State management
- **Axios** - HTTP client

## Project Structure

```
ocr-workflow/
├── app/
│   ├── main.py              # FastAPI application
│   ├── models.py            # Database models
│   ├── database.py          # Database connection
│   └── routes/
│       ├── documents.py     # Document endpoints
│       ├── reviews.py       # Review endpoints
│       └── export.py        # Export endpoints
├── ocr_pipeline/
│   └── ocr_processor.py     # OCR processing engine
├── ai_analysis/
│   └── text_analyzer.py     # DictaBERT integration
├── workflow/
│   └── queue_manager.py     # Queue management
├── review_ui/
│   └── src/
│       ├── views/           # Vue components
│       ├── stores/          # Pinia stores
│       └── api/             # API client
├── config.py                # Application configuration
├── requirements.txt         # Python dependencies
└── docker-compose.yml       # Docker deployment
```

## License

MIT
