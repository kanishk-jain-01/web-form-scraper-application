from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from ..db import get_db
from typing import AsyncGenerator


async def get_database() -> AsyncGenerator[AsyncSession, None]:
    """Dependency to get database session"""
    try:
        async for session in get_db():
            yield session
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database connection failed: {str(e)}")


def get_current_user():
    """Placeholder for authentication dependency"""
    # TODO: Implement JWT token validation
    return {"user_id": "anonymous", "permissions": ["read", "write"]}
