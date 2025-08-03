from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from .config import settings
import logging

# Base class for models
Base = declarative_base()

# Global variables to hold engine and session
engine = None
async_session = None

logger = logging.getLogger(__name__)


def initialize_db_connection():
    global engine, async_session
    
    try:
        # Convert sync URL to async for asyncpg
        ASYNC_DATABASE_URL = settings.database_url.replace("postgresql://", "postgresql+asyncpg://")
        
        # Create async engine
        engine = create_async_engine(ASYNC_DATABASE_URL, echo=True)
        
        # Create async session factory
        async_session = sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )
        
        logger.info("Database connection initialized successfully")
        return True
        
    except Exception as e:
        logger.warning(f"Could not initialize database connection: {e}")
        logger.info("Running without database - some features will be limited")
        return False


async def get_db():
    if async_session is None:
        raise RuntimeError("Database not initialized")
        
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    """Initialize database tables"""
    if engine is None:
        logger.warning("No database engine available, skipping table creation")
        return
        
    try:
        # Import all models here to ensure they are registered
        from .models import website, form_field, scrape_job
        
        async with engine.begin() as conn:
            # Create all tables
            await conn.run_sync(Base.metadata.create_all)
            
        logger.info("Database tables created successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize database tables: {e}")


# Try to initialize database connection on import
initialize_db_connection()
