"""
Unit tests for PDF Generation Service

Tests the PDF generation functionality including HTML-to-PDF conversion,
CSS styling, error handling, and filename sanitization.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime
import tempfile
import os

# Import the modules to test
from backend.services.pdf_generator import (
    PDFGenerator,
    PDFGenerationError,
    PDFValidationError,
    HTMLValidationError,
    sanitize_filename,
    generate_unique_filename,
    generate_pdf_from_html
)


class TestPDFGenerator:
    """Test cases for PDFGenerator class"""
    
    @pytest.fixture
    def pdf_generator(self):
        """Fixture to create a PDFGenerator instance for testing"""
        generator = PDFGenerator()
        # Mock the browser and playwright for testing
        generator._playwright = Mock()
        generator._browser = AsyncMock()
        return generator
    
    @pytest.mark.asyncio
    async def test_generate_pdf_from_html_success(self, pdf_generator):
        """Test successful PDF generation from HTML content"""
        # Mock page and PDF generation - create a valid PDF-like structure
        mock_page = AsyncMock()
        # Create a mock PDF that passes validation (starts with %PDF- and has sufficient size)
        mock_pdf_content = b"%PDF-1.4\n" + b"PDF_CONTENT_BYTES_" + b"0" * 200 + b"%%EOF"
        mock_page.pdf.return_value = mock_pdf_content
        pdf_generator._browser.new_page.return_value = mock_page
        
        html_content = "<h1>Test Document</h1><p>This is a test paragraph.</p>"
        title = "Test Document"
        
        result = await pdf_generator.generate_pdf_from_html(html_content, title)
        
        # Verify the result
        assert isinstance(result, bytes)
        assert len(result) > 100  # Should be larger than minimum size
        assert result.startswith(b"%PDF-")  # Should be a valid PDF
        
        # Verify page methods were called
        mock_page.set_content.assert_called_once()
        mock_page.pdf.assert_called_once()
        mock_page.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_generate_pdf_empty_content_error(self, pdf_generator):
        """Test error handling for empty HTML content"""
        with pytest.raises(PDFGenerationError, match="HTML content cannot be empty"):
            await pdf_generator.generate_pdf_from_html("")
        
        with pytest.raises(PDFGenerationError, match="HTML content cannot be empty"):
            await pdf_generator.generate_pdf_from_html("   ")
    
    @pytest.mark.asyncio
    async def test_generate_pdf_browser_not_initialized(self):
        """Test error when browser is not initialized"""
        generator = PDFGenerator()
        # Don't initialize browser
        
        with pytest.raises(PDFGenerationError, match="PDF generator not initialized"):
            await generator.generate_pdf_from_html("<p>Test</p>")
    
    @pytest.mark.asyncio
    async def test_generate_pdf_timeout_error(self, pdf_generator):
        """Test timeout error handling"""
        mock_page = AsyncMock()
        mock_page.set_content.side_effect = asyncio.TimeoutError()
        pdf_generator._browser.new_page.return_value = mock_page
        
        with pytest.raises(PDFGenerationError, match="PDF generation timed out"):
            await pdf_generator.generate_pdf_from_html("<p>Test</p>")
    
    @pytest.mark.asyncio
    async def test_generate_pdf_network_error(self, pdf_generator):
        """Test network error handling"""
        mock_page = AsyncMock()
        mock_page.set_content.side_effect = Exception("net::ERR_CONNECTION_FAILED")
        pdf_generator._browser.new_page.return_value = mock_page
        
        with pytest.raises(PDFGenerationError, match="Network error during PDF generation"):
            await pdf_generator.generate_pdf_from_html("<p>Test</p>")
    
    @pytest.mark.asyncio
    async def test_generate_pdf_protocol_error(self, pdf_generator):
        """Test browser protocol error handling"""
        mock_page = AsyncMock()
        mock_page.set_content.side_effect = Exception("Protocol error: Connection closed")
        pdf_generator._browser.new_page.return_value = mock_page
        
        with pytest.raises(PDFGenerationError, match="Browser protocol error"):
            await pdf_generator.generate_pdf_from_html("<p>Test</p>")
    
    @pytest.mark.asyncio
    async def test_generate_pdf_too_small_error(self, pdf_generator):
        """Test error when generated PDF is too small"""
        mock_page = AsyncMock()
        mock_page.pdf.return_value = b"tiny"  # Very small PDF
        pdf_generator._browser.new_page.return_value = mock_page
        
        with pytest.raises(PDFValidationError, match="Generated PDF is too small"):
            await pdf_generator.generate_pdf_from_html("<p>Test</p>")
    
    def test_add_pdf_styling_simple_html(self, pdf_generator):
        """Test CSS styling addition to simple HTML"""
        html_content = "<h1>Title</h1><p>Content</p>"
        result = pdf_generator._add_pdf_styling(html_content, "Test Title")
        
        # Check that proper HTML structure is added
        assert "<!DOCTYPE html>" in result
        assert "<html lang=\"en\">" in result
        assert "<head>" in result
        assert "<title>Test Title</title>" in result
        assert "font-family: 'Times New Roman'" in result
        assert "pdf-content" in result
        assert html_content in result
    
    def test_add_pdf_styling_complete_html(self, pdf_generator):
        """Test CSS styling addition to complete HTML document"""
        html_content = """
        <!DOCTYPE html>
        <html>
        <head><title>Original</title></head>
        <body><h1>Title</h1></body>
        </html>
        """
        result = pdf_generator._add_pdf_styling(html_content, "Test Title")
        
        # Check that CSS is injected properly
        assert "font-family: 'Times New Roman'" in result
        assert "@page" in result
        assert "Original" in result  # Original title should remain
    
    def test_get_header_template(self, pdf_generator):
        """Test header template generation"""
        title = "Test Document"
        result = pdf_generator._get_header_template(title)
        
        assert title in result
        assert "Generated on" in result
        assert "font-size: 10px" in result
        assert "border-bottom" in result
    
    def test_get_footer_template(self, pdf_generator):
        """Test footer template generation"""
        result = pdf_generator._get_footer_template()
        
        assert "pageNumber" in result
        assert "totalPages" in result
        assert "Page" in result
        assert "font-size: 10px" in result


class TestFilenameUtilities:
    """Test cases for filename utility functions"""
    
    def test_sanitize_filename_basic(self):
        """Test basic filename sanitization"""
        result = sanitize_filename("My Document")
        assert result == "My Document.pdf"
    
    def test_sanitize_filename_special_characters(self):
        """Test sanitization of special characters"""
        result = sanitize_filename("My<Document>:With|Special*Characters")
        assert result == "My_Document__With_Special_Characters.pdf"
    
    def test_sanitize_filename_empty(self):
        """Test sanitization of empty filename"""
        result = sanitize_filename("")
        assert result.startswith("document_")
        assert result.endswith(".pdf")
        assert len(result) > 10  # Should have timestamp
    
    def test_sanitize_filename_whitespace_only(self):
        """Test sanitization of whitespace-only filename"""
        result = sanitize_filename("   ")
        assert result.startswith("document_")
        assert result.endswith(".pdf")
    
    def test_sanitize_filename_too_long(self):
        """Test sanitization of overly long filename"""
        long_name = "a" * 150
        result = sanitize_filename(long_name, max_length=50)
        assert len(result) <= 50
        assert result.endswith(".pdf")
    
    def test_sanitize_filename_with_extension(self):
        """Test sanitization preserving existing extension"""
        result = sanitize_filename("document.txt")
        assert result == "document.pdf"  # Should replace with .pdf
    
    def test_sanitize_filename_dots_and_spaces(self):
        """Test sanitization of filenames with dots and spaces"""
        result = sanitize_filename("  .hidden file  ")
        assert not result.startswith(".")
        assert result.endswith(".pdf")
        # Should either contain "document" (if prefixed) or "hidden file" (if cleaned)
        assert "document" in result or "hidden file" in result
    
    def test_sanitize_filename_multiple_spaces(self):
        """Test sanitization of multiple consecutive spaces"""
        result = sanitize_filename("My    Document    With    Spaces")
        assert result == "My Document With Spaces.pdf"
    
    def test_generate_unique_filename(self):
        """Test unique filename generation"""
        base_name = "test_document"
        result = generate_unique_filename(base_name)
        
        assert result.startswith("test_document_")
        assert result.endswith(".pdf")
        assert len(result) > len(base_name) + 10  # Should have timestamp
    
    def test_generate_unique_filename_with_special_chars(self):
        """Test unique filename generation with special characters"""
        base_name = "test<document>with:special*chars"
        result = generate_unique_filename(base_name)
        
        assert "test_document_with_special_chars_" in result
        assert result.endswith(".pdf")
    
    def test_generate_unique_filename_multiple_calls_different(self):
        """Test that multiple calls generate different filenames"""
        import time
        base_name = "test_document"
        result1 = generate_unique_filename(base_name)
        time.sleep(0.001)  # Small delay to ensure different timestamps
        result2 = generate_unique_filename(base_name)
        
        assert result1 != result2
        both_start_with_base = all(r.startswith("test_document_") for r in [result1, result2])
        assert both_start_with_base


class TestConvenienceFunction:
    """Test cases for the convenience function"""
    
    @pytest.mark.asyncio
    @patch('backend.services.pdf_generator.PDFGenerator')
    async def test_generate_pdf_from_html_convenience(self, mock_generator_class):
        """Test the convenience function for PDF generation"""
        # Mock the generator instance and its methods
        mock_generator = AsyncMock()
        mock_generator.generate_pdf_from_html.return_value = b"PDF_CONTENT"
        mock_generator_class.return_value = mock_generator
        
        # Configure async context manager
        mock_generator.__aenter__.return_value = mock_generator
        mock_generator.__aexit__.return_value = None
        
        html_content = "<h1>Test</h1>"
        title = "Test Document"
        
        result = await generate_pdf_from_html(html_content, title)
        
        assert result == b"PDF_CONTENT"
        mock_generator.generate_pdf_from_html.assert_called_once_with(html_content, title)


class TestErrorHandling:
    """Test cases for comprehensive error handling"""
    
    @pytest.mark.asyncio
    async def test_pdf_generation_error_inheritance(self):
        """Test that PDFGenerationError is properly inherited from Exception"""
        error = PDFGenerationError("Test error")
        assert isinstance(error, Exception)
        assert str(error) == "Test error"
    
    @pytest.mark.asyncio
    async def test_unexpected_error_handling(self):
        """Test handling of unexpected errors"""
        generator = PDFGenerator()
        generator._browser = AsyncMock()
        
        # Mock an unexpected error
        mock_page = AsyncMock()
        mock_page.set_content.side_effect = ValueError("Unexpected error")
        generator._browser.new_page.return_value = mock_page
        
        with pytest.raises(PDFGenerationError, match="PDF generation failed"):
            await generator.generate_pdf_from_html("<p>Test</p>")


class TestPDFStyling:
    """Test cases for PDF styling functionality"""
    
    def test_css_includes_all_required_elements(self):
        """Test that CSS includes styling for all required HTML elements"""
        generator = PDFGenerator()
        html_content = """
        <h1>Heading 1</h1>
        <h2>Heading 2</h2>
        <h3>Heading 3</h3>
        <p>Paragraph with <code>inline code</code></p>
        <ul><li>List item</li></ul>
        <blockquote>Quote</blockquote>
        <pre><code>Code block</code></pre>
        <table><tr><th>Header</th><td>Cell</td></tr></table>
        """
        
        result = generator._add_pdf_styling(html_content)
        
        # Check that CSS includes styles for all elements
        css_elements = ['h1', 'h2', 'h3', 'p', 'ul', 'li', 'blockquote', 'code', 'pre', 'table', 'th', 'td']
        for element in css_elements:
            assert element in result
        
        # Check for PDF-specific properties
        assert "@page" in result
        assert "page-break" in result
        assert "Times New Roman" in result
    
    def test_css_page_break_properties(self):
        """Test that CSS includes proper page break properties"""
        generator = PDFGenerator()
        result = generator._add_pdf_styling("<p>Test</p>")
        
        # Check for page break related CSS
        assert "page-break-after: avoid" in result
        assert "page-break-inside: avoid" in result
        assert "page-break-before: always" in result
        assert "orphans: 2" in result
        assert "widows: 2" in result


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])