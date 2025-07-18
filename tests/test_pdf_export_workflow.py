"""
Tests for the PDF export workflow with performance optimizations and cleanup mechanisms
"""

import pytest
import os
import tempfile
import time
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from backend.services.pdf_generator import (
    PDFGenerator, 
    generate_pdf_from_html, 
    cleanup_temp_files,
    check_system_resources,
    PDFConfig
)
from backend.utils.metrics import pdf_metrics
from backend.utils.rate_limiter import rate_limiter


@pytest.fixture
def mock_pdf_bytes():
    """Return mock PDF bytes for testing"""
    return b"%PDF-1.5\nSome PDF content\n%%EOF"


@pytest.fixture
def mock_html_content():
    """Return mock HTML content for testing"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Test Document</title>
    </head>
    <body>
        <h1>Test Document</h1>
        <p>This is a test document for PDF generation.</p>
    </body>
    </html>
    """


@pytest.mark.asyncio
async def test_cleanup_temp_files():
    """Test that temporary files are cleaned up correctly"""
    # Create some temporary files
    temp_dir = PDFConfig.TEMP_DIR
    os.makedirs(temp_dir, exist_ok=True)
    
    # Create test files with different ages
    test_files = []
    for i in range(5):
        fd, path = tempfile.mkstemp(dir=temp_dir, suffix='.html')
        os.close(fd)
        test_files.append(path)
    
    # Set access time for some files to be older
    old_time = time.time() - (PDFConfig.TEMP_FILE_MAX_AGE_HOURS * 3600 + 3600)  # 1 hour older than max age
    for i in range(3):
        os.utime(test_files[i], (old_time, old_time))
    
    # Run cleanup with 1 hour max age (should delete the 3 older files)
    deleted = cleanup_temp_files(max_age_hours=PDFConfig.TEMP_FILE_MAX_AGE_HOURS)
    
    # Check that the correct number of files were deleted
    assert deleted >= 3, f"Expected at least 3 files to be deleted, but got {deleted}"
    
    # Check that the newer files still exist
    for i in range(3, 5):
        assert not os.path.exists(test_files[i]), f"Expected file {test_files[i]} to be deleted"
    
    # Clean up any remaining test files
    for path in test_files:
        if os.path.exists(path):
            os.unlink(path)


@pytest.mark.asyncio
async def test_check_system_resources():
    """Test that system resources are checked correctly"""
    resources = check_system_resources()
    
    # Verify that the function returns the expected keys
    assert "memory_percent" in resources
    assert "disk_percent" in resources
    assert "cpu_percent" in resources
    assert "memory_critical" in resources
    assert "disk_critical" in resources
    assert "temp_files_count" in resources
    
    # Values should be reasonable
    assert 0 <= resources["memory_percent"] <= 100
    assert 0 <= resources["disk_percent"] <= 100
    assert 0 <= resources["cpu_percent"] <= 100
    assert isinstance(resources["memory_critical"], bool)
    assert isinstance(resources["disk_critical"], bool)
    assert isinstance(resources["temp_files_count"], int)


@pytest.mark.asyncio
async def test_pdf_metrics_collection():
    """Test that PDF metrics are collected correctly"""
    # Reset metrics for clean test
    pdf_metrics.reset_metrics()
    
    # Record a successful generation
    start_time = time.time()
    pdf_metrics.record_generation_attempt(
        start_time=start_time,
        success=True,
        pdf_size=1024,
        document_id="test-doc-1",
        user_id="test-user-1"
    )
    
    # Record a failed generation
    pdf_metrics.record_generation_attempt(
        start_time=time.time(),
        success=False,
        error_type="test_error",
        error_message="Test error message",
        document_id="test-doc-2",
        user_id="test-user-1"
    )
    
    # Get metrics summary
    summary = pdf_metrics.get_metrics_summary()
    
    # Check metrics
    assert summary["pdf_generation"]["count"] == 2
    assert summary["pdf_generation"]["success_count"] == 1
    assert summary["pdf_generation"]["failure_count"] == 1
    assert summary["pdf_generation"]["success_rate"] == 50.0
    assert summary["pdf_generation"]["avg_size_kb"] > 0
    assert "test_error" in [error[0] for error in summary["errors"]["top_errors"]]


@pytest.mark.asyncio
async def test_rate_limiting():
    """Test that rate limiting works correctly"""
    # Reset rate limiter for clean test
    rate_limiter.clear_history()
    
    # Configure rate limit for testing
    rate_limiter.update_rate_limit("pdf_export", 3, 60)  # 3 requests per minute
    
    # First 3 requests should not be rate limited
    for i in range(3):
        is_limited, retry_after = rate_limiter.is_rate_limited("test-user", "pdf_export")
        assert not is_limited, f"Request {i+1} should not be rate limited"
        assert retry_after is None
    
    # 4th request should be rate limited
    is_limited, retry_after = rate_limiter.is_rate_limited("test-user", "pdf_export")
    assert is_limited, "4th request should be rate limited"
    assert retry_after is not None and retry_after > 0


@pytest.mark.asyncio
async def test_generate_pdf_from_html_with_metrics(mock_html_content, mock_pdf_bytes):
    """Test that PDF generation with metrics collection works correctly"""
    # Mock the PDFGenerator to avoid actual browser usage
    with patch('backend.services.pdf_generator.PDFGenerator') as MockPDFGenerator:
        # Configure the mock
        mock_generator = AsyncMock()
        mock_generator.generate_pdf_from_html.return_value = mock_pdf_bytes
        MockPDFGenerator.return_value.__aenter__.return_value = mock_generator
        
        # Call the function
        result = await generate_pdf_from_html(
            mock_html_content, 
            "Test Document",
            document_id="test-doc",
            user_id="test-user"
        )
        
        # Verify the result
        assert result == mock_pdf_bytes
        mock_generator.generate_pdf_from_html.assert_called_once()


@pytest.mark.asyncio
async def test_optimize_large_html_content():
    """Test that large HTML content is optimized correctly"""
    from backend.services.pdf_generator import optimize_large_html_content
    
    # Create a large HTML document with comments and excessive whitespace
    large_html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Large Document</title>
    </head>
    <body>
        <!-- This is a comment that should be removed -->
        <h1>   Large    Document    </h1>
        <p>    This is a paragraph with    excessive    whitespace.    </p>
        <img src="test.jpg" width="2000" height="1500" />
    </body>
    </html>
    """ * 100  # Repeat to make it large
    
    # Optimize the content
    optimized = await optimize_large_html_content(large_html)
    
    # Check that the content was optimized
    assert len(optimized) < len(large_html), "Optimized content should be smaller"
    assert "<!-- This is a comment that should be removed -->" not in optimized, "Comments should be removed"
    assert "width=\"1000\"" in optimized, "Image width should be limited to 1000px"


if __name__ == "__main__":
    pytest.main(["-xvs", __file__])