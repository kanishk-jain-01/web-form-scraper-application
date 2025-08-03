import asyncio
import logging
import uuid
from typing import Dict, Any, Optional, Callable
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import HumanMessage, AIMessage
from .tools import WebScrapingTools
from ..browser.stagehand import StagehandService

from ..config import settings
from ..api.websockets import websocket_manager

logger = logging.getLogger(__name__)


class ScrapingOrchestrator:
    def __init__(self, client_id: str, job_id: str):
        self.client_id = client_id
        self.job_id = job_id
        self.session_id = None
        
        # Browser services
        self.stagehand = None
        
        # Agent components
        self.tools = None
        self.agent = None
        self.checkpointer = MemorySaver()
        self.thread_id = str(uuid.uuid4())
        
        # LLM
        self.llm = self._initialize_llm()

    def _initialize_llm(self):
        """Initialize the LLM based on available API keys"""
        if settings.model_api_key:
            # Default to OpenAI GPT-4o, but could be configured for other models
            return ChatOpenAI(
                api_key=settings.model_api_key,
                model="gpt-4o",
                temperature=0.1
            )
        else:
            logger.warning("No LLM API key provided, using mock LLM")
            return None

    async def _initialize_browser_session(self) -> bool:
        """Initialize browser session and services"""
        try:
            # Initialize browser services with Stagehand
            logger.info("Initializing Stagehand browser session...")
            self.stagehand = await StagehandService.create()
            
            if not self.stagehand.is_ready():
                logger.error("Failed to initialize Stagehand service")
                return False
            
            self.session_id = self.stagehand.session_id
            logger.info(f"Browser session created successfully: {self.session_id}")
            
            # Send session info
            await websocket_manager.send_json_message({
                "type": "browser_ready",
                "session_id": self.session_id,
                "stagehand_ready": self.stagehand.is_ready()
            }, self.client_id)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize browser session: {e}")
            # Make sure session_id is None on failure
            self.session_id = None
            return False

    def _create_agent(self, human_input_callback: Optional[Callable] = None):
        """Create the LangGraph ReAct agent"""
        if not self.llm:
            logger.error("Cannot create agent without LLM")
            return
        
        try:
            # Create tools with browser services
            self.tools = WebScrapingTools(
                stagehand=self.stagehand,
                client_id=self.client_id,
                job_id=self.job_id,
                human_input_callback=human_input_callback
            )
            
            # Get all tools - properly invoke to get tool list
            tools = self.tools.get_all_tools()
            
            # Create ReAct agent with checkpointer for state management
            self.agent = create_react_agent(
                model=self.llm,
                tools=tools,
                checkpointer=self.checkpointer,
                interrupt_before=["tools"]  # Enable HITL interrupts
            )
            
            logger.info("LangGraph agent created successfully")
            
        except Exception as e:
            logger.error(f"Failed to create agent: {e}")

    async def run_scraping_job(
        self,
        url: str,
        config: Optional[Dict] = None,
        human_input_callback: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """Run the complete scraping job"""
        try:
            # Send initial status
            await websocket_manager.send_json_message({
                "type": "job_started",
                "message": f"Starting scraping job for {url}",
                "job_id": self.job_id
            }, self.client_id)
            
            # Initialize browser session
            if not await self._initialize_browser_session():
                error_msg = "Failed to initialize browser session"
                await websocket_manager.send_json_message({
                    "type": "job_error",
                    "message": error_msg
                }, self.client_id)
                return {"success": False, "error": error_msg}
            
            # Create agent
            self._create_agent(human_input_callback)
            if not self.agent:
                error_msg = "Failed to create LangGraph agent"
                await websocket_manager.send_json_message({
                    "type": "job_error",
                    "message": error_msg
                }, self.client_id)
                return {"success": False, "error": error_msg}
            
            # Create the initial prompt for the agent
            system_prompt = f"""You are a web scraping AI agent. Your task is to:

1. Navigate to the website: {url}
2. Analyze the page to identify forms and interactive elements
3. Extract form field information and metadata
4. If login is required, identify login forms
5. Fill out forms as needed to access utility information
6. Handle any CAPTCHAs or verification steps by requesting human input
7. Extract the final form data and structure

Configuration: {config or {}}

Important guidelines:
- Always start by navigating to the URL
- Analyze each page thoroughly before taking actions
- Be patient with page loads and dynamic content
- Request human help for CAPTCHAs, email verification, or unclear situations
- Provide detailed progress updates

Begin by navigating to the website and analyzing its structure."""

            # Start the agent conversation
            messages = [HumanMessage(content=system_prompt)]
            
            # Configure agent execution
            agent_config = {
                "configurable": {"thread_id": self.thread_id},
                "recursion_limit": 50
            }
            
            # Run the agent
            result = await self._run_agent(messages, agent_config)
            
            # Cleanup browser session
            await self._cleanup()
            
            return {
                "success": True,
                "job_id": self.job_id,
                "result": result
            }
            
        except Exception as e:
            error_msg = f"Error running scraping job: {str(e)}"
            logger.error(error_msg)
            await websocket_manager.send_json_message({
                "type": "job_error",
                "message": error_msg
            }, self.client_id)
            
            # Cleanup on error
            await self._cleanup()
            
            return {"success": False, "error": error_msg}

    async def _run_agent(self, messages, config) -> Dict[str, Any]:
        """Run the agent with proper async handling"""
        try:
            # Execute the agent
            response = await asyncio.to_thread(
                self.agent.invoke,
                {"messages": messages},
                config
            )
            
            # Send completion message with serializable data
            serializable_result = self._make_serializable(response)
            await websocket_manager.send_json_message({
                "type": "job_completed",
                "message": "Scraping job completed successfully",
                "final_result": serializable_result
            }, self.client_id)
            
            return response
            
        except Exception as e:
            error_msg = f"Agent execution error: {str(e)}"
            logger.error(error_msg)
            await websocket_manager.send_json_message({
                "type": "agent_error",
                "message": error_msg
            }, self.client_id)
            return {"error": error_msg}

    def _make_serializable(self, obj):
        """Convert LangChain objects to JSON-serializable format"""
        if hasattr(obj, 'dict'):
            # Pydantic model
            return obj.dict()
        elif hasattr(obj, 'content'):
            # LangChain message
            return {
                "type": obj.__class__.__name__,
                "content": obj.content
            }
        elif isinstance(obj, dict):
            return {k: self._make_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, (list, tuple)):
            return [self._make_serializable(item) for item in obj]
        else:
            try:
                # Try to serialize as-is
                import json
                json.dumps(obj)
                return obj
            except (TypeError, ValueError):
                # Fallback to string representation
                return str(obj)

    async def _cleanup(self):
        """Cleanup browser session and resources"""
        try:
            if self.stagehand and self.session_id:
                logger.info(f"Attempting to close browser session: {self.session_id}")
                success = await self.stagehand.close()
                if success:
                    logger.info(f"Browser session {self.session_id} closed successfully")
                else:
                    logger.warning(f"Failed to close browser session {self.session_id}")
                # Reset session ID after cleanup
                self.session_id = None
                self.stagehand = None
            else:
                logger.warning("No Stagehand service or session ID available for cleanup")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            # Reset session ID even on error
            self.session_id = None
            self.stagehand = None
