import asyncio
import logging
from typing import Optional, Dict, Any
from browserbase import Browserbase
from ..config import settings

logger = logging.getLogger(__name__)


class BrowserbaseService:
    def __init__(self):
        self.client = None
        self.project_id = settings.browserbase_project_id
        self.api_key = settings.browserbase_api_key
        
        if self.api_key and self.project_id:
            try:
                self.client = Browserbase(api_key=self.api_key)
                logger.info("Browserbase client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Browserbase client: {e}")
        else:
            logger.warning("Browserbase API key or project ID not provided")

    async def create_session(self, **kwargs) -> Optional[str]:
        """Create a new browser session"""
        if not self.client:
            logger.error("Browserbase client not initialized")
            return None
        
        try:
            session = await asyncio.to_thread(
                self.client.sessions.create,
                project_id=self.project_id,
                **kwargs
            )
            logger.info(f"Created Browserbase session: {session.id}")
            return session.id
        except Exception as e:
            logger.error(f"Failed to create Browserbase session: {e}")
            return None

    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session information"""
        if not self.client:
            return None
        
        try:
            session = await asyncio.to_thread(
                self.client.sessions.retrieve,
                session_id
            )
            return {
                "id": session.id,
                "status": session.status,
                "created_at": session.created_at,
                "project_id": session.project_id
            }
        except Exception as e:
            logger.error(f"Failed to get session {session_id}: {e}")
            return None

    async def close_session(self, session_id: str) -> bool:
        """Close a browser session"""
        if not self.client:
            return False
        
        try:
            await asyncio.to_thread(
                self.client.sessions.delete,
                session_id
            )
            logger.info(f"Closed Browserbase session: {session_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to close session {session_id}: {e}")
            return False

    def get_connect_url(self, session_id: str) -> Optional[str]:
        """Get WebSocket URL for connecting to session"""
        if not session_id:
            return None
        
        # Browserbase WebSocket URL format
        return f"wss://connect.browserbase.com?apiKey={self.api_key}&sessionId={session_id}"

    def is_available(self) -> bool:
        """Check if Browserbase service is available"""
        return self.client is not None


# Global instance
browserbase_service = BrowserbaseService()
