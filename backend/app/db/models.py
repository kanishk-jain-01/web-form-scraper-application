from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .session import Base


class Website(Base):
    __tablename__ = "websites"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    base_url = Column(String, nullable=False)
    login_required = Column(Boolean, default=False)
    login_url = Column(String, nullable=True)
    metadata_json = Column("metadata", JSONB, default={})
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    form_fields = relationship("FormField", back_populates="website")
    scrape_jobs = relationship("ScrapeJob", back_populates="website")


class FormField(Base):
    __tablename__ = "form_fields"

    id = Column(Integer, primary_key=True, index=True)
    website_id = Column(Integer, ForeignKey("websites.id"), nullable=False)
    field_name = Column(String, nullable=False)
    field_type = Column(String, nullable=False)  # text, email, password, select, etc.
    selector = Column(String, nullable=False)  # CSS selector or XPath
    required = Column(Boolean, default=False)
    max_length = Column(Integer, nullable=True)
    options = Column(JSONB, default=[])  # For select fields
    validation_rules = Column(JSONB, default={})
    metadata_json = Column("metadata", JSONB, default={})
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    website = relationship("Website", back_populates="form_fields")


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
