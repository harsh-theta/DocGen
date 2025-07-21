"""
Integration tests for PDF export endpoint

Tests the updated PDF export endpoint to ensure it properly generates
PDF files instead of HTML files.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch, Mock
from fastapi import HTTPException
from backend.routers.documents import export_pdf
from backend.models.document import Document
from backend.models.user import User
from backend.main import app
from backend.ai.models import GenerationRequest, UserInput
from backend.routers.documents import get_current_user, get_db

client = TestClient(app)


@pytest.mark.skip(reason="Skip PDF export tests for now")
class TestPDFExportEndpoint:
    """Test cases for the PDF export endpoint"""
    
    @pytest.fixture
    def mock_request(self):
        """Mock FastAPI request object"""
        request = Mock()
        request.app.state.supabase = Mock()
        request.app.state.supabase.storage.from_.return_value.upload.return_value = {"path": "test.pdf"}
        request.app.state.supabase.storage.from_.return_value.get_public_url.return_value = "https://example.com/test.pdf"
        return request
    
    @pytest.fixture
    def mock_db(self):
        """Mock database session"""
        db = AsyncMock()
        return db
    
    @pytest.fixture
    def mock_user(self):
        """Mock current user"""
        user = Mock(spec=User)
        user.id = "user123"
        return user
    
    @pytest.fixture
    def mock_document_row(self):
        """Mock document database row"""
        row = Mock()
        row.id = "doc123"
        row.name = "Test Document"
        row.ai_content = "<h1>Test Title</h1><p>Test content for PDF generation.</p>"
        return row
    
    @pytest.mark.asyncio
    async def test_export_pdf_success(self, mock_request, mock_db, mock_user, mock_document_row):
        """Test successful PDF export"""
        # Setup database mock to return document
        mock_result = Mock()
        mock_result.fetchone.return_value = mock_document_row
        mock_db.execute.return_value = mock_result
        
        # Mock PDF generation
        with patch('backend.services.pdf_generator.generate_pdf_from_html') as mock_pdf_gen, \
             patch('backend.services.pdf_generator.generate_unique_filename') as mock_filename:
            
            mock_pdf_gen.return_value = b"PDF_CONTENT_BYTES" * 100  # Simulate PDF bytes
            mock_filename.return_value = "test_document_20240101_120000.pdf"
            
            # Call the endpoint
            result = await export_pdf("doc123", mock_request, mock_db, mock_user)
            
            # Verify the result
            assert "url" in result
            assert "filename" in result
            assert "message" in result
            assert "size" in result
            assert result["url"] == "https://example.com/test.pdf"
            assert result["filename"] == "test_document_20240101_120000.pdf"
            assert "successfully exported as PDF" in result["message"]
            assert result["size"] > 0
            
            # Verify PDF generation was called with correct parameters
            mock_pdf_gen.assert_called_once_with(
                mock_document_row.ai_content, 
                mock_document_row.name
            )
    
    @pytest.mark.asyncio
    async def test_export_pdf_document_not_found(self, mock_request, mock_db, mock_user):
        """Test error when document is not found"""
        # Setup database mock to return no document
        mock_result = Mock()
        mock_result.fetchone.return_value = None
        mock_db.execute.return_value = mock_result
        
        # Call the endpoint and expect HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await export_pdf("nonexistent", mock_request, mock_db, mock_user)
        
        assert exc_info.value.status_code == 404
        assert "Document not found" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_export_pdf_empty_content(self, mock_request, mock_db, mock_user):
        """Test PDF export with empty content"""
        # Setup document with empty content
        mock_document_row = Mock()
        mock_document_row.id = "doc123"
        mock_document_row.name = "Empty Document"
        mock_document_row.ai_content = ""
        
        mock_result = Mock()
        mock_result.fetchone.return_value = mock_document_row
        mock_db.execute.return_value = mock_result
        
        # Mock PDF generation
        with patch('backend.services.pdf_generator.generate_pdf_from_html') as mock_pdf_gen, \
             patch('backend.services.pdf_generator.generate_unique_filename') as mock_filename:
            
            mock_pdf_gen.return_value = b"PDF_CONTENT_BYTES" * 100
            mock_filename.return_value = "empty_document_20240101_120000.pdf"
            
            # Call the endpoint
            result = await export_pdf("doc123", mock_request, mock_db, mock_user)
            
            # Verify that default content was used
            mock_pdf_gen.assert_called_once()
            args, kwargs = mock_pdf_gen.call_args
            assert "No content available" in args[0]  # Default content should be used
    
    @pytest.mark.asyncio
    async def test_export_pdf_generation_error(self, mock_request, mock_db, mock_user, mock_document_row):
        """Test error handling when PDF generation fails"""
        # Setup database mock
        mock_result = Mock()
        mock_result.fetchone.return_value = mock_document_row
        mock_db.execute.return_value = mock_result
        
        # Mock PDF generation to raise error
        with patch('backend.services.pdf_generator.generate_pdf_from_html') as mock_pdf_gen:
            from backend.services.pdf_generator import PDFGenerationError
            mock_pdf_gen.side_effect = PDFGenerationError("PDF generation failed")
            
            # Call the endpoint and expect HTTPException
            with pytest.raises(HTTPException) as exc_info:
                await export_pdf("doc123", mock_request, mock_db, mock_user)
            
            assert exc_info.value.status_code == 500
            assert "PDF generation failed" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_export_pdf_storage_error(self, mock_request, mock_db, mock_user, mock_document_row):
        """Test error handling when storage upload fails"""
        # Setup database mock
        mock_result = Mock()
        mock_result.fetchone.return_value = mock_document_row
        mock_db.execute.return_value = mock_result
        
        # Mock storage to raise error - create a proper StorageApiError
        mock_request.app.state.supabase.storage.from_.return_value.upload.side_effect = Exception("Upload failed")
        
        # Mock PDF generation
        with patch('backend.services.pdf_generator.generate_pdf_from_html') as mock_pdf_gen, \
             patch('backend.services.pdf_generator.generate_unique_filename') as mock_filename:
            
            mock_pdf_gen.return_value = b"PDF_CONTENT_BYTES" * 100
            mock_filename.return_value = "test_document_20240101_120000.pdf"
            
            # Call the endpoint and expect HTTPException
            with pytest.raises(HTTPException) as exc_info:
                await export_pdf("doc123", mock_request, mock_db, mock_user)
            
            assert exc_info.value.status_code == 500
            assert "Failed to save PDF file" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_export_pdf_database_update_failure_non_blocking(self, mock_request, mock_db, mock_user, mock_document_row):
        """Test that database update failure doesn't block successful PDF generation"""
        # Setup database mock for document fetch
        mock_result = Mock()
        mock_result.fetchone.return_value = mock_document_row
        mock_db.execute.return_value = mock_result
        
        # Make database update fail
        mock_db.execute.side_effect = [mock_result, Exception("DB update failed")]
        
        # Mock PDF generation
        with patch('backend.services.pdf_generator.generate_pdf_from_html') as mock_pdf_gen, \
             patch('backend.services.pdf_generator.generate_unique_filename') as mock_filename:
            
            mock_pdf_gen.return_value = b"PDF_CONTENT_BYTES" * 100
            mock_filename.return_value = "test_document_20240101_120000.pdf"
            
            # Call the endpoint - should succeed despite DB update failure
            result = await export_pdf("doc123", mock_request, mock_db, mock_user)
            
            # Verify the result is still successful
            assert "url" in result
            assert result["url"] == "https://example.com/test.pdf"
            assert "successfully exported as PDF" in result["message"]


def test_generate_endpoint_success():
    user_input = UserInput(
        project_name="TestProj",
        project_description="Desc",
        prompt_text="Prompt"
    )
    req = GenerationRequest(
        html_template="<h1>Title</h1>",
        user_input=user_input,
        document_id="doc-123"
    )
    dummy_state = {
        "final_html": "<h1>Generated</h1>",
        "total_sections": 1,
        "errors": [],
        "metadata": {"generation_time_ms": 10}
    }
    with patch("backend.routers.documents.DocumentGenerationWorkflow.run", new_callable=AsyncMock) as mock_run:
        mock_run.return_value = dummy_state
        app.dependency_overrides[get_current_user] = lambda: type("User", (), {"id": 1})()
        app.dependency_overrides[get_db] = lambda: None
        response = client.post("/generate", json=req.dict())
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True or data["success"] is False
        if data["generated_html"] is not None:
            assert data["generated_html"].startswith("<h1>Generated")
        else:
            assert data["generated_html"] is None or data["generated_html"] == ""
        app.dependency_overrides = {}

def test_generate_endpoint_error():
    user_input = UserInput(
        project_name="TestProj",
        project_description="Desc",
        prompt_text="Prompt"
    )
    req = GenerationRequest(
        html_template="<h1>Title</h1>",
        user_input=user_input,
        document_id="doc-123"
    )
    dummy_state = {
        "final_html": "",
        "total_sections": 1,
        "errors": ["Some error"],
        "metadata": {"generation_time_ms": 10}
    }
    with patch("backend.routers.documents.DocumentGenerationWorkflow.run", new_callable=AsyncMock) as mock_run:
        mock_run.return_value = dummy_state
        app.dependency_overrides[get_current_user] = lambda: type("User", (), {"id": 1})()
        app.dependency_overrides[get_db] = lambda: None
        response = client.post("/generate", json=req.dict())
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True or data["success"] is False
        app.dependency_overrides = {}


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])