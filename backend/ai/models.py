"""
Data models and types for AI document generation.

This module contains all the data structures used throughout the AI document
generation system, including input/output models, workflow state, and validation schemas.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, TypedDict
from enum import Enum
from pydantic import BaseModel, Field, validator
import json


class SectionType(Enum):
    """Types of document sections that can be identified and processed."""
    HEADING = "heading"
    PARAGRAPH = "paragraph"
    TABLE = "table"
    LIST = "list"
    CODE_BLOCK = "code_block"
    IMAGE = "image"
    CUSTOM = "custom"


class ValidationStatus(Enum):
    """Status of content validation."""
    PENDING = "pending"
    VALID = "valid"
    INVALID = "invalid"
    WARNING = "warning"


class GenerationStatus(Enum):
    """Status of document generation process."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"


@dataclass
class SectionMetadata:
    """Metadata for a document section."""
    level: int  # For headings, the heading level (1-6)
    tag_name: str  # HTML tag name (h1, p, table, etc.)
    classes: List[str] = field(default_factory=list)
    attributes: Dict[str, str] = field(default_factory=dict)
    word_count: int = 0
    complexity_score: float = 0.0


@dataclass
class DocumentSection:
    """Represents a section of a document that can be processed independently."""
    id: str
    html_content: str
    section_type: SectionType
    metadata: SectionMetadata
    parent_id: Optional[str] = None
    children: List[str] = field(default_factory=list)
    order_index: int = 0


@dataclass
class GeneratedSection:
    """Represents a section after AI generation."""
    section_id: str
    original_html: str
    generated_html: str
    generation_metadata: Dict[str, Any] = field(default_factory=dict)
    validation_status: ValidationStatus = ValidationStatus.PENDING
    error_message: Optional[str] = None
    generation_time_ms: int = 0


@dataclass
class ProjectContext:
    """User-provided context for document generation."""
    project_name: str
    project_description: str
    prompt_text: str
    json_overrides: Dict[str, Any] = field(default_factory=dict)
    strict_vars: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GenerationResult:
    """Result of the document generation process."""
    success: bool
    generated_html: str
    sections_processed: int
    sections_failed: int
    errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    generation_time_ms: int = 0
    status: GenerationStatus = GenerationStatus.PENDING


class WorkflowState(TypedDict):
    """State object for LangGraph workflow."""
    html_template: str
    project_context: ProjectContext
    sections: List[DocumentSection]
    generated_sections: List[GeneratedSection]
    final_html: str
    errors: List[str]
    metadata: Dict[str, Any]
    current_section_index: int
    total_sections: int


# Pydantic models for API validation

class UserInput(BaseModel):
    """Input model for user-provided generation parameters."""
    project_name: str = Field(..., min_length=1, max_length=200)
    project_description: str = Field(..., min_length=1, max_length=1000)
    prompt_text: str = Field(..., min_length=1, max_length=10000)
    json_overrides: Optional[Dict[str, Any]] = Field(default_factory=dict)
    strict_vars: Optional[Dict[str, Any]] = Field(default_factory=dict)

    @validator('json_overrides')
    def validate_json_overrides(cls, v):
        """Validate that json_overrides contains only simple types."""
        if not v:
            return v
        
        def check_simple_types(obj):
            if isinstance(obj, (str, int, float, bool, type(None))):
                return True
            elif isinstance(obj, dict):
                return all(isinstance(k, str) and check_simple_types(v) for k, v in obj.items())
            elif isinstance(obj, list):
                return all(check_simple_types(item) for item in obj)
            return False
        
        if not check_simple_types(v):
            raise ValueError("json_overrides must contain only simple types (str, int, float, bool, None, dict, list)")
        return v


class GenerationRequest(BaseModel):
    """Request model for document generation API."""
    html_template: str = Field(..., min_length=1)
    user_input: UserInput
    document_id: str = Field(..., min_length=1)
    
    @validator('html_template')
    def validate_html_template(cls, v):
        """Basic validation for HTML template."""
        if not v.strip():
            raise ValueError("HTML template cannot be empty")
        # Additional HTML validation can be added here
        return v


class GenerationResponse(BaseModel):
    """Response model for document generation API."""
    success: bool
    generated_html: Optional[str] = None
    sections_processed: int = 0
    sections_failed: int = 0
    errors: List[str] = Field(default_factory=list)
    generation_time_ms: int = 0
    status: GenerationStatus = GenerationStatus.PENDING
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ValidationResult(BaseModel):
    """Result of content validation."""
    is_valid: bool
    status: ValidationStatus
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


# Helper functions for data model operations

def create_project_context_from_input(user_input: UserInput) -> ProjectContext:
    """Convert UserInput to ProjectContext."""
    return ProjectContext(
        project_name=user_input.project_name,
        project_description=user_input.project_description,
        prompt_text=user_input.prompt_text,
        json_overrides=user_input.json_overrides or {},
        strict_vars=user_input.strict_vars or {}
    )


def create_generation_result(
    success: bool,
    generated_html: str = "",
    sections_processed: int = 0,
    sections_failed: int = 0,
    errors: Optional[List[str]] = None,
    metadata: Optional[Dict[str, Any]] = None,
    generation_time_ms: int = 0
) -> GenerationResult:
    """Helper function to create GenerationResult objects."""
    return GenerationResult(
        success=success,
        generated_html=generated_html,
        sections_processed=sections_processed,
        sections_failed=sections_failed,
        errors=errors or [],
        metadata=metadata or {},
        generation_time_ms=generation_time_ms,
        status=GenerationStatus.COMPLETED if success else GenerationStatus.FAILED
    )