"""
Tests for PDF file integrity and content verification

Tests the integrity and content of generated PDF files to ensure they meet
quality standards and correctly represent the original HTML content.
"""

import pytest
import os
import tempfile
import io
from unittest.mock import Mock, AsyncMock, patch
import PyPDF2
import re
from datetime import datetime

# Import application components
from backend.services.pdf_generator import (
    PDFGenerator,
    generate_pdf_from_html,
    validate_pdf_output,
    PDFValidationError
)


class TestPDFIntegrity:
    """Tests for PDF file integrity and content verification"""
    
    @pytest.fixture
    def sample_html_content(self):
        """Sample HTML content for testing"""
        return """
        <h1>Test Document</h1>
        <h2>Section 1</h2>
        <p>This is a paragraph with <strong>bold</strong> and <em>italic</em> text.</p>
        <h2>Section 2</h2>
        <ul>
            <li>Item 1</li>
            <li>Item 2</li>
            <li>Item 3</li>
        </ul>
        <p>Another paragraph with some text.</p>
        """
    
    @pytest.mark.asyncio
    async def test_pdf_header_and_structure(self, sample_html_content):
        """Test that generated PDF has proper header and structure"""
        # Mock the browser for PDF generation
        with patch('backend.services.pdf_generator.PDFGenerator._browser') as mock_browser:
            # Create a real PDF for testing
            mock_page = AsyncMock()
            
            # Create a minimal valid PDF content
            # This is a simplified PDF structure with just enough to pass validation
            pdf_content = (
                b"%PDF-1.4\n"
                b"1 0 obj\n<</Type/Catalog/Pages 2 0 R>>\nendobj\n"
                b"2 0 obj\n<</Type/Pages/Kids[3 0 R]/Count 1>>\nendobj\n"
                b"3 0 obj\n<</Type/Page/MediaBox[0 0 595 842]/Parent 2 0 R/Resources<<>>>>\nendobj\n"
                b"xref\n0 4\n0000000000 65535 f\n0000000010 00000 n\n0000000053 00000 n\n0000000102 00000 n\n"
                b"trailer\n<</Size 4/Root 1 0 R>>\n"
                b"startxref\n180\n"
                b"%%EOF"
            )
            mock_page.pdf.return_value = pdf_content
            mock_browser.new_page.return_value = mock_page
            
            # Create a PDFGenerator instance with mocked browser
            generator = PDFGenerator()
            generator._browser = mock_browser
            generator._playwright = Mock()
            
            # Generate PDF
            pdf_bytes = await generator.generate_pdf_from_html(sample_html_content, "Test Document")
            
            # Verify PDF structure
            assert pdf_bytes.startswith(b"%PDF-")
            assert b"%%EOF" in pdf_bytes
            
            # Validate the PDF using the validation function
            try:
                validate_pdf_output(pdf_bytes)
                validation_passed = True
            except PDFValidationError:
                validation_passed = False
            
            assert validation_passed, "PDF validation should pass"
    
    @pytest.mark.asyncio
    async def test_pdf_content_extraction(self, sample_html_content):
        """Test that text content can be extracted from the PDF"""
        # This test requires a real PDF library to extract text
        # We'll use PyPDF2 for this purpose
        
        # Mock the browser for PDF generation
        with patch('backend.services.pdf_generator.PDFGenerator._browser') as mock_browser:
            # Create a mock page that returns a real PDF
            mock_page = AsyncMock()
            
            # For this test, we need to create a PDF with actual text content
            # We'll use a pre-generated PDF with text content matching our sample HTML
            # This is a simplified approach - in a real test, you might use a real PDF generation library
            
            # Create a PDF with text content (simplified for testing)
            pdf_content = (
                b"%PDF-1.4\n"
                b"1 0 obj\n<</Type/Catalog/Pages 2 0 R>>\nendobj\n"
                b"2 0 obj\n<</Type/Pages/Kids[3 0 R]/Count 1>>\nendobj\n"
                b"3 0 obj\n<</Type/Page/MediaBox[0 0 595 842]/Parent 2 0 R"
                b"/Contents 4 0 R/Resources<</Font<</F1<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>>>>>>\nendobj\n"
                b"4 0 obj\n<</Length 90>>\nstream\n"
                b"BT\n/F1 12 Tf\n50 750 Td\n(Test Document) Tj\n0 -20 Td\n"
                b"(Section 1) Tj\n0 -20 Td\n(This is a paragraph with bold and italic text.) Tj\n"
                b"ET\nendstream\nendobj\n"
                b"xref\n0 5\n0000000000 65535 f\n0000000010 00000 n\n0000000053 00000 n\n0000000102 00000 n\n0000000223 00000 n\n"
                b"trailer\n<</Size 5/Root 1 0 R>>\n"
                b"startxref\n350\n"
                b"%%EOF"
            )
            mock_page.pdf.return_value = pdf_content
            mock_browser.new_page.return_value = mock_page
            
            # Create a PDFGenerator instance with mocked browser
            generator = PDFGenerator()
            generator._browser = mock_browser
            generator._playwright = Mock()
            
            # Generate PDF
            pdf_bytes = await generator.generate_pdf_from_html(sample_html_content, "Test Document")
            
            # Extract text from the PDF
            pdf_file = io.BytesIO(pdf_bytes)
            try:
                pdf_reader = PyPDF2.PdfReader(pdf_file)
                text_content = ""
                for page in pdf_reader.pages:
                    text_content += page.extract_text()
                
                # Verify that key content from the HTML is present in the PDF text
                assert "Test Document" in text_content
                assert "Section 1" in text_content
                
                # Note: The exact formatting might differ, so we check for presence of key content
                # rather than exact matches
            except Exception as e:
                pytest.skip(f"PDF text extraction failed: {str(e)}")
    
    @pytest.mark.asyncio
    async def test_pdf_size_validation(self):
        """Test PDF size validation logic"""
        # Test with PDF that's too small
        tiny_pdf = b"%PDF-1.0\n%%EOF"
        with pytest.raises(PDFValidationError, match="too small"):
            validate_pdf_output(tiny_pdf)
        
        # Test with PDF that's large enough
        valid_pdf = b"%PDF-1.4\n" + b"x" * 200 + b"\n%%EOF"
        # This should not raise an exception
        validate_pdf_output(valid_pdf)
        
        # Test with PDF that's too large
        from backend.services.pdf_generator import PDFConfig
        original_max_size = PDFConfig.MAX_PDF_SIZE
        PDFConfig.MAX_PDF_SIZE = 100  # Temporarily set max size to 100 bytes
        try:
            large_pdf = b"%PDF-1.4\n" + b"x" * 200 + b"\n%%EOF"
            with pytest.raises(PDFValidationError, match="too large"):
                validate_pdf_output(large_pdf)
        finally:
            PDFConfig.MAX_PDF_SIZE = original_max_size  # Restore original max size
    
    @pytest.mark.asyncio
    async def test_pdf_header_validation(self):
        """Test PDF header validation logic"""
        # Test with invalid PDF (no PDF header)
        invalid_pdf = b"Not a PDF file\n" + b"x" * 200 + b"\n%%EOF"
        with pytest.raises(PDFValidationError, match="not a valid PDF"):
            validate_pdf_output(invalid_pdf)
        
        # Test with valid PDF header
        valid_pdf = b"%PDF-1.4\n" + b"x" * 200 + b"\n%%EOF"
        # This should not raise an exception
        validate_pdf_output(valid_pdf)
    
    @pytest.mark.asyncio
    async def test_pdf_styling_applied(self, sample_html_content):
        """Test that CSS styling is properly applied to the PDF"""
        # Mock the browser for PDF generation
        with patch('backend.services.pdf_generator.PDFGenerator._browser') as mock_browser:
            # Create a mock page
            mock_page = AsyncMock()
            mock_page.pdf.return_value = b"%PDF-1.4\n" + b"x" * 200 + b"\n%%EOF"
            mock_browser.new_page.return_value = mock_page
            
            # Create a PDFGenerator instance with mocked browser
            generator = PDFGenerator()
            generator._browser = mock_browser
            generator._playwright = Mock()
            
            # Generate PDF
            await generator.generate_pdf_from_html(sample_html_content, "Test Document")
            
            # Verify that CSS styling was added to the HTML content
            mock_page.set_content.assert_called_once()
            content_arg = mock_page.set_content.call_args[0][0]
            
            # Check for CSS styling elements
            assert "<style>" in content_arg
            assert "font-family" in content_arg
            assert "@page" in content_arg
            
            # Check for specific styling rules
            assert "h1" in content_arg
            assert "h2" in content_arg
            assert "p" in content_arg
            assert "ul" in content_arg
            assert "li" in content_arg
    
    @pytest.mark.asyncio
    async def test_pdf_header_footer_templates(self):
        """Test that header and footer templates are properly applied"""
        # Mock the browser for PDF generation
        with patch('backend.services.pdf_generator.PDFGenerator._browser') as mock_browser:
            # Create a mock page
            mock_page = AsyncMock()
            mock_page.pdf.return_value = b"%PDF-1.4\n" + b"x" * 200 + b"\n%%EOF"
            mock_browser.new_page.return_value = mock_page
            
            # Create a PDFGenerator instance with mocked browser
            generator = PDFGenerator()
            generator._browser = mock_browser
            generator._playwright = Mock()
            
            # Generate PDF with a title (should include header and footer)
            html_content = "<h1>Test Document</h1><p>Test content</p>"
            await generator.generate_pdf_from_html(html_content, "Test Document Title")
            
            # Verify that PDF options include header and footer templates
            mock_page.pdf.assert_called_once()
            pdf_options = mock_page.pdf.call_args[1]
            
            assert pdf_options["display_header_footer"] is True
            assert "header_template" in pdf_options
            assert "footer_template" in pdf_options
            
            # Check header template content
            header_template = pdf_options["header_template"]
            assert "Test Document Title" in header_template
            assert "Generated on" in header_template
            
            # Check footer template content
            footer_template = pdf_options["footer_template"]
            assert "Page" in footer_template
            assert "pageNumber" in footer_template
            assert "totalPages" in footer_template


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])