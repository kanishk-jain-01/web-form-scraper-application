import asyncio
import logging
import os
from typing import Dict, Any, Optional, List
from dotenv import load_dotenv
from stagehand import StagehandConfig, Stagehand
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# Load env vars once at module level if needed
load_dotenv()

# Pydantic models for extraction schema
class FormField(BaseModel):
    name: str
    type: str
    selector: str
    required: bool
    placeholder: str
    options: List[str] = []

class FormData(BaseModel):
    formId: str  # Changed from form_id to match Stagehand output
    fields: List[FormField]

class ExtractedData(BaseModel):
    forms: List[FormData]

class StagehandService:
    def __init__(self):
        self.stagehand = None
        self.session_id = None
        self._initialized = False

    @classmethod
    async def create(cls):
        """Create and initialize a StagehandService instance"""
        instance = cls()
        await instance._initialize()
        return instance

    async def _initialize(self):
        """Initialize Stagehand instance with BrowserBase config"""
        try:
            config = StagehandConfig(
                env="BROWSERBASE",  # Or "LOCAL" for development (no BrowserBase needed)
                api_key=os.getenv("BROWSERBASE_API_KEY"),
                project_id=os.getenv("BROWSERBASE_PROJECT_ID"),
                model_name="gpt-4o",  # Change to your preferred model, e.g., "google/gemini-2.5-flash-preview-05-20"
                model_api_key=os.getenv("MODEL_API_KEY")  
            )
            self.stagehand = Stagehand(config)
            await self.stagehand.init()
            self.session_id = self.stagehand.session_id
            self._initialized = True
            
            if self.stagehand.env == "BROWSERBASE":
                logger.info(f"View live browser: https://www.browserbase.com/sessions/{self.session_id}")
            
            logger.info(f"Stagehand initialized with session {self.session_id}")
        except Exception as e:
            logger.error(f"Failed to initialize Stagehand: {e}")
            self.stagehand = None
            self._initialized = False

    async def navigate_to_url(self, url: str) -> bool:
        if not self.stagehand:
            logger.error("Stagehand not initialized")
            return False
        try:
            await self.stagehand.page.goto(url)
            logger.info(f"Navigated to: {url}")
            return True
        except Exception as e:
            logger.error(f"Failed to navigate to {url}: {e}")
            return False

    async def extract_data(self, instruction: str, schema: Optional[type[BaseModel]] = None) -> Dict[str, Any]:
        if not self.stagehand:
            logger.error("Stagehand not initialized")
            return {}
        try:
            # Use Pydantic model as schema (Stagehand expects this)
            schema_to_use = schema or ExtractedData
            
            result = await self.stagehand.page.extract(
                instruction=instruction,
                schema=schema_to_use
            )
            
            logger.info("Data extraction completed")
            
            # Check if validation failed and raw data is in .data field
            if hasattr(result, 'data'):
                return result.data
            
            # Convert Pydantic model to dict if needed
            if hasattr(result, 'model_dump'):
                return result.model_dump()
            elif hasattr(result, 'dict'):
                return result.dict()
            else:
                return result
                
        except Exception as e:
            logger.error(f"Failed to extract data: {e}")
            return {}

    async def perform_action(self, action: str) -> bool:
        if not self.stagehand:
            logger.error("Stagehand not initialized")
            return False
        try:
            await self.stagehand.page.act(action=action)
            logger.info(f"Performed action: {action}")
            return True
        except Exception as e:
            logger.error(f"Failed to perform action '{action}': {e}")
            return False

    async def observe_page(self, instruction: str = "Analyze the current page") -> Dict[str, Any]:
        if not self.stagehand:
            logger.error("Stagehand not initialized")
            return {}
        try:
            result = await self.stagehand.page.observe(instruction=instruction)
            logger.info("Page observation completed")
            return result
        except Exception as e:
            logger.error(f"Failed to observe page: {e}")
            return {}

    async def close(self) -> bool:
        """Close the Stagehand session"""
        if not self.stagehand:
            return False
        try:
            await self.stagehand.close()
            logger.info(f"Closed Stagehand session: {self.session_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to close session: {e}")
            return False

    def is_ready(self) -> bool:
        """Check if Stagehand is ready"""
        return self._initialized and self.stagehand is not None and self.session_id is not None
