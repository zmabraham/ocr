"""FastAPI Application for OCR Workflow"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import logging
import os

from config import settings
from .database import init_db, engine
from .routes import documents, reviews, export

logger = logging.getLogger(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)

# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    debug=settings.DEBUG
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(documents.router, prefix="/api/documents", tags=["documents"])
app.include_router(reviews.router, prefix="/api/reviews", tags=["reviews"])
app.include_router(export.router, prefix="/api/export", tags=["export"])


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "version": settings.VERSION}


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Hebrew OCR Post-Processor API",
        "version": settings.VERSION,
        "docs": "/docs",
        "endpoints": {
            "documents": "/api/documents",
            "reviews": "/api/reviews",
            "export": "/api/export"
        }
    }


@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    logger.info("=" * 50)
    logger.info("STARTUP: Application starting...")
    logger.info(f"PORT: {os.getenv('PORT', 'not set')}")
    logger.info(f"DATABASE_URL: {settings.DATABASE_URL[:50]}...")
    logger.info(f"REDIS_URL: {settings.REDIS_URL[:50]}...")

    try:
        logger.info("Initializing database...")
        init_db()
        logger.info(f"{settings.APP_NAME} started successfully")
    except Exception as e:
        logger.warning(f"Database initialization failed: {e}")
        logger.info(f"{settings.APP_NAME} started without database")

    logger.info("=" * 50)


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down gracefully")


# Optional: Serve static files for frontend if built
# app.mount("/static", StaticFiles(directory="review_ui/dist"), name="static")


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )
