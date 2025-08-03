from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from ..database import Base


class ScrapeJob(Base):
    __tablename__ = "scrape_jobs"

    id = Column(Integer, primary_key=True, index=True)
    website_id = Column(Integer, ForeignKey("websites.id"), nullable=False)
    job_id = Column(String, unique=True, index=True, nullable=False)
    target_url = Column(String, nullable=False)
    status = Column(String, default="pending")  # pending, running, completed, failed, interrupted
    current_action = Column(String, nullable=True)
    progress_percentage = Column(Integer, default=0)
    form_data = Column(JSONB, default={})
    error_message = Column(Text, nullable=True)
    agent_state = Column(JSONB, default={})
    requires_human_input = Column(Boolean, default=False)
    human_input_prompt = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    website = relationship("Website", back_populates="scrape_jobs")
