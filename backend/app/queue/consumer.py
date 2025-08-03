import asyncio
import json
import uuid
import logging
from typing import Dict, Any, Optional, List
from collections import deque
from datetime import datetime
from ..agents.orchestrator import ScrapingOrchestrator

logger = logging.getLogger(__name__)


class JobQueue:
    def __init__(self):
        self.job_queue: deque = deque()
        self.active_jobs: Dict[str, Dict] = {}
        self.human_input_queue: Dict[str, str] = {}
        self.is_processing = False
        self._consumer_task = None

    async def start_consumer(self):
        """Start the job queue consumer"""
        if self._consumer_task is None or self._consumer_task.done():
            self._consumer_task = asyncio.create_task(self._consumer_loop())
            logger.info("Job queue consumer started")

    async def stop_consumer(self):
        """Stop the job queue consumer"""
        if self._consumer_task and not self._consumer_task.done():
            self._consumer_task.cancel()
            try:
                await self._consumer_task
            except asyncio.CancelledError:
                pass
            logger.info("Job queue consumer stopped")

    async def add_scraping_job(
        self,
        url: str,
        client_id: str,
        website_id: int,
        config: Optional[Dict] = None
    ) -> str:
        """Add a scraping job to the queue"""
        job_id = str(uuid.uuid4())
        
        job_data = {
            "job_id": job_id,
            "url": url,
            "client_id": client_id,
            "website_id": website_id,
            "config": config or {},
            "created_at": datetime.utcnow().isoformat(),
            "status": "queued"
        }
        
        self.job_queue.append(job_data)
        logger.info(f"Added job {job_id} to queue for URL: {url}")
        
        # Start consumer if not running
        await self.start_consumer()
        
        return job_id

    async def submit_human_input(self, job_id: str, user_input: str):
        """Submit human input for a job waiting for HITL"""
        self.human_input_queue[job_id] = user_input
        logger.info(f"Human input submitted for job {job_id}")

    async def cancel_job(self, job_id: str) -> bool:
        """Cancel a job"""
        # Remove from queue if not started
        for i, job in enumerate(list(self.job_queue)):
            if job["job_id"] == job_id:
                del self.job_queue[i]
                logger.info(f"Removed job {job_id} from queue")
                return True
        
        # Mark active job as cancelled
        if job_id in self.active_jobs:
            self.active_jobs[job_id]["status"] = "cancelled"
            logger.info(f"Marked active job {job_id} as cancelled")
            return True
        
        return False

    async def get_queue_status(self) -> Dict[str, Any]:
        """Get current queue status"""
        return {
            "queued_jobs": len(self.job_queue),
            "active_jobs": len(self.active_jobs),
            "is_processing": self.is_processing,
            "awaiting_human_input": len(self.human_input_queue)
        }

    async def _consumer_loop(self):
        """Main consumer loop"""
        logger.info("Job queue consumer loop started")
        
        while True:
            try:
                # Process queued jobs
                if self.job_queue and not self.is_processing:
                    await self._process_next_job()
                
                # Check for completed jobs
                await self._cleanup_completed_jobs()
                
                # Wait before next iteration
                await asyncio.sleep(1)
                
            except asyncio.CancelledError:
                logger.info("Consumer loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in consumer loop: {e}")
                await asyncio.sleep(5)  # Wait longer on error

    async def _process_next_job(self):
        """Process the next job in the queue"""
        if not self.job_queue:
            return
        
        job_data = self.job_queue.popleft()
        job_id = job_data["job_id"]
        
        try:
            self.is_processing = True
            self.active_jobs[job_id] = job_data
            job_data["status"] = "running"
            job_data["started_at"] = datetime.utcnow().isoformat()
            
            logger.info(f"Starting job {job_id}")
            
            # Create orchestrator and run job
            orchestrator = ScrapingOrchestrator(
                client_id=job_data["client_id"],
                job_id=job_id
            )
            
            # Run the job in background
            asyncio.create_task(
                self._run_job(orchestrator, job_data)
            )
            
        except Exception as e:
            logger.error(f"Error starting job {job_id}: {e}")
            job_data["status"] = "failed"
            job_data["error"] = str(e)
        finally:
            self.is_processing = False

    async def _run_job(self, orchestrator: ScrapingOrchestrator, job_data: Dict):
        """Run a scraping job"""
        job_id = job_data["job_id"]
        
        try:
            # Set up human input callback
            async def human_input_callback() -> str:
                # Wait for human input
                while job_id not in self.human_input_queue:
                    if job_data.get("status") == "cancelled":
                        raise Exception("Job cancelled")
                    await asyncio.sleep(1)
                
                user_input = self.human_input_queue.pop(job_id)
                return user_input
            
            # Run the orchestrator
            result = await orchestrator.run_scraping_job(
                url=job_data["url"],
                config=job_data["config"],
                human_input_callback=human_input_callback
            )
            
            # Update job status
            job_data["status"] = "completed"
            job_data["result"] = result
            job_data["completed_at"] = datetime.utcnow().isoformat()
            
            logger.info(f"Job {job_id} completed successfully")
            
        except Exception as e:
            logger.error(f"Job {job_id} failed: {e}")
            job_data["status"] = "failed"
            job_data["error"] = str(e)
            job_data["completed_at"] = datetime.utcnow().isoformat()

    async def _cleanup_completed_jobs(self):
        """Clean up completed jobs after some time"""
        completed_jobs = []
        current_time = datetime.utcnow()
        
        for job_id, job_data in self.active_jobs.items():
            if job_data["status"] in ["completed", "failed", "cancelled"]:
                # Keep completed jobs for 1 hour for status checking
                if "completed_at" in job_data:
                    completed_at = datetime.fromisoformat(job_data["completed_at"])
                    if (current_time - completed_at).total_seconds() > 3600:  # 1 hour
                        completed_jobs.append(job_id)
        
        # Remove old completed jobs
        for job_id in completed_jobs:
            del self.active_jobs[job_id]
            logger.debug(f"Cleaned up completed job {job_id}")

    def get_job_status(self, job_id: str) -> Optional[Dict]:
        """Get status of a specific job"""
        if job_id in self.active_jobs:
            return self.active_jobs[job_id]
        
        # Check if in queue
        for job in self.job_queue:
            if job["job_id"] == job_id:
                return job
        
        return None
