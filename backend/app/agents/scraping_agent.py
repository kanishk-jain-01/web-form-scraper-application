import asyncio
import logging
import uuid
from typing import Dict, Any, List, Optional
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import HumanMessage, AIMessage
from .tools import WebScrapingTools
from ..services.browser_automation import BrowserAutomationService
from ..config import settings
from ..websocket_manager import manager

logger = logging.getLogger(__name__)


class ScrapingAgent:
    def __init__(self, client_id: str):
        self.client_id = client_id
        self.browser_service = BrowserAutomationService()
        self.tools = WebScrapingTools(self.browser_service, client_id)
        self.agent = None
        self.checkpointer = MemorySaver()
        self.thread_id = str(uuid.uuid4())
        
        # Initialize LLM
        self.llm = self._initialize_llm()
        
        # Create the agent
        self._create_agent()

    def _initialize_llm(self):
        """Initialize the LLM based on available API keys"""
        if settings.openai_api_key:
            return ChatOpenAI(
                api_key=settings.openai_api_key,
                model="gpt-4o",
                temperature=0.1
            )
        elif settings.anthropic_api_key:
            return ChatAnthropic(
                api_key=settings.anthropic_api_key,
                model="claude-3-5-sonnet-20241022",
                temperature=0.1
            )
        else:
            logger.warning("No LLM API key provided, using mock LLM")
            return None

    def _create_agent(self):
        """Create the LangGraph ReAct agent"""
        if not self.llm:
            logger.error("Cannot create agent without LLM")
            return
        
        try:
            # Get all tools
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

    async def start_scraping_job(self, url: str, job_config: Optional[Dict] = None) -> Dict[str, Any]:
        """Start a new scraping job"""
        try:
            # Send initial status
            await manager.send_json_message({
                "type": "job_started",
                "message": f"Starting scraping job for {url}",
                "job_id": self.thread_id
            }, self.client_id)
            
            # Initialize browser session
            browser_initialized = await self.browser_service.initialize_session()
            if not browser_initialized:
                error_msg = "Failed to initialize browser session"
                await manager.send_json_message({
                    "type": "job_error",
                    "message": error_msg
                }, self.client_id)
                return {"success": False, "error": error_msg}
            
            # Send browser session info
            session_info = self.browser_service.get_session_info()
            await manager.send_json_message({
                "type": "browser_ready",
                "session_info": session_info
            }, self.client_id)
            
            # Create the initial prompt for the agent
            system_prompt = f"""You are a web scraping AI agent. Your task is to:

1. Navigate to the website: {url}
2. Analyze the page to identify forms and interactive elements
3. Extract form field information and metadata
4. If login is required, identify login forms
5. Fill out forms as needed to access utility information
6. Handle any CAPTCHAs or verification steps by requesting human input
7. Extract the final form data and structure

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
            config = {
                "configurable": {"thread_id": self.thread_id},
                "recursion_limit": 50
            }
            
            # Run the agent
            result = await self._run_agent(messages, config)
            
            return {
                "success": True,
                "job_id": self.thread_id,
                "result": result
            }
            
        except Exception as e:
            error_msg = f"Error starting scraping job: {str(e)}"
            logger.error(error_msg)
            await manager.send_json_message({
                "type": "job_error",
                "message": error_msg
            }, self.client_id)
            return {"success": False, "error": error_msg}

    async def _run_agent(self, messages: List, config: Dict) -> Dict[str, Any]:
        """Run the agent with proper async handling"""
        try:
            # Execute the agent
            response = await asyncio.to_thread(
                self.agent.invoke,
                {"messages": messages},
                config
            )
            
            # Send completion message
            await manager.send_json_message({
                "type": "job_completed",
                "message": "Scraping job completed successfully",
                "final_result": response
            }, self.client_id)
            
            return response
            
        except Exception as e:
            error_msg = f"Agent execution error: {str(e)}"
            logger.error(error_msg)
            await manager.send_json_message({
                "type": "agent_error",
                "message": error_msg
            }, self.client_id)
            return {"error": error_msg}

    async def handle_human_input(self, user_input: str) -> Dict[str, Any]:
        """Handle human input during HITL interrupts"""
        try:
            # Resume agent with human input
            config = {"configurable": {"thread_id": self.thread_id}}
            
            # Add human message and continue
            messages = [HumanMessage(content=f"Human input received: {user_input}")]
            
            response = await asyncio.to_thread(
                self.agent.invoke,
                {"messages": messages},
                config
            )
            
            await manager.send_json_message({
                "type": "human_input_processed",
                "message": "Human input processed, continuing...",
                "response": response
            }, self.client_id)
            
            return response
            
        except Exception as e:
            error_msg = f"Error processing human input: {str(e)}"
            logger.error(error_msg)
            return {"error": error_msg}

    async def get_job_status(self) -> Dict[str, Any]:
        """Get current job status"""
        try:
            session_info = self.browser_service.get_session_info()
            
            return {
                "job_id": self.thread_id,
                "client_id": self.client_id,
                "browser_session": session_info,
                "agent_ready": self.agent is not None,
                "llm_available": self.llm is not None
            }
            
        except Exception as e:
            return {"error": str(e)}

    async def stop_job(self):
        """Stop the current scraping job and cleanup"""
        try:
            await self.browser_service.close_session()
            
            await manager.send_json_message({
                "type": "job_stopped",
                "message": "Scraping job stopped and browser session closed"
            }, self.client_id)
            
            logger.info(f"Scraping job {self.thread_id} stopped")
            
        except Exception as e:
            logger.error(f"Error stopping job: {e}")
