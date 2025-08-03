from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Dict, Any, Optional
import logging
from ..agents.scraping_agent import ScrapingAgent

router = APIRouter()
logger = logging.getLogger(__name__)

# Store active agents
active_agents: Dict[str, ScrapingAgent] = {}


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


async def run_scraping_agent(agent: ScrapingAgent, url: str, config: Optional[Dict] = None):
    """Background task to run the scraping agent"""
    try:
        await agent.start_scraping_job(url, config)
    except Exception as e:
        logger.error(f"Error in background scraping task: {e}")
    finally:
        # Clean up agent from active agents
        if agent.client_id in active_agents:
            del active_agents[agent.client_id]


@router.post("/start", response_model=ScrapeResponse)
async def start_scraping(request: StartScrapeRequest, background_tasks: BackgroundTasks):
    """Start a new scraping job"""
    
    if not request.url.startswith(("http://", "https://")):
        raise HTTPException(status_code=400, detail="Invalid URL format")
    
    try:
        # Create new agent for this client
        agent = ScrapingAgent(request.client_id)
        active_agents[request.client_id] = agent
        
        # Start the scraping job in the background
        background_tasks.add_task(
            run_scraping_agent,
            agent,
            request.url,
            request.config
        )
        
        return ScrapeResponse(
            job_id=agent.thread_id,
            status="started",
            message=f"Scraping job started for {request.url}"
        )
        
    except Exception as e:
        logger.error(f"Error starting scraping job: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start scraping job: {str(e)}")


@router.get("/status/{client_id}")
async def get_scrape_status(client_id: str):
    """Get the status of a scraping job by client ID"""
    
    if client_id not in active_agents:
        raise HTTPException(status_code=404, detail="No active job found for this client")
    
    try:
        agent = active_agents[client_id]
        status = await agent.get_job_status()
        return status
        
    except Exception as e:
        logger.error(f"Error getting job status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get job status: {str(e)}")


@router.post("/human-input")
async def submit_human_input(request: HumanInputRequest):
    """Submit human input for HITL workflow"""
    
    # Find agent by job_id
    agent = None
    for client_id, active_agent in active_agents.items():
        if active_agent.thread_id == request.job_id:
            agent = active_agent
            break
    
    if not agent:
        raise HTTPException(status_code=404, detail="Job not found or no longer active")
    
    try:
        result = await agent.handle_human_input(request.user_input)
        return {
            "job_id": request.job_id,
            "status": "input_processed",
            "result": result
        }
        
    except Exception as e:
        logger.error(f"Error processing human input: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to process human input: {str(e)}")


@router.post("/stop/{client_id}")
async def stop_scraping_job(client_id: str):
    """Stop a scraping job"""
    
    if client_id not in active_agents:
        raise HTTPException(status_code=404, detail="No active job found for this client")
    
    try:
        agent = active_agents[client_id]
        await agent.stop_job()
        del active_agents[client_id]
        
        return {
            "client_id": client_id,
            "status": "stopped",
            "message": "Scraping job stopped successfully"
        }
        
    except Exception as e:
        logger.error(f"Error stopping job: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to stop job: {str(e)}")


@router.get("/jobs")
async def list_active_jobs():
    """List all active scraping jobs"""
    try:
        jobs = []
        for client_id, agent in active_agents.items():
            status = await agent.get_job_status()
            jobs.append({
                "client_id": client_id,
                "job_id": agent.thread_id,
                "status": status
            })
        
        return {"active_jobs": jobs, "total_count": len(jobs)}
        
    except Exception as e:
        logger.error(f"Error listing jobs: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list jobs: {str(e)}")
