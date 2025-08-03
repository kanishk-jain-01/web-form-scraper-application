import asyncio
import logging
from typing import Dict, Any, Optional
from stagehand import Stagehand
from .browserbase import browserbase_service

logger = logging.getLogger(__name__)


class StagehandService:
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.stagehand = None
        self._initialize()

    def _initialize(self):
        """Initialize Stagehand instance"""
        try:
            self.stagehand = Stagehand(
                env="browserbase",
                api_key=browserbase_service.api_key,
                project_id=browserbase_service.project_id,
                session_id=self.session_id
            )
            logger.info(f"Stagehand initialized for session {self.session_id}")
        except Exception as e:
            logger.error(f"Failed to initialize Stagehand: {e}")
            self.stagehand = None

    async def navigate_to_url(self, url: str) -> bool:
        """Navigate to a URL"""
        if not self.stagehand:
            logger.error("Stagehand not initialized")
            return False
        
        try:
            await asyncio.to_thread(self.stagehand.page.goto, url)
            logger.info(f"Navigated to: {url}")
            return True
        except Exception as e:
            logger.error(f"Failed to navigate to {url}: {e}")
            return False

    async def extract_data(self, schema: Optional[Dict] = None) -> Dict[str, Any]:
        """Extract data from current page"""
        if not self.stagehand:
            logger.error("Stagehand not initialized")
            return {}
        
        try:
            # Default schema for form extraction
            default_schema = {
                "type": "object",
                "properties": {
                    "forms": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "form_id": {"type": "string"},
                                "fields": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "name": {"type": "string"},
                                            "type": {"type": "string"},
                                            "selector": {"type": "string"},
                                            "required": {"type": "boolean"},
                                            "placeholder": {"type": "string"},
                                            "options": {"type": "array"}
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
            
            extraction_schema = schema or default_schema
            result = await asyncio.to_thread(
                self.stagehand.extract,
                schema=extraction_schema
            )
            
            logger.info("Data extraction completed")
            return result
            
        except Exception as e:
            logger.error(f"Failed to extract data: {e}")
            return {}

    async def perform_action(self, action: str) -> bool:
        """Perform an action using natural language"""
        if not self.stagehand:
            logger.error("Stagehand not initialized")
            return False
        
        try:
            await asyncio.to_thread(self.stagehand.act, action=action)
            logger.info(f"Performed action: {action}")
            return True
        except Exception as e:
            logger.error(f"Failed to perform action '{action}': {e}")
            return False

    async def observe_page(self, instruction: str = "Analyze the current page") -> Dict[str, Any]:
        """Observe page content"""
        if not self.stagehand:
            logger.error("Stagehand not initialized")
            return {}
        
        try:
            result = await asyncio.to_thread(
                self.stagehand.observe,
                instruction=instruction
            )
            logger.info("Page observation completed")
            return result
        except Exception as e:
            logger.error(f"Failed to observe page: {e}")
            return {}

    def is_ready(self) -> bool:
        """Check if Stagehand is ready"""
        return self.stagehand is not None
