from sqlalchemy import Column, String, DateTime, Integer, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from backend.core.database import Base

class Document(Base):
    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(255), nullable=False)  # original filename
    stored_filename = Column(String(255), unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    type = Column(String(32), default="original")
    status = Column(String(32), default="Uploaded")
    original_file_url = Column(String(512), nullable=False)
    ai_content = Column(Text, nullable=True)
    final_file_url = Column(String(512), nullable=True)
    parsed_structure = Column(Text, nullable=True)

    # Optionally, relationship to user
    user = relationship("User", back_populates="documents") 