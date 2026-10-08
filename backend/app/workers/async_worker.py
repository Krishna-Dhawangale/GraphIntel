import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Coroutine, Dict, Optional

from sqlalchemy import select

from app.core.resilience import execute_with_retry
from app.db.session import AsyncSessionLocal
from app.models.ingestion import IngestionJob, JobStatus
from app.workers.base import BaseWorker

logger = logging.getLogger(__name__)


class AsyncBackgroundWorker(BaseWorker):
    """
    In-process asynchronous background worker with automatic DB job tracking,
    retry management, and resilience.
    """

    def __init__(self, max_concurrent: int = 5):
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._running_tasks: Dict[str, asyncio.Task] = {}

    async def submit_job(
        self,
        job_type: str,
        payload: Dict[str, Any],
        task_func: Optional[Callable[..., Coroutine]] = None,
    ) -> str:
        job_id = payload.get("job_id") or str(uuid.uuid4())
        doc_id = payload.get("document_id")
        tenant_id = payload.get("tenant_id")

        # Spawn task in background
        task = asyncio.create_task(
            self._execute_tracked_job(
                job_id=job_id,
                doc_id=doc_id,
                tenant_id=tenant_id,
                job_type=job_type,
                payload=payload,
                task_func=task_func,
            )
        )
        self._running_tasks[job_id] = task

        # Clean up reference on completion
        task.add_done_callback(lambda _: self._running_tasks.pop(job_id, None))
        return job_id

    async def _execute_tracked_job(
        self,
        job_id: str,
        doc_id: Optional[str],
        tenant_id: Optional[str],
        job_type: str,
        payload: Dict[str, Any],
        task_func: Optional[Callable[..., Coroutine]],
    ):
        async with self._semaphore:
            # Mark RUNNING in DB
            async with AsyncSessionLocal() as db:
                if doc_id:
                    stmt = select(IngestionJob).where(IngestionJob.id == job_id)
                    res = await db.execute(stmt)
                    job_record = res.scalar_one_or_none()
                    if job_record:
                        job_record.status = JobStatus.RUNNING
                        job_record.started_at = datetime.now(timezone.utc)
                        await db.commit()

            try:
                logger.info(f"Worker starting background job {job_id} ({job_type})")
                if task_func:
                    # Execute with resilience retry policy
                    await execute_with_retry(
                        task_func,
                        payload=payload,
                        max_retries=3,
                        initial_delay=1.0,
                    )

                # Mark COMPLETED in DB
                async with AsyncSessionLocal() as db:
                    if doc_id:
                        stmt = select(IngestionJob).where(IngestionJob.id == job_id)
                        res = await db.execute(stmt)
                        job_record = res.scalar_one_or_none()
                        if job_record:
                            job_record.status = JobStatus.COMPLETED
                            job_record.completed_at = datetime.now(timezone.utc)
                            await db.commit()
                logger.info(f"Worker completed job {job_id} ({job_type}) successfully")

            except Exception as exc:
                logger.exception(f"Worker failed executing job {job_id}: {exc}")
                async with AsyncSessionLocal() as db:
                    if doc_id:
                        stmt = select(IngestionJob).where(IngestionJob.id == job_id)
                        res = await db.execute(stmt)
                        job_record = res.scalar_one_or_none()
                        if job_record:
                            job_record.status = JobStatus.FAILED
                            job_record.error_message = str(exc)
                            job_record.completed_at = datetime.now(timezone.utc)
                            await db.commit()

    async def get_status(self, job_id: str) -> Dict[str, Any]:
        async with AsyncSessionLocal() as db:
            stmt = select(IngestionJob).where(IngestionJob.id == job_id)
            res = await db.execute(stmt)
            job = res.scalar_one_or_none()
            if not job:
                return {"job_id": job_id, "status": "UNKNOWN"}
            return {
                "job_id": job.id,
                "document_id": job.document_id,
                "status": job.status.value,
                "error_message": job.error_message,
                "started_at": job.started_at.isoformat() if job.started_at else None,
                "completed_at": job.completed_at.isoformat() if job.completed_at else None,
            }


# Global worker instance
background_worker = AsyncBackgroundWorker()
