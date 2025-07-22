"""
Tests for the WeasyPrint PDF generator service
"""

import os
import pytest
from backend.services.weasyprint_generator import WeasyPrintGenerator, HTMLValidationError, PDFValidationError, WEASYPRINT_AVAILABLE

# Sample HTML content for testing
SAMPLE_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Test Document</title>
</head>
<body>
    <h1>Test Heading</h1>
    <p>This is a test paragraph with <strong>bold text</strong> and <em>italic text</em>.</p>
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
</body>
</html>
"""

def test_weasyprint_generator_initialization():
    """Test that the WeasyPrint generator initializes correctly"""
    generator = WeasyPrintGenerator()
    assert generator is not None
    
    # Skip font_config check if WeasyPrint is not available
    if WEASYPRINT_AVAILABLE:
        assert generator.font_config is not None

# Mark tests that require WeasyPrint to be installed
weasyprint_required = pytest.mark.skipif(
    not WEASYPRINT_AVAILABLE,
    reason="WeasyPrint is not installed. Install with 'pip install weasyprint>=60.0'"
)

@weasyprint_required
def test_pdf_generation_with_valid_html():
    """Test PDF generation with valid HTML content"""
    generator = WeasyPrintGenerator()
    
    # Generate PDF
    pdf_bytes = generator.generate_pdf_from_html(SAMPLE_HTML, "Test Document")
    
    # Verify PDF was generated
    assert pdf_bytes is not None
    assert len(pdf_bytes) > 0
    assert pdf_bytes.startswith(b'%PDF-')  # PDF signature
    assert b'%%EOF' in pdf_bytes[-1024:]  # PDF EOF marker

@weasyprint_required
def test_pdf_generation_with_empty_html():
    """Test PDF generation with empty HTML content raises appropriate error"""
    generator = WeasyPrintGenerator()
    
    # Try to generate PDF with empty content
    with pytest.raises(HTMLValidationError):
        generator.generate_pdf_from_html("", "Empty Document")

@weasyprint_required
def test_pdf_generation_with_cover_page():
    """Test PDF generation with cover page"""
    generator = WeasyPrintGenerator()
    
    # Generate PDF with cover page
    pdf_bytes = generator.generate_pdf_with_cover_page(
        "<p>This is the document content.</p>",
        "Cover Page Test",
        "July 22, 2025"
    )
    
    # Verify PDF was generated
    assert pdf_bytes is not None
    assert len(pdf_bytes) > 0
    assert pdf_bytes.startswith(b'%PDF-')  # PDF signature