import asyncio
import logging
from typing import Dict, Any, Optional, Callable, Type
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field
from ..browser.stagehand import StagehandService

from ..api.websockets import websocket_manager

logger = logging.getLogger(__name__)


class NavigateInput(BaseModel):
    url: str = Field(description="The URL to navigate to")


class NavigateTool(BaseTool):
    name: str = "navigate_to_website"
    description: str = "Navigate to a website URL"
    args_schema: Type[BaseModel] = NavigateInput
    
    stagehand: StagehandService = Field(exclude=True)
    client_id: str = Field(exclude=True)
    job_id: str = Field(exclude=True)
    
    def _run(self, url: str) -> str:
        """Sync wrapper for async method"""
        return asyncio.run(self._arun(url))
    
    async def _arun(self, url: str) -> str:
        try:
            await self.send_progress_update(f"Navigating to {url}")
            
            success = await self.stagehand.navigate_to_url(url)
            if success:
                message = f"Successfully navigated to {url}"
                await self.send_progress_update(message)
                return message
            else:
                error_msg = f"Failed to navigate to {url}"
                await self.send_progress_update(error_msg)
                return error_msg
                
        except Exception as e:
            error_msg = f"Error navigating to {url}: {str(e)}"
            await self.send_progress_update(error_msg)
            return error_msg
    
    async def send_progress_update(self, message: str, data: Optional[Dict] = None):
        try:
            await websocket_manager.send_json_message({
                "type": "agent_progress",
                "message": message,
                "job_id": self.job_id,
                "data": data or {}
            }, self.client_id)
        except Exception as e:
            logger.error(f"Failed to send progress update: {e}")


class AnalyzePageInput(BaseModel):
    instruction: str = Field(default="Analyze the current page for forms and interactive elements", description="Specific instruction for page analysis")


class AnalyzePageTool(BaseTool):
    name: str = "analyze_page_content"
    description: str = "Analyze the current page content to understand forms and structure"
    args_schema: Type[BaseModel] = AnalyzePageInput
    
    stagehand: StagehandService = Field(exclude=True)
    client_id: str = Field(exclude=True)
    job_id: str = Field(exclude=True)
    
    def _run(self, instruction: str = "Analyze the current page for forms and interactive elements") -> Dict[str, Any]:
        """Sync wrapper for async method"""
        return asyncio.run(self._arun(instruction))
    
    async def _arun(self, instruction: str = "Analyze the current page for forms and interactive elements") -> Dict[str, Any]:
        try:
            await self.send_progress_update("Analyzing page content...")
            
            # Use Stagehand to observe the page
            observation = await self.stagehand.observe_page(instruction)
            
            # Extract form fields
            form_data = await self.stagehand.extract_data("Extract all form fields and interactive elements from the current page")
            
            result = {
                "observation": observation,
                "forms": form_data,
                "page_analyzed": True
            }
            
            await self.send_progress_update("Page analysis completed", result)
            return result
            
        except Exception as e:
            error_msg = f"Error analyzing page: {str(e)}"
            await self.send_progress_update(error_msg)
            return {"error": error_msg, "page_analyzed": False}
    
    async def send_progress_update(self, message: str, data: Optional[Dict] = None):
        try:
            await websocket_manager.send_json_message({
                "type": "agent_progress",
                "message": message,
                "job_id": self.job_id,
                "data": data or {}
            }, self.client_id)
        except Exception as e:
            logger.error(f"Failed to send progress update: {e}")


class FillFormInput(BaseModel):
    field_data: Dict[str, str] = Field(description="Dictionary mapping field selectors to values")


class FillFormTool(BaseTool):
    name: str = "fill_form_fields"
    description: str = "Fill form fields with provided data"
    args_schema: Type[BaseModel] = FillFormInput
    
    stagehand: StagehandService = Field(exclude=True)
    client_id: str = Field(exclude=True)
    job_id: str = Field(exclude=True)
    
    def _run(self, field_data: Dict[str, str]) -> Dict[str, Any]:
        """Sync wrapper for async method"""
        return asyncio.run(self._arun(field_data))
    
    async def _arun(self, field_data: Dict[str, str]) -> Dict[str, Any]:
        try:
            await self.send_progress_update("Filling form fields...")
            
            results = {}
            for selector, value in field_data.items():
                try:
                    success = await self.stagehand.perform_action(f"Fill the field with selector '{selector}' with value '{value}'")
                    results[selector] = {
                        "success": success,
                        "value": value,
                        "error": None if success else "Failed to fill field"
                    }
                    
                    if success:
                        await self.send_progress_update(f"Filled field: {selector}")
                    else:
                        await self.send_progress_update(f"Failed to fill field: {selector}")
                        
                except Exception as e:
                    results[selector] = {
                        "success": False,
                        "value": value,
                        "error": str(e)
                    }
                    await self.send_progress_update(f"Error filling field {selector}: {str(e)}")
            
            return {
                "fields_filled": results,
                "total_fields": len(field_data),
                "successful_fields": sum(1 for r in results.values() if r["success"])
            }
            
        except Exception as e:
            error_msg = f"Error filling form fields: {str(e)}"
            await self.send_progress_update(error_msg)
            return {"error": error_msg}
    
    async def send_progress_update(self, message: str, data: Optional[Dict] = None):
        try:
            await websocket_manager.send_json_message({
                "type": "agent_progress",
                "message": message,
                "job_id": self.job_id,
                "data": data or {}
            }, self.client_id)
        except Exception as e:
            logger.error(f"Failed to send progress update: {e}")


class ClickElementInput(BaseModel):
    selector: str = Field(description="CSS selector or description of element to click")
    description: str = Field(default="", description="Human-readable description of what we're clicking")


class ClickElementTool(BaseTool):
    name: str = "click_element"
    description: str = "Click an element on the page"
    args_schema: Type[BaseModel] = ClickElementInput
    
    stagehand: StagehandService = Field(exclude=True)
    client_id: str = Field(exclude=True)
    job_id: str = Field(exclude=True)
    
    def _run(self, selector: str, description: str = "") -> str:
        """Sync wrapper for async method"""
        return asyncio.run(self._arun(selector, description))
    
    async def _arun(self, selector: str, description: str = "") -> str:
        try:
            action_desc = description or f"element {selector}"
            await self.send_progress_update(f"Clicking {action_desc}")
            
            success = await self.stagehand.perform_action(f"Click the element with selector '{selector}'")
            if success:
                message = f"Successfully clicked {action_desc}"
                await self.send_progress_update(message)
                return message
            else:
                error_msg = f"Failed to click {action_desc}"
                await self.send_progress_update(error_msg)
                return error_msg
                
        except Exception as e:
            error_msg = f"Error clicking {selector}: {str(e)}"
            await self.send_progress_update(error_msg)
            return error_msg
    
    async def send_progress_update(self, message: str, data: Optional[Dict] = None):
        try:
            await websocket_manager.send_json_message({
                "type": "agent_progress",
                "message": message,
                "job_id": self.job_id,
                "data": data or {}
            }, self.client_id)
        except Exception as e:
            logger.error(f"Failed to send progress update: {e}")


class HumanInputInput(BaseModel):
    prompt: str = Field(description="Message to display to the human")
    input_type: str = Field(default="text", description="Type of input needed (text, confirmation, etc.)")


class HumanInputTool(BaseTool):
    name: str = "request_human_input"
    description: str = "Request human input for CAPTCHA, verification, or other manual steps"
    args_schema: Type[BaseModel] = HumanInputInput
    
    stagehand: StagehandService = Field(exclude=True)
    client_id: str = Field(exclude=True)
    job_id: str = Field(exclude=True)
    human_input_callback: Optional[Callable] = Field(exclude=True)
    
    def _run(self, prompt: str, input_type: str = "text") -> str:
        """Sync wrapper for async method"""
        return asyncio.run(self._arun(prompt, input_type))
    
    async def _arun(self, prompt: str, input_type: str = "text") -> str:
        try:
            await self.send_progress_update("Human input required", {
                "requires_human_input": True,
                "prompt": prompt,
                "input_type": input_type
            })
            
            # Request human input via callback if available
            if self.human_input_callback:
                response = await self.human_input_callback()
                await self.send_progress_update("Human input received, continuing...")
                return response
            else:
                # Fallback placeholder
                return "HUMAN_INPUT_PENDING"
            
        except Exception as e:
            error_msg = f"Error requesting human input: {str(e)}"
            await self.send_progress_update(error_msg)
            return error_msg
    
    async def send_progress_update(self, message: str, data: Optional[Dict] = None):
        try:
            await websocket_manager.send_json_message({
                "type": "agent_progress",
                "message": message,
                "job_id": self.job_id,
                "data": data or {}
            }, self.client_id)
        except Exception as e:
            logger.error(f"Failed to send progress update: {e}")


class ComplexTaskInput(BaseModel):
    task_description: str = Field(description="Natural language description of the task to perform")


class ComplexTaskTool(BaseTool):
    name: str = "run_complex_task"
    description: str = "Run a complex multi-step task using Stagehand's act method"
    args_schema: Type[BaseModel] = ComplexTaskInput
    
    stagehand: StagehandService = Field(exclude=True)
    client_id: str = Field(exclude=True)
    job_id: str = Field(exclude=True)
    
    def _run(self, task_description: str) -> Dict[str, Any]:
        """Sync wrapper for async method"""
        return asyncio.run(self._arun(task_description))
    
    async def _arun(self, task_description: str) -> Dict[str, Any]:
        try:
            await self.send_progress_update(f"Running complex task: {task_description}")
            
            success = await self.stagehand.perform_action(task_description)
            if success:
                result = {
                    "success": True,
                    "task": task_description,
                    "message": "Task completed successfully"
                }
                await self.send_progress_update("Complex task completed")
                return result
            else:
                result = {
                    "success": False,
                    "task": task_description,
                    "error": "Task execution failed"
                }
                await self.send_progress_update("Complex task failed")
                return result
                
        except Exception as e:
            error_msg = f"Error running complex task: {str(e)}"
            await self.send_progress_update(error_msg)
            return {"success": False, "error": error_msg}
    
    async def send_progress_update(self, message: str, data: Optional[Dict] = None):
        try:
            await websocket_manager.send_json_message({
                "type": "agent_progress",
                "message": message,
                "job_id": self.job_id,
                "data": data or {}
            }, self.client_id)
        except Exception as e:
            logger.error(f"Failed to send progress update: {e}")


class WebScrapingTools:
    def __init__(
        self,
        stagehand: StagehandService,
        client_id: str,
        job_id: str,
        human_input_callback: Optional[Callable] = None
    ):
        self.stagehand = stagehand
        self.client_id = client_id
        self.job_id = job_id
        self.human_input_callback = human_input_callback

    def get_all_tools(self):
        """Get all available tools for the agent"""
        return [
            NavigateTool(
                stagehand=self.stagehand,
                client_id=self.client_id,
                job_id=self.job_id
            ),
            AnalyzePageTool(
                stagehand=self.stagehand,
                client_id=self.client_id,
                job_id=self.job_id
            ),
            FillFormTool(
                stagehand=self.stagehand,
                client_id=self.client_id,
                job_id=self.job_id
            ),
            ClickElementTool(
                stagehand=self.stagehand,
                client_id=self.client_id,
                job_id=self.job_id
            ),
            HumanInputTool(
                stagehand=self.stagehand,
                client_id=self.client_id,
                job_id=self.job_id,
                human_input_callback=self.human_input_callback
            ),
            ComplexTaskTool(
                stagehand=self.stagehand,
                client_id=self.client_id,
                job_id=self.job_id
            )
        ]
