import asyncio
import logging
from typing import Dict, Any, Optional, List
from stagehand import Stagehand
from browser_use import Agent as BrowserUseAgent
from .browserbase_service import browserbase_service

logger = logging.getLogger(__name__)


class BrowserAutomationService:
    def __init__(self):
        self.stagehand = None
        self.browser_use_agent = None
        self.session_id = None
        self.connect_url = None

    async def initialize_session(self) -> bool:
        """Initialize a new browser session"""
        try:
            # Create Browserbase session
            self.session_id = await browserbase_service.create_session()
            if not self.session_id:
                logger.error("Failed to create Browserbase session")
                return False
            
            # Get WebSocket connection URL
            self.connect_url = browserbase_service.get_connect_url(self.session_id)
            if not self.connect_url:
                logger.error("Failed to get WebSocket URL")
                return False
            
            # Initialize Stagehand
            try:
                self.stagehand = Stagehand(
                    env="browserbase",
                    api_key=browserbase_service.api_key,
                    project_id=browserbase_service.project_id,
                    session_id=self.session_id
                )
                logger.info("Stagehand initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Stagehand: {e}")
                self.stagehand = None
            
            # Initialize BrowserUse agent
            try:
                self.browser_use_agent = BrowserUseAgent(
                    task="Web form automation",
                    use_vision=True,
                    browser_type="browserbase",
                    browserbase_api_key=browserbase_service.api_key,
                    browserbase_project_id=browserbase_service.project_id,
                    browserbase_session_id=self.session_id
                )
                logger.info("BrowserUse agent initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize BrowserUse agent: {e}")
                self.browser_use_agent = None
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize browser session: {e}")
            return False

    async def navigate_to_url(self, url: str) -> bool:
        """Navigate to a URL using Stagehand"""
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

    async def extract_form_fields(self, schema: Optional[Dict] = None) -> Dict[str, Any]:
        """Extract form fields from current page using Stagehand"""
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
            
            logger.info("Form fields extracted successfully")
            return result
            
        except Exception as e:
            logger.error(f"Failed to extract form fields: {e}")
            return {}

    async def fill_form_field(self, selector: str, value: str) -> bool:
        """Fill a form field using Stagehand"""
        if not self.stagehand:
            logger.error("Stagehand not initialized")
            return False
        
        try:
            await asyncio.to_thread(
                self.stagehand.act,
                action=f"Fill the field with selector '{selector}' with value '{value}'"
            )
            logger.info(f"Filled field {selector} with value: {value}")
            return True
        except Exception as e:
            logger.error(f"Failed to fill field {selector}: {e}")
            return False

    async def click_element(self, selector: str) -> bool:
        """Click an element using Stagehand"""
        if not self.stagehand:
            logger.error("Stagehand not initialized")
            return False
        
        try:
            await asyncio.to_thread(
                self.stagehand.act,
                action=f"Click the element with selector '{selector}'"
            )
            logger.info(f"Clicked element: {selector}")
            return True
        except Exception as e:
            logger.error(f"Failed to click element {selector}: {e}")
            return False

    async def observe_page(self, instruction: str = "Analyze the current page") -> Dict[str, Any]:
        """Observe page content using Stagehand"""
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

    async def run_browser_use_task(self, task: str) -> Dict[str, Any]:
        """Run a high-level task using BrowserUse agent"""
        if not self.browser_use_agent:
            logger.error("BrowserUse agent not initialized")
            return {}
        
        try:
            result = await asyncio.to_thread(
                self.browser_use_agent.run,
                task=task
            )
            logger.info(f"BrowserUse task completed: {task}")
            return result
        except Exception as e:
            logger.error(f"Failed to run BrowserUse task: {e}")
            return {}

    async def close_session(self):
        """Close the browser session"""
        if self.session_id:
            await browserbase_service.close_session(self.session_id)
            self.session_id = None
            self.connect_url = None
            self.stagehand = None
            self.browser_use_agent = None
            logger.info("Browser session closed")

    def get_session_info(self) -> Dict[str, Any]:
        """Get current session information"""
        return {
            "session_id": self.session_id,
            "connect_url": self.connect_url,
            "stagehand_ready": self.stagehand is not None,
            "browser_use_ready": self.browser_use_agent is not None
        }
