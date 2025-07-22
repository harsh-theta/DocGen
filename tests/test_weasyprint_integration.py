"""
Integration tests for WeasyPrint PDF generator.

This module tests the WeasyPrint integration with Inter font support,
focusing on font rendering, CSS styling, and PDF output quality.
"""

import pytest
import os
import io
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
import PyPDF2
from bs4 import BeautifulSoup

from backend.services.export_manager import ExportFormatManager
from backend.services.document_formatter import DocumentFormatter

# Mock WeasyPrint if it's not available
try:
    from backend.services.weasyprint_generator import (
        WeasyPrintGenerator,
        WeasyPrintConfig,
        WEASYPRINT_AVAILABLE,
        validate_html_content,
        validate_pdf_output
    )
except (ImportError, OSError):
    WEASYPRINT_AVAILABLE = False
    WeasyPrintGenerator = Mock()
    WeasyPrintConfig = Mock()
    validate_html_content = Mock()
    validate_pdf_output = Mock()

# Skip tests that require WeasyPrint
weasyprint_required = pytest.mark.skipif(
    not WEASYPRINT_AVAILABLE,
    reason="WeasyPrint or its dependencies are not available"
)


@pytest.fixture
def export_config():
    """Standard export configuration for consistent testing."""
    return {
        'font_family': 'Inter',
        'font_size': 12,
        'margins': {'top': 25, 'right': 25, 'bottom': 25, 'left': 25},
        'cover_page_mode': 'minimal',
        'table_style': {
            'border_color': '#dddddd',
            'border_width': '1px',
            'header_bg_color': '#f3f3f3',
            'cell_padding': '8px',
            'text_align': 'left'
        }
    }


@pytest.fixture
def sample_html_content():
    """Sample HTML content for testing."""
    return """
    <h1>WeasyPrint Integration Test</h1>
    <p>This is a test paragraph with <strong>bold</strong> and <em>italic</em> text.</p>
    <h2>Font Rendering Test</h2>
    <p>This paragraph tests the Inter font rendering with various characters:</p>
    <ul>
        <li>Regular text in Inter font</li>
        <li><strong>Bold text in Inter font</strong></li>
        <li><em>Italic text in Inter font</em></li>
        <li>Special characters: áéíóúñç</li>
        <li>Symbols: &copy; &reg; &trade; &euro; &pound;</li>
    </ul>
    <h2>Table Rendering Test</h2>
    <table>
        <thead>
            <tr>
                <th>Header 1</th>
                <th>Header 2</th>
                <th>Header 3</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td>Row 1, Cell 1</td>
                <td>Row 1, Cell 2</td>
                <td>Row 1, Cell 3</td>
            </tr>
            <tr>
                <td>Row 2, Cell 1</td>
                <td><strong>Bold text</strong></td>
                <td><em>Italic text</em></td>
            </tr>
        </tbody>
    </table>
    """


class TestWeasyPrintIntegration:
    """Test cases for WeasyPrint integration with Inter font support."""
    
    @weasyprint_required
    def test_weasyprint_initialization(self, export_config):
        """Test that WeasyPrintGenerator initializes correctly with export configuration."""
        generator = WeasyPrintGenerator(export_config)
        
        # Verify generator is initialized
        assert generator is not None
        assert generator.font_config is not None
        
        # Verify export manager is initialized with correct config
        assert generator.export_manager is not None
        assert generator.export_manager.font_family == export_config['font_family']
        assert generator.export_manager.font_size == export_config['font_size']
        
        # Verify document formatter is initialized with correct config
        assert generator.document_formatter is not None
        assert generator.document_formatter.cover_page_mode == export_config['cover_page_mode']
    
    @weasyprint_required
    def test_pdf_generation_with_inter_font(self, export_config, sample_html_content):
        """Test PDF generation with Inter font."""
        generator = WeasyPrintGenerator(export_config)
        
        # Generate PDF
        pdf_bytes = generator.generate_pdf_from_html(sample_html_content, "Font Test")
        
        # Basic validation
        assert pdf_bytes is not None
        assert len(pdf_bytes) > 0
        assert pdf_bytes.startswith(b'%PDF-')
        
        # Write to temporary file for inspection
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
            temp_file.write(pdf_bytes)
            temp_path = temp_file.name
        
        try:
            # Use PyPDF2 to extract text and verify content
            with open(temp_path, 'rb') as pdf_file:
                pdf_reader = PyPDF2.PdfReader(pdf_file)
                text = ""
                for page in pdf_reader.pages:
                    text += page.extract_text()
                
                # Verify content is present
                assert "WeasyPrint Integration Test" in text
                assert "Font Rendering Test" in text
                assert "Regular text in Inter font" in text
                assert "Bold text in Inter font" in text
                assert "Italic text in Inter font" in text
                
                # Verify special characters (may be encoded differently in PDF)
                # We check for presence of some of these characters
                special_chars = "áéíóúñç"
                for char in special_chars:
                    assert char in text or char.encode('utf-8').decode('latin1') in text
        finally:
            # Clean up temporary file
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    @weasyprint_required
    def test_css_styling_application(self, export_config, sample_html_content):
        """Test that CSS styling is properly applied to the PDF."""
        generator = WeasyPrintGenerator(export_config)
        
        # Get the styled HTML (internal method)
        styled_html = generator._add_pdf_styling(sample_html_content, "Styling Test")
        
        # Parse the styled HTML
        soup = BeautifulSoup(styled_html, 'html.parser')
        
        # Verify CSS is included
        style_tags = soup.find_all('style')
        assert len(style_tags) > 0
        
        # Verify CSS contains font family
        css_content = style_tags[0].string
        assert f"font-family: '{export_config['font_family']}'" in css_content
        
        # Verify CSS contains font size
        assert f"font-size: {export_config['font_size']}pt" in css_content
        
        # Verify CSS contains margins
        margin_values = f"{export_config['margins']['top']}mm {export_config['margins']['right']}mm {export_config['margins']['bottom']}mm {export_config['margins']['left']}mm"
        assert f"margin: {margin_values}" in css_content or f"margin:{margin_values}" in css_content
        
        # Verify WeasyPrint-specific page rules
        assert "@page" in css_content
        assert "size: A4" in css_content
        assert "@top-center" in css_content
        assert "@bottom-center" in css_content
        
        # Verify Inter font is set for headers
        assert "string-set: title content()" in css_content
    
    @weasyprint_required
    def test_table_rendering_in_pdf(self, export_config):
        """Test that tables are properly rendered in the PDF."""
        generator = WeasyPrintGenerator(export_config)
        
        # Create HTML with a table
        table_html = """
        <h1>Table Test</h1>
        <table>
            <thead>
                <tr>
                    <th>Header 1</th>
                    <th>Header 2</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td>Cell 1</td>
                    <td>Cell 2</td>
                </tr>
                <tr>
                    <td>Cell 3</td>
                    <td>Cell 4</td>
                </tr>
            </tbody>
        </table>
        """
        
        # Apply consistent table styling
        export_manager = ExportFormatManager(export_config)
        styled_html = export_manager.apply_consistent_table_styling(table_html)
        
        # Generate PDF
        pdf_bytes = generator.generate_pdf_from_html(styled_html, "Table Test")
        
        # Write to temporary file for inspection
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
            temp_file.write(pdf_bytes)
            temp_path = temp_file.name
        
        try:
            # Use PyPDF2 to extract text and verify content
            with open(temp_path, 'rb') as pdf_file:
                pdf_reader = PyPDF2.PdfReader(pdf_file)
                text = pdf_reader.pages[0].extract_text()
                
                # Verify table content is present
                assert "Header 1" in text
                assert "Header 2" in text
                assert "Cell 1" in text
                assert "Cell 2" in text
                assert "Cell 3" in text
                assert "Cell 4" in text
        finally:
            # Clean up temporary file
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    @weasyprint_required
    def test_cover_page_generation(self, export_config):
        """Test that cover pages are properly generated and rendered."""
        # Test with full cover page
        full_cover_config = export_config.copy()
        full_cover_config['cover_page_mode'] = 'full'
        
        generator = WeasyPrintGenerator(full_cover_config)
        
        # Simple HTML content
        html_content = "<h1>Cover Page Test</h1><p>This is a test paragraph.</p>"
        
        # Generate PDF with full cover page
        pdf_bytes = generator.generate_pdf_with_cover_page(
            html_content,
            "Cover Page Test",
            {"date": "July 22, 2025", "author": "Test Author"}
        )
        
        # Write to temporary file for inspection
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
            temp_file.write(pdf_bytes)
            temp_path = temp_file.name
        
        try:
            # Use PyPDF2 to extract text and verify content
            with open(temp_path, 'rb') as pdf_file:
                pdf_reader = PyPDF2.PdfReader(pdf_file)
                
                # Verify we have at least 2 pages (cover page + content)
                assert len(pdf_reader.pages) >= 2
                
                # Extract text from first page (cover page)
                cover_text = pdf_reader.pages[0].extract_text()
                
                # Verify cover page content
                assert "Cover Page Test" in cover_text
                assert "July 22, 2025" in cover_text
                assert "Test Author" in cover_text
                
                # Extract text from second page (content)
                content_text = pdf_reader.pages[1].extract_text()
                
                # Verify content page doesn't duplicate the title
                # (since we're using full cover page mode)
                title_count = content_text.count("Cover Page Test")
                assert title_count <= 1, "Title should not be duplicated on content page"
        finally:
            # Clean up temporary file
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    @weasyprint_required
    def test_font_file_paths(self):
        """Test that font file paths are correctly configured."""
        # Verify font directory exists
        font_dir = Path(WeasyPrintConfig.FONT_DIR)
        assert font_dir.exists(), "Font directory should exist"
        
        # Verify Inter font files exist
        regular_font = Path(WeasyPrintConfig.INTER_FONT_PATH)
        bold_font = Path(WeasyPrintConfig.INTER_BOLD_PATH)
        italic_font = Path(WeasyPrintConfig.INTER_ITALIC_PATH)
        
        assert regular_font.exists(), "Inter Regular font file should exist"
        assert bold_font.exists(), "Inter Bold font file should exist"
        assert italic_font.exists(), "Inter Italic font file should exist"
    
    @weasyprint_required
    def test_html_validation(self):
        """Test HTML validation for WeasyPrint."""
        # Test with valid HTML
        valid_html = "<h1>Valid HTML</h1><p>This is valid HTML content.</p>"
        validated_html = validate_html_content(valid_html)
        assert validated_html == valid_html
        
        # Test with empty HTML
        with pytest.raises(Exception, match="HTML content cannot be empty"):
            validate_html_content("")
        
        # Test with HTML containing potentially malicious content
        malicious_html = "<h1>Test</h1><script>alert('XSS')</script>"
        sanitized_html = validate_html_content(malicious_html)
        assert "<script>" not in sanitized_html
        assert "alert" not in sanitized_html
    
    @weasyprint_required
    def test_pdf_validation(self):
        """Test PDF validation for WeasyPrint."""
        # Test with valid PDF
        valid_pdf = b"%PDF-1.4\n" + b"x" * 200 + b"\n%%EOF"
        # This should not raise an exception
        validate_pdf_output(valid_pdf)
        
        # Test with PDF that's too small
        tiny_pdf = b"%PDF-1.0\n%%EOF"
        with pytest.raises(Exception, match="too small"):
            validate_pdf_output(tiny_pdf)
        
        # Test with non-PDF content
        invalid_pdf = b"Not a PDF file" + b"x" * 200
        with pytest.raises(Exception, match="not a valid PDF"):
            validate_pdf_output(invalid_pdf)


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])