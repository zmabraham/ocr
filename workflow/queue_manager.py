"""Queue management for OCR processing workflow using Redis/Bull"""
import redis
import json
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

from config import settings

logger = logging.getLogger(__name__)


class QueueManager:
    """Manager for OCR processing and review queues"""

    def __init__(self):
        self.redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
        self.ocr_queue = f"queue:{settings.OCR_QUEUE_NAME}"
        self.review_queue = f"queue:{settings.REVIEW_QUEUE_NAME}"

    def enqueue_ocr_job(self, document_id: str, file_path: str, priority: int = 0) -> str:
        """Add a document to the OCR processing queue"""
        job_id = f"ocr:{document_id}:{datetime.utcnow().timestamp()}"

        job_data = {
            "id": job_id,
            "type": "ocr",
            "document_id": document_id,
            "file_path": file_path,
            "priority": priority,
            "created_at": datetime.utcnow().isoformat(),
            "status": "pending",
            "attempts": 0
        }

        # Add to Redis queue
        self.redis_client.hset(f"job:{job_id}", mapping=job_data)
        self.redis_client.zadd(self.ocr_queue, {job_id: priority})

        logger.info(f"Enqueued OCR job {job_id} for document {document_id}")
        return job_id

    def enqueue_review_job(self, document_id: str, error_count: int, priority: int = 0) -> str:
        """Add a document to the review queue"""
        job_id = f"review:{document_id}:{datetime.utcnow().timestamp()}"

        job_data = {
            "id": job_id,
            "type": "review",
            "document_id": document_id,
            "error_count": error_count,
            "priority": priority,
            "created_at": datetime.utcnow().isoformat(),
            "status": "pending",
            "attempts": 0
        }

        self.redis_client.hset(f"job:{job_id}", mapping=job_data)
        self.redis_client.zadd(self.review_queue, {job_id: priority})

        logger.info(f"Enqueued review job {job_id} for document {document_id}")
        return job_id

    def dequeue_ocr_job(self) -> Optional[Dict[str, Any]]:
        """Get next OCR job from queue"""
        # Get highest priority job (lowest score = highest priority)
        job_ids = self.redis_client.zrange(self.ocr_queue, 0, 0)

        if not job_ids:
            return None

        job_id = job_ids[0]
        job_data = self.redis_client.hgetall(f"job:{job_id}")

        if job_data:
            # Update job status
            self.redis_client.hset(f"job:{job_id}", "status", "processing")
            self.redis_client.hincrby(f"job:{job_id}", "attempts", 1)
            return job_data

        return None

    def dequeue_review_job(self) -> Optional[Dict[str, Any]]:
        """Get next review job from queue"""
        job_ids = self.redis_client.zrange(self.review_queue, 0, 0)

        if not job_ids:
            return None

        job_id = job_ids[0]
        job_data = self.redis_client.hgetall(f"job:{job_id}")

        if job_data:
            self.redis_client.hset(f"job:{job_id}", "status", "processing")
            self.redis_client.hincrby(f"job:{job_id}", "attempts", 1)
            return job_data

        return None

    def complete_job(self, job_id: str, result: Dict[str, Any] = None):
        """Mark a job as completed and remove from queue"""
        queue_name = self.ocr_queue if job_id.startswith("ocr:") else self.review_queue

        if result:
            self.redis_client.hset(f"job:{job_id}", "result", json.dumps(result))
            self.redis_client.hset(f"job:{job_id}", "completed_at", datetime.utcnow().isoformat())

        self.redis_client.hset(f"job:{job_id}", "status", "completed")
        self.redis_client.zrem(queue_name, job_id)

        # Archive job (keep for 7 days)
        self.redis_client.expire(f"job:{job_id}", 604800)

        logger.info(f"Completed job {job_id}")

    def fail_job(self, job_id: str, error_message: str):
        """Mark a job as failed"""
        queue_name = self.ocr_queue if job_id.startswith("ocr:") else self.review_queue

        self.redis_client.hset(f"job:{job_id}", "status", "failed")
        self.redis_client.hset(f"job:{job_id}", "error", error_message)
        self.redis_client.hset(f"job:{job_id}", "failed_at", datetime.utcnow().isoformat())
        self.redis_client.zrem(queue_name, job_id)

        logger.error(f"Job {job_id} failed: {error_message}")

    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific job"""
        job_data = self.redis_client.hgetall(f"job:{job_id}")
        return job_data if job_data else None

    def get_queue_stats(self) -> Dict[str, Any]:
        """Get statistics for both queues"""
        ocr_pending = self.redis_client.zcard(self.ocr_queue)
        review_pending = self.redis_client.zcard(self.review_queue)

        # Count jobs by status
        ocr_keys = self.redis_client.keys("job:ocr:*")
        review_keys = self.redis_client.keys("job:review:*")

        ocr_processing = sum(1 for k in ocr_keys if self.redis_client.hget(k, "status") == "processing")
        review_processing = sum(1 for k in review_keys if self.redis_client.hget(k, "status") == "processing")

        return {
            "ocr_queue": {
                "pending": ocr_pending,
                "processing": ocr_processing
            },
            "review_queue": {
                "pending": review_pending,
                "processing": review_processing
            },
            "timestamp": datetime.utcnow().isoformat()
        }

    def clear_queue(self, queue_type: str = "all"):
        """Clear jobs from queue(s)"""
        if queue_type in ("all", "ocr"):
            job_ids = self.redis_client.zrange(self.ocr_queue, 0, -1)
            for job_id in job_ids:
                self.redis_client.delete(f"job:{job_id}")
            self.redis_client.delete(self.ocr_queue)

        if queue_type in ("all", "review"):
            job_ids = self.redis_client.zrange(self.review_queue, 0, -1)
            for job_id in job_ids:
                self.redis_client.delete(f"job:{job_id}")
            self.redis_client.delete(self.review_queue)

        logger.info(f"Cleared {queue_type} queue(s)")


# Worker process functions
async def ocr_worker(queue_manager: QueueManager, stop_event):
    """Worker process for OCR jobs"""
    logger.info("OCR worker started")

    while not stop_event.is_set():
        job = queue_manager.dequeue_ocr_job()

        if job:
            try:
                # Import here to avoid circular dependency
                from ocr_pipeline import OCRProcessor
                from app.database import SessionLocal
                from app.models import Document

                processor = OCRProcessor()
                db = SessionLocal()

                # Process document
                document = db.query(Document).filter(Document.id == job["document_id"]).first()
                if document:
                    document.status = "processing"
                    db.commit()

                    result = processor.process_pdf(job["file_path"])

                    document.total_pages = result.pages
                    document.ocr_text = result.text
                    document.overall_confidence = result.confidence
                    document.processed_pages = result.pages
                    db.commit()

                    queue_manager.complete_job(job["id"], {"pages": result.pages})

                db.close()

            except Exception as e:
                logger.error(f"OCR job {job['id']} failed: {e}")
                queue_manager.fail_job(job["id"], str(e))
        else:
            # No jobs, sleep briefly
            import asyncio
            await asyncio.sleep(1)


async def review_worker(queue_manager: QueueManager, stop_event):
    """Worker process for review preparation jobs"""
    logger.info("Review worker started")

    while not stop_event.is_set():
        job = queue_manager.dequeue_review_job()

        if job:
            try:
                from ai_analysis import DictaBERTAnalyzer, CorrectionSuggester
                from app.database import SessionLocal
                from app.models import Document, ErrorRecord
                import uuid

                analyzer = DictaBERTAnalyzer()
                suggester = CorrectionSuggester()
                db = SessionLocal()

                document = db.query(Document).filter(Document.id == job["document_id"]).first()
                if document and document.ocr_text:
                    # Analyze text for errors
                    # (This would need to be implemented based on ocr_result)
                    pass

                db.close()
                queue_manager.complete_job(job["id"])

            except Exception as e:
                logger.error(f"Review job {job['id']} failed: {e}")
                queue_manager.fail_job(job["id"], str(e))
        else:
            import asyncio
            await asyncio.sleep(1)
