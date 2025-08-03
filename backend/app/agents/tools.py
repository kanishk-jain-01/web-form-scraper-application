import asyncio
import logging
from typing import Dict, Any, Optional, Callable
from langchain.tools import tool
from ..browser.stagehand import StagehandService
from ..browser.browseruse import BrowserUseService
from ..api.websockets import websocket_manager

logger = logging.getLogger(__name__)


class WebScrapingTools:
    def __init__(
        self, 
        stagehand: StagehandService, 
        browseruse: BrowserUseService,
        client_id: str,
        job_id: str,
        human_input_callback: Optional[Callable] = None
    ):
        self.stagehand = stagehand
        self.browseruse = browseruse
        self.client_id = client_id
        self.job_id = job_id
        self.human_input_callback = human_input_callback

    async def send_progress_update(self, message: str, data: Optional[Dict] = None):
        """Send progress update to frontend via WebSocket"""
        try:
            await websocket_manager.send_json_message({
                "type": "agent_progress",
                "message": message,
                "job_id": self.job_id,
                "data": data or {}
            }, self.client_id)
        except Exception as e:
            logger.error(f"Failed to send progress update: {e}")

    @tool
    async def navigate_to_website(self, url: str) -> str:
        """Navigate to a website URL.
        
        Args:
            url: The URL to navigate to
            
        Returns:
            Success message or error details
        """
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

    @tool
    async def analyze_page_content(self, instruction: str = "Analyze the current page for forms and interactive elements") -> Dict[str, Any]:
        """Analyze the current page content to understand forms and structure.
        
        Args:
            instruction: Specific instruction for page analysis
            
        Returns:
            Page analysis results including forms, fields, and structure
        """
        try:
            await self.send_progress_update("Analyzing page content...")
            
            # Use Stagehand to observe the page
            observation = await self.stagehand.observe_page(instruction)
            
            # Extract form fields
            form_data = await self.stagehand.extract_data()
            
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

    @tool
    async def fill_form_fields(self, field_data: Dict[str, str]) -> Dict[str, Any]:
        """Fill form fields with provided data.
        
        Args:
            field_data: Dictionary mapping field selectors to values
            
        Returns:
            Results of filling each field
        """
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

    @tool
    async def click_element(self, selector: str, description: str = "") -> str:
        """Click an element on the page.
        
        Args:
            selector: CSS selector or description of element to click
            description: Human-readable description of what we're clicking
            
        Returns:
            Success message or error details
        """
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

    @tool
    async def request_human_input(self, prompt: str, input_type: str = "text") -> str:
        """Request human input for CAPTCHA, verification, or other manual steps.
        
        Args:
            prompt: Message to display to the human
            input_type: Type of input needed (text, confirmation, etc.)
            
        Returns:
            The human's response
        """
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

    @tool
    async def run_complex_task(self, task_description: str) -> Dict[str, Any]:
        """Run a complex multi-step task using BrowserUse agent.
        
        Args:
            task_description: Description of the task to perform
            
        Returns:
            Task execution results
        """
        try:
            await self.send_progress_update(f"Running complex task: {task_description}")
            
            result = await self.browseruse.run_task(task_description)
            
            await self.send_progress_update("Complex task completed", result)
            return result
            
        except Exception as e:
            error_msg = f"Error running complex task: {str(e)}"
            await self.send_progress_update(error_msg)
            return {"error": error_msg}

    def get_all_tools(self):
        """Get all available tools for the agent"""
        return [
            self.navigate_to_website,
            self.analyze_page_content,
            self.fill_form_fields,
            self.click_element,
            self.request_human_input,
            self.run_complex_task
        ]
