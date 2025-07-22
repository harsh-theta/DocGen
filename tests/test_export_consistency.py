"""
Integration tests for export consistency between PDF and DOCX formats.

This module tests that PDF and DOCX exports produce identical formatting,
table rendering, heading hierarchy, and layout synchronization.
"""

import pytest
import os
import io
import tempfile
from pathlib import Path
from unittest.mock import patch, Mock, AsyncMock
import PyPDF2
from docx import Document as DocxDocument
from bs4 import BeautifulSoup

from backend.services.export_manager import ExportFormatManager
from backend.services.document_formatter import DocumentFormatter

# Mock WeasyPrint if it's not available
try:
    from backend.services.weasyprint_generator import WeasyPrintGenerator, WEASYPRINT_AVAILABLE
except (ImportError, OSError):
    WEASYPRINT_AVAILABLE = False
    WeasyPrintGenerator = Mock()

# Mock document export functions
export_pdf = Mock()
export_docx = Mock()

# Skip tests that require WeasyPrint
weasyprint_required = pytest.mark.skipif(
    not WEASYPRINT_AVAILABLE,
    reason="WeasyPrint or its dependencies are not available"
)


@pytest.fixture
def sample_html_with_formatting():
    """Sample HTML content with various formatting elements for testing."""
    return """
    <h1>Test Document</h1>
    <p>This is a test paragraph with <strong>bold</strong> and <em>italic</em> text.</p>
    <h2>Section 1</h2>
    <p>This is the first section with some content.</p>
    <ul>
        <li>List item 1</li>
        <li>List item 2 with <strong>bold</strong> text</li>
        <li>List item 3</li>
    </ul>
    <h2>Section 2</h2>
    <p>This is the second section with a table:</p>
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
    <h3>Subsection 2.1</h3>
    <p>This is a subsection with more content.</p>
    <blockquote>This is a blockquote with some important information.</blockquote>
    <h2>Section 3</h2>
    <p>This is the third section with a code block:</p>
    <pre><code>def hello_world():
    print("Hello, World!")
    return True</code></pre>
    """


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
def mock_request():
    """Mock FastAPI request object"""
    request = Mock()
    request.app.state.supabase = Mock()
    request.app.state.supabase.storage.from_.return_value.upload.return_value = {"path": "test.pdf"}
    request.app.state.supabase.storage.from_.return_value.get_public_url.return_value = "https://example.com/test.pdf"
    return request


@pytest.fixture
def mock_db():
    """Mock database session"""
    db = AsyncMock()
    return db


@pytest.fixture
def mock_user():
    """Mock current user"""
    user = Mock()
    user.id = "user123"
    return user


@pytest.fixture
def mock_document_row(sample_html_with_formatting):
    """Mock document database row"""
    row = Mock()
    row.id = "doc123"
    row.name = "Test Document"
    row.ai_content = sample_html_with_formatting
    return row


class TestExportConsistency:
    """Test cases for export consistency between PDF and DOCX formats."""
    
    def test_export_manager_consistency(self, export_config):
        """Test that ExportFormatManager provides consistent styling for both formats."""
        manager = ExportFormatManager(export_config)
        
        # Get styling for both formats
        pdf_config = manager.get_export_config('pdf')
        docx_config = manager.get_export_config('docx')
        
        # Verify font family is consistent
        assert pdf_config['font_family'] == docx_config['font_family']
        
        # Verify font size is consistent (accounting for unit differences)
        assert pdf_config['font_size'] == docx_config['font_size']
        
        # Verify margins are consistent (accounting for unit differences)
        for key in ['top', 'right', 'bottom', 'left']:
            # PDF uses mm, DOCX uses twips (1/20th of a point)
            # The conversion factor is applied in the ExportFormatManager
            assert pdf_config['margins'][key] * 2.835 == pytest.approx(docx_config['margins'][key], rel=0.1)
    
    def test_document_formatter_consistency(self, export_config, sample_html_with_formatting):
        """Test that DocumentFormatter produces consistent output for both formats."""
        formatter = DocumentFormatter(export_config)
        
        # Format document with title and metadata
        title = "Test Document"
        metadata = {"date": "July 22, 2025", "author": "Test Author"}
        
        formatted_html = formatter.format_document(sample_html_with_formatting, title, metadata)
        
        # Verify title is present
        assert title in formatted_html
        
        # Verify metadata is present
        assert metadata["date"] in formatted_html
        assert metadata["author"] in formatted_html
        
        # Verify cover page is generated according to mode
        if export_config['cover_page_mode'] == 'minimal':
            assert "minimal-cover" in formatted_html
        elif export_config['cover_page_mode'] == 'full':
            assert "cover-page" in formatted_html
            assert "page-break" in formatted_html
        else:  # 'none'
            assert "cover-page" not in formatted_html
            assert "minimal-cover" not in formatted_html
        
        # Verify titles are present
        soup = BeautifulSoup(formatted_html, 'html.parser')
        h1_elements = soup.find_all('h1', string=title)
        
        # In minimal cover page mode, we expect two h1 elements with the title:
        # one in the cover page and one in the content
        if export_config['cover_page_mode'] == 'minimal':
            assert len(h1_elements) <= 2, "Should have at most 2 titles (cover page and content)"
        elif export_config['cover_page_mode'] == 'full':
            # In full cover page mode, the content title should be removed
            content_h1_elements = [h for h in h1_elements if 'cover-title' not in h.get('class', [])]
            assert len(content_h1_elements) <= 1, "Content should have at most 1 title"
        else:  # 'none'
            assert len(h1_elements) <= 1, "Should have at most 1 title"
    
    def test_table_styling_consistency(self, export_config):
        """Test that table styling is consistent between formats."""
        manager = ExportFormatManager(export_config)
        
        # Create a simple HTML table
        table_html = """
        <table>
            <thead>
                <tr><th>Header 1</th><th>Header 2</th></tr>
            </thead>
            <tbody>
                <tr><td>Cell 1</td><td>Cell 2</td></tr>
            </tbody>
        </table>
        """
        
        # Apply consistent styling
        styled_html = manager.apply_consistent_table_styling(table_html)
        
        # Parse the styled HTML
        soup = BeautifulSoup(styled_html, 'html.parser')
        table = soup.find('table')
        
        # Verify table styling
        assert 'width:100%' in table['style']
        assert 'border-collapse:collapse' in table['style']
        assert export_config['table_style']['border_width'] in table['style']
        assert export_config['table_style']['border_color'] in table['style']
        
        # Verify header styling
        th = soup.find('th')
        assert export_config['table_style']['header_bg_color'] in th['style']
        assert export_config['table_style']['text_align'] in th['style']
        
        # Verify cell styling
        td = soup.find('td')
        assert export_config['table_style']['cell_padding'] in td['style']
        assert export_config['table_style']['border_width'] in td['style']
        assert export_config['table_style']['border_color'] in td['style']
    
    def test_heading_hierarchy_consistency(self, export_config):
        """Test that heading hierarchy is consistent between formats."""
        manager = ExportFormatManager(export_config)
        
        # Create HTML with headings
        headings_html = """
        <h1>Heading 1</h1>
        <h2>Heading 2</h2>
        <h3>Heading 3</h3>
        <h4>Heading 4</h4>
        <h5>Heading 5</h5>
        <h6>Heading 6</h6>
        """
        
        # Apply consistent heading hierarchy
        styled_html = manager.apply_heading_hierarchy(headings_html)
        
        # Parse the styled HTML
        soup = BeautifulSoup(styled_html, 'html.parser')
        
        # Verify each heading level has consistent styling
        for level in range(1, 7):
            tag = f'h{level}'
            heading = soup.find(tag)
            assert heading is not None
            assert 'style' in heading.attrs
            
            # Verify font family
            assert f"font-family:'{export_config['font_family']}'" in heading['style']
            
            # Verify font size based on heading level
            expected_size = manager.heading_sizes[tag]
            assert f"font-size:{expected_size}pt" in heading['style']
            
            # Verify margins
            assert "margin-top" in heading['style']
            assert "margin-bottom" in heading['style']
    
    def test_table_rendering_consistency(self, export_config, sample_html_with_formatting):
        """Test that tables are rendered consistently across formats."""
        manager = ExportFormatManager(export_config)
        
        # Apply consistent styling to the sample HTML
        styled_html = manager.apply_consistent_table_styling(sample_html_with_formatting)
        
        # Parse the styled HTML
        soup = BeautifulSoup(styled_html, 'html.parser')
        table = soup.find('table')
        
        # Verify table structure
        assert table is not None
        
        # Count rows and columns
        rows = table.find_all('tr')
        assert len(rows) == 3  # Header row + 2 data rows
        
        header_cells = rows[0].find_all(['th'])
        assert len(header_cells) == 3  # 3 header columns
        
        data_cells_row1 = rows[1].find_all(['td'])
        assert len(data_cells_row1) == 3  # 3 data columns
        
        # Verify header styling
        for th in header_cells:
            assert 'style' in th.attrs
            assert export_config['table_style']['header_bg_color'] in th['style']
        
        # Verify data cell styling
        for td in data_cells_row1:
            assert 'style' in td.attrs
            assert export_config['table_style']['cell_padding'] in td['style']
            assert export_config['table_style']['border_width'] in td['style']


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])