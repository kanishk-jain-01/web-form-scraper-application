from .consumer import JobQueue

# Global job queue instance
job_queue = JobQueue()

__all__ = ["job_queue"]
