import asyncio
import logging
from typing import Dict, Any
from browser_use import Agent as BrowserUseAgent
from .browserbase import browserbase_service

logger = logging.getLogger(__name__)


class BrowserUseService:
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.agent = None
        self._initialize()

    def _initialize(self):
        """Initialize BrowserUse agent"""
        try:
            self.agent = BrowserUseAgent(
                task="Web form automation",
                use_vision=True,
                browser_type="browserbase",
                browserbase_api_key=browserbase_service.api_key,
                browserbase_project_id=browserbase_service.project_id,
                browserbase_session_id=self.session_id
            )
            logger.info(f"BrowserUse agent initialized for session {self.session_id}")
        except Exception as e:
            logger.error(f"Failed to initialize BrowserUse agent: {e}")
            self.agent = None

    async def run_task(self, task_description: str) -> Dict[str, Any]:
        """Run a complex multi-step task"""
        if not self.agent:
            logger.error("BrowserUse agent not initialized")
            return {}
        
        try:
            result = await asyncio.to_thread(
                self.agent.run,
                task=task_description
            )
            logger.info(f"BrowserUse task completed: {task_description}")
            return result
        except Exception as e:
            logger.error(f"Failed to run BrowserUse task: {e}")
            return {}

    def is_ready(self) -> bool:
        """Check if BrowserUse agent is ready"""
        return self.agent is not None
