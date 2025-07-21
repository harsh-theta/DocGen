from sqlalchemy import Column, String, DateTime, Integer, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from backend.core.database import Base
from sqlalchemy.dialects.postgresql import JSONB

class Document(Base):
    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(255), nullable=False)  # original filename
    stored_filename = Column(String(255), unique=True, nullable=False)
    title = Column(String(255), nullable=True)  # Project name/title
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    type = Column(String(32), default="original")
    status = Column(String(32), default="Uploaded")
    original_file_url = Column(String(512), nullable=False)
    ai_content = Column(Text, nullable=True)
    final_file_url = Column(String(512), nullable=True)
    parsed_structure = Column(Text, nullable=True)
    html_template = Column(Text, nullable=True)  # AI: original HTML template
    ai_generation_metadata = Column(JSONB, nullable=True)  # AI: generation metadata (JSONB)
    generated_sections = Column(JSONB, nullable=True)  # AI: per-section results (JSONB)

    # Optionally, relationship to user
    user = relationship("User", back_populates="documents") 