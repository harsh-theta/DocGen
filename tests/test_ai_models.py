"""
Unit tests for AI data models and types.
"""

import pytest
from pydantic import ValidationError
from backend.ai.models import (
    SectionType, ValidationStatus, GenerationStatus,
    SectionMetadata, DocumentSection, GeneratedSection,
    ProjectContext, GenerationResult, WorkflowState,
    UserInput, GenerationRequest, GenerationResponse,
    ValidationResult, create_project_context_from_input,
    create_generation_result
)
from backend.ai.context_handler import ProjectContextHandler
from unittest.mock import AsyncMock, patch
from backend.ai.workflow import DocumentGenerationWorkflow


class TestEnums:
    """Test enum classes."""
    
    def test_section_type_enum(self):
        """Test SectionType enum values."""
        assert SectionType.HEADING.value == "heading"
        assert SectionType.PARAGRAPH.value == "paragraph"
        assert SectionType.TABLE.value == "table"
        assert SectionType.LIST.value == "list"
        assert SectionType.CODE_BLOCK.value == "code_block"
        assert SectionType.IMAGE.value == "image"
        assert SectionType.CUSTOM.value == "custom"
    
    def test_validation_status_enum(self):
        """Test ValidationStatus enum values."""
        assert ValidationStatus.PENDING.value == "pending"
        assert ValidationStatus.VALID.value == "valid"
        assert ValidationStatus.INVALID.value == "invalid"
        assert ValidationStatus.WARNING.value == "warning"
    
    def test_generation_status_enum(self):
        """Test GenerationStatus enum values."""
        assert GenerationStatus.PENDING.value == "pending"
        assert GenerationStatus.IN_PROGRESS.value == "in_progress"
        assert GenerationStatus.COMPLETED.value == "completed"
        assert GenerationStatus.FAILED.value == "failed"
        assert GenerationStatus.PARTIAL.value == "partial"


class TestDataClasses:
    """Test dataclass models."""
    
    def test_section_metadata_creation(self):
        """Test SectionMetadata creation and defaults."""
        metadata = SectionMetadata(level=1, tag_name="h1")
        assert metadata.level == 1
        assert metadata.tag_name == "h1"
        assert metadata.classes == []
        assert metadata.attributes == {}
        assert metadata.word_count == 0
        assert metadata.complexity_score == 0.0
    
    def test_document_section_creation(self):
        """Test DocumentSection creation."""
        metadata = SectionMetadata(level=1, tag_name="h1")
        section = DocumentSection(
            id="section-1",
            html_content="<h1>Test</h1>",
            section_type=SectionType.HEADING,
            metadata=metadata
        )
        assert section.id == "section-1"
        assert section.html_content == "<h1>Test</h1>"
        assert section.section_type == SectionType.HEADING
        assert section.metadata == metadata
        assert section.parent_id is None
        assert section.children == []
        assert section.order_index == 0
    
    def test_generated_section_creation(self):
        """Test GeneratedSection creation."""
        section = GeneratedSection(
            section_id="section-1",
            original_html="<h1>Original</h1>",
            generated_html="<h1>Generated</h1>"
        )
        assert section.section_id == "section-1"
        assert section.original_html == "<h1>Original</h1>"
        assert section.generated_html == "<h1>Generated</h1>"
        assert section.generation_metadata == {}
        assert section.validation_status == ValidationStatus.PENDING
        assert section.error_message is None
        assert section.generation_time_ms == 0
    
    def test_project_context_creation(self):
        """Test ProjectContext creation."""
        context = ProjectContext(
            project_name="Test Project",
            project_description="A test project",
            prompt_text="Generate a document for testing"
        )
        assert context.project_name == "Test Project"
        assert context.project_description == "A test project"
        assert context.prompt_text == "Generate a document for testing"
        assert context.json_overrides == {}
        assert context.strict_vars == {}
    
    def test_generation_result_creation(self):
        """Test GenerationResult creation."""
        result = GenerationResult(
            success=True,
            generated_html="<html>Generated content</html>",
            sections_processed=5,
            sections_failed=0
        )
        assert result.success is True
        assert result.generated_html == "<html>Generated content</html>"
        assert result.sections_processed == 5
        assert result.sections_failed == 0
        assert result.errors == []
        assert result.metadata == {}
        assert result.generation_time_ms == 0
        assert result.status == GenerationStatus.PENDING


class TestPydanticModels:
    """Test Pydantic validation models."""
    
    def test_user_input_valid(self):
        """Test valid UserInput creation."""
        user_input = UserInput(
            project_name="Test Project",
            project_description="A test project description",
            prompt_text="Generate a document about testing"
        )
        assert user_input.project_name == "Test Project"
        assert user_input.project_description == "A test project description"
        assert user_input.prompt_text == "Generate a document about testing"
        assert user_input.json_overrides == {}
        assert user_input.strict_vars == {}
    
    def test_user_input_with_overrides(self):
        """Test UserInput with json_overrides."""
        user_input = UserInput(
            project_name="Test Project",
            project_description="A test project description",
            prompt_text="Generate a document about testing",
            json_overrides={"frontend": "React", "backend": "FastAPI"},
            strict_vars={"version": "1.0"}
        )
        assert user_input.json_overrides == {"frontend": "React", "backend": "FastAPI"}
        assert user_input.strict_vars == {"version": "1.0"}
    
    def test_user_input_validation_errors(self):
        """Test UserInput validation errors."""
        # Test empty project name
        with pytest.raises(ValidationError):
            UserInput(
                project_name="",
                project_description="A test project description",
                prompt_text="Generate a document about testing"
            )
        
        # Test project name too long
        with pytest.raises(ValidationError):
            UserInput(
                project_name="x" * 201,  # Too long
                project_description="A test project description",
                prompt_text="Generate a document about testing"
            )
        
        # Test empty description
        with pytest.raises(ValidationError):
            UserInput(
                project_name="Test Project",
                project_description="",
                prompt_text="Generate a document about testing"
            )
        
        # Test empty prompt
        with pytest.raises(ValidationError):
            UserInput(
                project_name="Test Project",
                project_description="A test project description",
                prompt_text=""
            )
    
    def test_user_input_json_overrides_validation(self):
        """Test json_overrides validation."""
        # Valid simple types
        user_input = UserInput(
            project_name="Test Project",
            project_description="A test project description",
            prompt_text="Generate a document about testing",
            json_overrides={
                "string_val": "test",
                "int_val": 42,
                "float_val": 3.14,
                "bool_val": True,
                "null_val": None,
                "dict_val": {"nested": "value"},
                "list_val": [1, 2, 3]
            }
        )
        assert user_input.json_overrides["string_val"] == "test"
        assert user_input.json_overrides["int_val"] == 42
    
    def test_generation_request_valid(self):
        """Test valid GenerationRequest creation."""
        user_input = UserInput(
            project_name="Test Project",
            project_description="A test project description",
            prompt_text="Generate a document about testing"
        )
        request = GenerationRequest(
            html_template="<h1>Template</h1>",
            user_input=user_input,
            document_id="doc-123"
        )
        assert request.html_template == "<h1>Template</h1>"
        assert request.user_input == user_input
        assert request.document_id == "doc-123"
    
    def test_generation_request_validation_errors(self):
        """Test GenerationRequest validation errors."""
        user_input = UserInput(
            project_name="Test Project",
            project_description="A test project description",
            prompt_text="Generate a document about testing"
        )
        
        # Test empty HTML template
        with pytest.raises(ValidationError):
            GenerationRequest(
                html_template="",
                user_input=user_input,
                document_id="doc-123"
            )
        
        # Test empty document ID
        with pytest.raises(ValidationError):
            GenerationRequest(
                html_template="<h1>Template</h1>",
                user_input=user_input,
                document_id=""
            )
    
    def test_generation_response_creation(self):
        """Test GenerationResponse creation."""
        response = GenerationResponse(
            success=True,
            generated_html="<h1>Generated</h1>",
            sections_processed=3,
            sections_failed=0,
            generation_time_ms=1500,
            status=GenerationStatus.COMPLETED
        )
        assert response.success is True
        assert response.generated_html == "<h1>Generated</h1>"
        assert response.sections_processed == 3
        assert response.sections_failed == 0
        assert response.generation_time_ms == 1500
        assert response.status == GenerationStatus.COMPLETED
        assert response.errors == []
        assert response.metadata == {}
    
    def test_validation_result_creation(self):
        """Test ValidationResult creation."""
        result = ValidationResult(
            is_valid=True,
            status=ValidationStatus.VALID
        )
        assert result.is_valid is True
        assert result.status == ValidationStatus.VALID
        assert result.errors == []
        assert result.warnings == []
        assert result.metadata == {}


class TestHelperFunctions:
    """Test helper functions."""
    
    def test_create_project_context_from_input(self):
        """Test create_project_context_from_input function."""
        user_input = UserInput(
            project_name="Test Project",
            project_description="A test project description",
            prompt_text="Generate a document about testing",
            json_overrides={"frontend": "React"},
            strict_vars={"version": "1.0"}
        )
        
        context = create_project_context_from_input(user_input)
        
        assert context.project_name == "Test Project"
        assert context.project_description == "A test project description"
        assert context.prompt_text == "Generate a document about testing"
        assert context.json_overrides == {"frontend": "React"}
        assert context.strict_vars == {"version": "1.0"}
    
    def test_create_generation_result_success(self):
        """Test create_generation_result for successful generation."""
        result = create_generation_result(
            success=True,
            generated_html="<h1>Success</h1>",
            sections_processed=5,
            sections_failed=0,
            generation_time_ms=2000
        )
        
        assert result.success is True
        assert result.generated_html == "<h1>Success</h1>"
        assert result.sections_processed == 5
        assert result.sections_failed == 0
        assert result.generation_time_ms == 2000
        assert result.status == GenerationStatus.COMPLETED
        assert result.errors == []
        assert result.metadata == {}
    
    def test_create_generation_result_failure(self):
        """Test create_generation_result for failed generation."""
        result = create_generation_result(
            success=False,
            sections_processed=3,
            sections_failed=2,
            errors=["Error 1", "Error 2"],
            metadata={"attempt": 1}
        )
        
        assert result.success is False
        assert result.generated_html == ""
        assert result.sections_processed == 3
        assert result.sections_failed == 2
        assert result.errors == ["Error 1", "Error 2"]
        assert result.metadata == {"attempt": 1}
        assert result.status == GenerationStatus.FAILED


class TestWorkflowState:
    """Test WorkflowState TypedDict."""
    
    def test_workflow_state_structure(self):
        """Test WorkflowState can be created with proper structure."""
        context = ProjectContext(
            project_name="Test",
            project_description="Test desc",
            prompt_text="Test prompt"
        )
        
        # This tests that the TypedDict structure is correct
        state: WorkflowState = {
            "html_template": "<h1>Template</h1>",
            "project_context": context,
            "sections": [],
            "generated_sections": [],
            "final_html": "",
            "errors": [],
            "metadata": {},
            "current_section_index": 0,
            "total_sections": 0
        }
        
        assert state["html_template"] == "<h1>Template</h1>"
        assert state["project_context"] == context
        assert state["sections"] == []
        assert state["generated_sections"] == []
        assert state["final_html"] == ""
        assert state["errors"] == []
        assert state["metadata"] == {}
        assert state["current_section_index"] == 0
        assert state["total_sections"] == 0


class TestProjectContextHandler:
    def test_extract_json_overrides_valid(self):
        prompt = "We're building a fintech app... {\n  \"frontend\": \"Next.js\", \"auth_method\": \"OAuth2\"\n}"
        result = ProjectContextHandler.extract_json_overrides(prompt)
        assert result == {"frontend": "Next.js", "auth_method": "OAuth2"}

    def test_extract_json_overrides_none(self):
        prompt = "No JSON here, just text."
        result = ProjectContextHandler.extract_json_overrides(prompt)
        assert result == {}

    def test_extract_json_overrides_malformed(self):
        prompt = "Some text {not: valid, json}"
        result = ProjectContextHandler.extract_json_overrides(prompt)
        assert result == {}

    def test_sanitize_input(self):
        text = "   Hello   world!  "
        assert ProjectContextHandler.sanitize_input(text) == "Hello world!"
        assert ProjectContextHandler.sanitize_input("") == ""

    def test_build_project_context_prefers_explicit_overrides(self):
        user_input = UserInput(
            project_name="Test",
            project_description="Desc",
            prompt_text="Prompt {\"foo\": \"bar\"}",
            json_overrides={"explicit": True},
            strict_vars={"x": 1}
        )
        context = ProjectContextHandler.build_project_context(user_input)
        assert context.json_overrides == {"explicit": True}
        assert context.strict_vars == {"x": 1}

    def test_build_project_context_extracts_from_prompt(self):
        user_input = UserInput(
            project_name="Test",
            project_description="Desc",
            prompt_text="Prompt {\"foo\": \"bar\"}",
            json_overrides={},
            strict_vars={}
        )
        context = ProjectContextHandler.build_project_context(user_input)
        assert context.json_overrides == {"foo": "bar"}

    def test_validate_project_context(self):
        context = ProjectContext(
            project_name="Test",
            project_description="Desc",
            prompt_text="Prompt"
        )
        assert ProjectContextHandler.validate_project_context(context) is None
        context.project_name = ""
        assert ProjectContextHandler.validate_project_context(context) == "Project name is required."
        context.project_name = "Test"
        context.project_description = ""
        assert ProjectContextHandler.validate_project_context(context) == "Project description is required."
        context.project_description = "Desc"
        context.prompt_text = ""
        assert ProjectContextHandler.validate_project_context(context) == "Prompt text is required."


@pytest.mark.asyncio
async def test_document_generation_workflow_success():
    html_template = """
    <h1>Title</h1>
    <p>Intro</p>
    <h2>Section</h2>
    <p>Content</p>
    """
    context = ProjectContext(
        project_name="TestProj",
        project_description="Desc",
        prompt_text="Prompt"
    )
    # Patch ContentGenerator.generate_section to return dummy content
    with patch("backend.ai.content_generator.ContentGenerator.generate_section", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = type("DummyGen", (), {
            "section_id": "dummy",
            "original_html": "<h1>Title</h1>",
            "generated_html": "<h1>Generated Title</h1>",
            "generation_metadata": {},
            "validation_status": 1,
            "error_message": None,
            "generation_time_ms": 10
        })()
        workflow = DocumentGenerationWorkflow()
        state = await workflow.run(html_template, context)
        assert state["final_html"].startswith("<h1>Generated Title")
        assert state["total_sections"] > 0
        assert not state["errors"]

@pytest.mark.asyncio
async def test_document_generation_workflow_error():
    html_template = "<h1>Title</h1>"
    context = ProjectContext(
        project_name="TestProj",
        project_description="Desc",
        prompt_text="Prompt"
    )
    # Patch ContentGenerator.generate_section to return invalid content
    with patch("backend.ai.content_generator.ContentGenerator.generate_section", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = type("DummyGen", (), {
            "section_id": "dummy",
            "original_html": "<h1>Title</h1>",
            "generated_html": "",  # Invalid (empty)
            "generation_metadata": {},
            "validation_status": 3,
            "error_message": "fail",
            "generation_time_ms": 10
        })()
        workflow = DocumentGenerationWorkflow()
        state = await workflow.run(html_template, context)
        assert state["errors"]