from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Dict, Any, Optional
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from ..queue import job_queue
from ..db.crud import ScrapeJobCRUD, WebsiteCRUD
from .dependencies import get_database, get_current_user

router = APIRouter()
logger = logging.getLogger(__name__)


class StartScrapeRequest(BaseModel):
    url: str
    client_id: str
    config: Optional[Dict[str, Any]] = None


class ScrapeResponse(BaseModel):
    job_id: str
    status: str
    message: str


class HumanInputRequest(BaseModel):
    job_id: str
    user_input: str


@router.post("/start", response_model=ScrapeResponse)
async def start_scraping(
    request: StartScrapeRequest,
    db: AsyncSession = Depends(get_database),
    current_user: dict = Depends(get_current_user)
):
    """Start a new scraping job"""
    
    if not request.url.startswith(("http://", "https://")):
        raise HTTPException(status_code=400, detail="Invalid URL format")
    
    try:
        # Get or create website record
        website = await WebsiteCRUD.get_website_by_url(db, request.url)
        if not website:
            website = await WebsiteCRUD.create_website(
                db, 
                name=request.url, 
                base_url=request.url
            )
        
        # Add job to queue
        job_id = await job_queue.add_scraping_job(
            url=request.url,
            client_id=request.client_id,
            website_id=website.id,
            config=request.config
        )
        
        # Create database record
        await ScrapeJobCRUD.create_scrape_job(
            db,
            website_id=website.id,
            job_id=job_id,
            target_url=request.url,
            status="queued"
        )
        
        return ScrapeResponse(
            job_id=job_id,
            status="queued",
            message=f"Scraping job queued for {request.url}"
        )
        
    except Exception as e:
        logger.error(f"Error starting scraping job: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start scraping job: {str(e)}")


@router.get("/status/{job_id}")
async def get_scrape_status(
    job_id: str,
    db: AsyncSession = Depends(get_database),
    current_user: dict = Depends(get_current_user)
):
    """Get the status of a scraping job"""
    
    try:
        job = await ScrapeJobCRUD.get_job_by_id(db, job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        return {
            "job_id": job.job_id,
            "status": job.status,
            "current_action": job.current_action,
            "progress_percentage": job.progress_percentage,
            "form_data": job.form_data,
            "requires_human_input": job.requires_human_input,
            "human_input_prompt": job.human_input_prompt,
            "error_message": job.error_message,
            "created_at": job.created_at,
            "completed_at": job.completed_at
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting job status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get job status: {str(e)}")


@router.post("/human-input")
async def submit_human_input(
    request: HumanInputRequest,
    db: AsyncSession = Depends(get_database),
    current_user: dict = Depends(get_current_user)
):
    """Submit human input for HITL workflow"""
    
    try:
        # Update job to remove human input requirement
        job = await ScrapeJobCRUD.set_human_input_required(
            db, request.job_id, False
        )
        
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Send input to job queue for processing
        await job_queue.submit_human_input(request.job_id, request.user_input)
        
        return {
            "job_id": request.job_id,
            "status": "input_processed",
            "message": "Human input submitted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing human input: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to process human input: {str(e)}")


@router.post("/stop/{job_id}")
async def stop_scraping_job(
    job_id: str,
    db: AsyncSession = Depends(get_database),
    current_user: dict = Depends(get_current_user)
):
    """Stop a scraping job"""
    
    try:
        # Update job status in database
        job = await ScrapeJobCRUD.update_job_status(
            db, job_id, "cancelled", current_action="Job cancelled by user"
        )
        
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Stop job in queue
        await job_queue.cancel_job(job_id)
        
        return {
            "job_id": job_id,
            "status": "cancelled",
            "message": "Scraping job cancelled successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error stopping job: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to stop job: {str(e)}")


@router.get("/jobs")
async def list_scraping_jobs(
    db: AsyncSession = Depends(get_database),
    current_user: dict = Depends(get_current_user)
):
    """List scraping jobs"""
    try:
        # Get active jobs from database
        active_jobs = await ScrapeJobCRUD.get_active_jobs(db)
        
        jobs_data = []
        for job in active_jobs:
            jobs_data.append({
                "job_id": job.job_id,
                "target_url": job.target_url,
                "status": job.status,
                "current_action": job.current_action,
                "progress_percentage": job.progress_percentage,
                "created_at": job.created_at,
                "requires_human_input": job.requires_human_input
            })
        
        return {
            "jobs": jobs_data,
            "total_count": len(jobs_data),
            "queue_status": await job_queue.get_queue_status()
        }
        
    except Exception as e:
        logger.error(f"Error listing jobs: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list jobs: {str(e)}")


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "web-scraper-api",
        "queue_status": await job_queue.get_queue_status()
    }
