from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from ..database import Base


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
    metadata = Column(JSONB, default={})
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    website = relationship("Website", back_populates="form_fields")
