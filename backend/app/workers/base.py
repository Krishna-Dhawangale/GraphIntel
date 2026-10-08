from abc import ABC, abstractmethod
from typing import Any, Callable, Coroutine, Dict, Optional


class BaseWorker(ABC):
    """
    Abstract worker interface for background jobs.
    Allows seamlessly switching between asyncio in-process worker, Celery, Dramatiq, or Kafka.
    """

    @abstractmethod
    async def submit_job(
        self,
        job_type: str,
        payload: Dict[str, Any],
        task_func: Optional[Callable[..., Coroutine]] = None,
    ) -> str:
        """Enqueue or dispatch a job."""
        pass

    @abstractmethod
    async def get_status(self, job_id: str) -> Dict[str, Any]:
        """Fetch job status and metadata."""
        pass
