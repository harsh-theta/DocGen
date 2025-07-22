"""
Test the unified export formatting system.

This module tests the ExportFormatManager and DocumentFormatter classes
to ensure consistent styling across different export formats.
"""

import os
import pytest
import tempfile
from pathlib import Path
from datetime import datetime
from bs4 import BeautifulSoup

from backend.services.export_manager import ExportFormatManager
from backend.services.document_formatter import DocumentFormatter
from backend.services.pdf_generator import PDFGenerator
from backend.services.weasyprint_generator import WeasyPrintGenerator, WEASYPRINT_AVAILABLE


class TestExportFormatManager:
    """Test the ExportFormatManager class"""
    
    def test_init_with_default_config(self):
        """Test initialization with default configuration"""
        manager = ExportFormatManager()
        assert manager.font_family == ExportFormatManager.DEFAULT_FONT_FAMILY
        assert manager.font_size == ExportFormatManager.DEFAULT_FONT_SIZE
        assert manager.margins == ExportFormatManager.DEFAULT_MARGINS
        assert manager.table_style == ExportFormatManager.DEFAULT_TABLE_STYLE
        assert manager.heading_sizes == ExportFormatManager.DEFAULT_HEADING_SIZES
    
    def test_init_with_custom_config(self):
        """Test initialization with custom configuration"""
        custom_config = {
            'font_family': 'Arial',
            'font_size': 14,
            'margins': {'top': 30, 'right': 30, 'bottom': 30, 'left': 30},
            'heading_sizes': {'h1': 28, 'h2': 24, 'h3': 20, 'h4': 18, 'h5': 16, 'h6': 14}
        }
        manager = ExportFormatManager(custom_config)
        assert manager.font_family == 'Arial'
        assert manager.font_size == 14
        assert manager.margins['top'] == 30
        assert manager.heading_sizes['h1'] == 28
    
    def test_get_css_template(self):
        """Test getting CSS template"""
        manager = ExportFormatManager()
        css = manager.get_css_template()
        assert 'font-family' in css
        assert 'Inter' in css
        assert 'body' in css
        assert 'h1' in css
        assert 'table' in css
    
    def test_get_docx_style_dict(self):
        """Test getting DOCX style dictionary"""
        manager = ExportFormatManager()
        docx_style = manager.get_docx_style_dict()
        assert 'font_family' in docx_style
        assert 'font_size' in docx_style
        assert 'margins' in docx_style
        assert 'heading_sizes' in docx_style
        assert 'table_style' in docx_style
    
    def test_apply_consistent_table_styling(self):
        """Test applying consistent table styling to HTML"""
        manager = ExportFormatManager()
        html = """
        <table>
            <thead>
                <tr><th>Header 1</th><th>Header 2</th></tr>
            </thead>
            <tbody>
                <tr><td>Cell 1</td><td>Cell 2</td></tr>
            </tbody>
        </table>
        """
        styled_html = manager.apply_consistent_table_styling(html)
        soup = BeautifulSoup(styled_html, 'html.parser')
        table = soup.find('table')
        assert 'width:100%' in table['style']
        assert 'border-collapse:collapse' in table['style']
        
        th = soup.find('th')
        assert 'background-color' in th['style']
        
        td = soup.find('td')
        assert 'padding' in td['style']
        assert 'border' in td['style']


class TestDocumentFormatter:
    """Test the DocumentFormatter class"""
    
    def test_init_with_default_config(self):
        """Test initialization with default configuration"""
        formatter = DocumentFormatter()
        assert formatter.cover_page_mode == 'none'
    
    def test_init_with_custom_config(self):
        """Test initialization with custom configuration"""
        custom_config = {'cover_page_mode': 'full'}
        formatter = DocumentFormatter(custom_config)
        assert formatter.cover_page_mode == 'full'
    
    def test_remove_duplicate_titles(self):
        """Test removing duplicate titles"""
        formatter = DocumentFormatter()
        html = """
        <h1>Test Title</h1>
        <p>Some content</p>
        <h1>Test Title</h1>
        <p>More content</p>
        """
        result = formatter.remove_duplicate_titles(html, "Test Title")
        soup = BeautifulSoup(result, 'html.parser')
        h1_elements = soup.find_all('h1')
        assert len(h1_elements) == 1
    
    def test_generate_cover_page_none(self):
        """Test generating no cover page"""
        formatter = DocumentFormatter({'cover_page_mode': 'none'})
        cover = formatter.generate_cover_page("Test Document")
        assert cover == ""
    
    def test_generate_cover_page_minimal(self):
        """Test generating minimal cover page"""
        formatter = DocumentFormatter({'cover_page_mode': 'minimal'})
        cover = formatter.generate_cover_page("Test Document", {"date": "2025-07-22"})
        assert "Test Document" in cover
        assert "2025-07-22" in cover
        assert "minimal-cover" in cover
    
    def test_generate_cover_page_full(self):
        """Test generating full cover page"""
        formatter = DocumentFormatter({'cover_page_mode': 'full'})
        cover = formatter.generate_cover_page("Test Document", {"date": "2025-07-22"})
        assert "Test Document" in cover
        assert "2025-07-22" in cover
        assert "cover-page" in cover
        assert "page-break" in cover
    
    def test_format_document(self):
        """Test formatting document with title and metadata"""
        formatter = DocumentFormatter({'cover_page_mode': 'minimal'})
        html = "<p>Test content</p>"
        result = formatter.format_document(html, "Test Document", {"date": "2025-07-22"})
        assert "Test Document" in result
        assert "2025-07-22" in result
        assert "Test content" in result
        assert "minimal-cover" in result


@pytest.mark.asyncio
async def test_pdf_generator_integration():
    """Test that PDFGenerator uses the unified export formatting system"""
    # Skip if running in CI environment without browser
    if os.environ.get('CI') == 'true':
        pytest.skip("Skipping browser-based test in CI environment")
    
    # Create a simple HTML document
    html = """
    <h1>Test Document</h1>
    <p>This is a test paragraph.</p>
    <table>
        <tr><th>Header 1</th><th>Header 2</th></tr>
        <tr><td>Cell 1</td><td>Cell 2</td></tr>
    </table>
    """
    
    # Configure export formatting
    export_config = {
        'font_family': 'Inter',
        'font_size': 12,
        'cover_page_mode': 'minimal'
    }
    
    # Generate PDF using Playwright
    async with PDFGenerator(export_config) as generator:
        pdf_bytes = await generator.generate_pdf_from_html(html, "Test Document")
        
    # Basic validation
    assert pdf_bytes.startswith(b'%PDF-')
    assert len(pdf_bytes) > 1000


@pytest.mark.skipif(not WEASYPRINT_AVAILABLE, reason="WeasyPrint not installed")
def test_weasyprint_generator_integration():
    """Test that WeasyPrintGenerator uses the unified export formatting system"""
    # Create a simple HTML document
    html = """
    <h1>Test Document</h1>
    <p>This is a test paragraph.</p>
    <table>
        <tr><th>Header 1</th><th>Header 2</th></tr>
        <tr><td>Cell 1</td><td>Cell 2</td></tr>
    </table>
    """
    
    # Configure export formatting
    export_config = {
        'font_family': 'Inter',
        'font_size': 12,
        'cover_page_mode': 'minimal'
    }
    
    # Generate PDF using WeasyPrint
    generator = WeasyPrintGenerator(export_config)
    pdf_bytes = generator.generate_pdf_from_html(html, "Test Document")
    
    # Basic validation
    assert pdf_bytes.startswith(b'%PDF-')
    assert len(pdf_bytes) > 1000


def test_consistent_styling_between_generators():
    """
    Test that both PDF generators use the same styling from ExportFormatManager.
    
    This test doesn't actually generate PDFs but verifies that both generators
    use the same ExportFormatManager configuration.
    """
    # Configure export formatting
    export_config = {
        'font_family': 'Inter',
        'font_size': 14,
        'margins': {'top': 20, 'right': 20, 'bottom': 20, 'left': 20},
        'cover_page_mode': 'minimal'
    }
    
    # Create both generators
    playwright_generator = PDFGenerator(export_config)
    weasyprint_generator = WeasyPrintGenerator(export_config)
    
    # Verify they use the same configuration
    assert playwright_generator.export_manager.font_family == weasyprint_generator.export_manager.font_family
    assert playwright_generator.export_manager.font_size == weasyprint_generator.export_manager.font_size
    assert playwright_generator.export_manager.margins == weasyprint_generator.export_manager.margins
    assert playwright_generator.document_formatter.cover_page_mode == weasyprint_generator.document_formatter.cover_page_mode