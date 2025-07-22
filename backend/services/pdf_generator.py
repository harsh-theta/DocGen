"""
PDF Generation Service

This service handles HTML-to-PDF conversion using Playwright.
Provides functionality to generate PDF files from HTML content with proper formatting.
Includes performance optimizations, temporary file cleanup, and metrics collection.
"""

import asyncio
import logging
import re
import time
import gc
import psutil
import shutil
import random
from typing import Optional, Dict, Any, List, Tuple
from playwright.async_api import async_playwright
import tempfile
import os
from datetime import datetime
import html
from bs4 import BeautifulSoup
import bleach
from backend.utils.metrics import pdf_metrics
from backend.services.export_manager import ExportFormatManager
from backend.services.document_formatter import DocumentFormatter

logger = logging.getLogger(__name__)

# Configuration constants for validation and limits
class PDFConfig:
    # File size limits (in bytes)
    MAX_PDF_SIZE = 50 * 1024 * 1024  # 50MB
    MIN_PDF_SIZE = 100  # 100 bytes minimum
    
    # Content limits
    MAX_HTML_SIZE = 10 * 1024 * 1024  # 10MB HTML content
    MIN_HTML_SIZE = 1  # 1 byte minimum
    
    # Processing timeouts (in milliseconds)
    PAGE_LOAD_TIMEOUT = 60000  # 60 seconds
    PDF_GENERATION_TIMEOUT = 120000  # 2 minutes
    
    # Performance optimization settings
    MEMORY_THRESHOLD_PERCENT = 85  # Trigger cleanup when memory usage exceeds this percentage
    TEMP_FILE_MAX_AGE_HOURS = 24  # Maximum age for temporary files before cleanup
    TEMP_DIR = os.path.join(tempfile.gettempdir(), "pdf_generator")  # Custom temp directory for PDF generation
    CHUNK_SIZE = 1024 * 1024  # 1MB chunks for processing large documents
    MAX_CONCURRENT_GENERATIONS = 5  # Maximum concurrent PDF generations
    
    # Allowed HTML tags for security
    ALLOWED_HTML_TAGS = [
        'p', 'br', 'div', 'span', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
        'strong', 'b', 'em', 'i', 'u', 'strike', 'del', 'ins',
        'ul', 'ol', 'li', 'dl', 'dt', 'dd',
        'blockquote', 'pre', 'code',
        'table', 'thead', 'tbody', 'tr', 'th', 'td',
        'img', 'a', 'hr',
        'sub', 'sup', 'small', 'mark'
    ]
    
    # Allowed HTML attributes
    ALLOWED_HTML_ATTRIBUTES = {
        '*': ['class', 'id', 'style'],
        'a': ['href', 'title', 'target'],
        'img': ['src', 'alt', 'title', 'width', 'height'],
        'table': ['border', 'cellpadding', 'cellspacing'],
        'th': ['colspan', 'rowspan', 'scope'],
        'td': ['colspan', 'rowspan']
    }


class PDFGenerationError(Exception):
    """Custom exception for PDF generation failures"""
    def __init__(self, message: str, error_code: str = "pdf_generation_failed", retry_possible: bool = False):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.retry_possible = retry_possible


class PDFValidationError(PDFGenerationError):
    """Exception for PDF validation failures"""
    def __init__(self, message: str, error_code: str = "pdf_validation_failed"):
        super().__init__(message, error_code, retry_possible=False)


class HTMLValidationError(PDFGenerationError):
    """Exception for HTML validation failures"""
    def __init__(self, message: str, error_code: str = "html_validation_failed"):
        super().__init__(message, error_code, retry_possible=False)


def validate_html_content(html_content: str) -> str:
    """
    Validate and sanitize HTML content before PDF generation
    
    Args:
        html_content: The HTML content to validate
        
    Returns:
        str: Sanitized HTML content
        
    Raises:
        HTMLValidationError: If HTML content is invalid or unsafe
    """
    try:
        # Check content size limits
        if not html_content:
            raise HTMLValidationError("HTML content cannot be empty")
        
        content_size = len(html_content.encode('utf-8'))
        if content_size < PDFConfig.MIN_HTML_SIZE:
            raise HTMLValidationError("HTML content is too small")
        
        if content_size > PDFConfig.MAX_HTML_SIZE:
            raise HTMLValidationError(
                f"HTML content is too large ({content_size} bytes). Maximum allowed: {PDFConfig.MAX_HTML_SIZE} bytes"
            )
        
        # Basic HTML structure validation
        stripped_content = html_content.strip()
        if not stripped_content:
            raise HTMLValidationError("HTML content cannot be empty after stripping whitespace")
        
        # Check for potentially malicious content
        if any(dangerous in html_content.lower() for dangerous in ['<script', 'javascript:', 'vbscript:', 'onload=', 'onerror=']):
            logger.warning("Potentially malicious content detected in HTML")
            # Sanitize the content instead of rejecting it
            sanitized_content = bleach.clean(
                html_content,
                tags=PDFConfig.ALLOWED_HTML_TAGS,
                attributes=PDFConfig.ALLOWED_HTML_ATTRIBUTES,
                strip=True
            )
            logger.info("HTML content sanitized for security")
            return sanitized_content
        
        # Validate HTML structure using BeautifulSoup
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Check if parsing was successful
            if not soup or not soup.get_text(strip=True):
                raise HTMLValidationError("HTML content appears to be empty or invalid")
            
            # Check for excessively nested content that might cause issues
            max_depth = 50  # Maximum nesting depth
            def check_depth(element, current_depth=0):
                if current_depth > max_depth:
                    raise HTMLValidationError(f"HTML content is too deeply nested (max depth: {max_depth})")
                for child in element.children:
                    if hasattr(child, 'children'):
                        check_depth(child, current_depth + 1)
            
            check_depth(soup)
            
        except Exception as e:
            if isinstance(e, HTMLValidationError):
                raise
            logger.warning(f"HTML parsing warning: {str(e)}")
            # Don't fail for minor parsing issues, just log them
        
        # Return the original content if validation passes
        return html_content
        
    except HTMLValidationError:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during HTML validation: {str(e)}")
        raise HTMLValidationError(f"HTML validation failed: {str(e)}")


def validate_pdf_output(pdf_bytes: bytes) -> None:
    """
    Validate generated PDF output
    
    Args:
        pdf_bytes: The generated PDF bytes to validate
        
    Raises:
        PDFValidationError: If PDF is invalid or doesn't meet requirements
    """
    try:
        # Check if PDF bytes exist
        if not pdf_bytes:
            raise PDFValidationError("PDF generation produced no output")
        
        # Check PDF size limits
        pdf_size = len(pdf_bytes)
        if pdf_size < PDFConfig.MIN_PDF_SIZE:
            raise PDFValidationError(f"Generated PDF is too small ({pdf_size} bytes). Minimum: {PDFConfig.MIN_PDF_SIZE} bytes")
        
        if pdf_size > PDFConfig.MAX_PDF_SIZE:
            raise PDFValidationError(
                f"Generated PDF is too large ({pdf_size} bytes). Maximum allowed: {PDFConfig.MAX_PDF_SIZE} bytes"
            )
        
        # Basic PDF format validation - check for PDF header
        if not pdf_bytes.startswith(b'%PDF-'):
            raise PDFValidationError("Generated file is not a valid PDF (missing PDF header)")
        
        # Check for PDF trailer (basic structure validation)
        if b'%%EOF' not in pdf_bytes[-1024:]:  # Check last 1KB for EOF marker
            logger.warning("PDF may be incomplete - EOF marker not found in expected location")
            # Don't fail for this, as some PDFs might have different structures
        
        logger.info(f"PDF validation passed - size: {pdf_size} bytes")
        
    except PDFValidationError:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during PDF validation: {str(e)}")
        raise PDFValidationError(f"PDF validation failed: {str(e)}")


def create_error_response(error: Exception, request_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Create standardized error response format
    
    Args:
        error: The exception that occurred
        request_id: Optional request ID for tracking
        
    Returns:
        Dict containing standardized error response
    """
    error_response = {
        "error": "unknown_error",
        "message": "An unexpected error occurred",
        "details": None,
        "retry_possible": False,
        "timestamp": datetime.now().isoformat()
    }
    
    if request_id:
        error_response["request_id"] = request_id
    
    if isinstance(error, (PDFGenerationError, PDFValidationError, HTMLValidationError)):
        error_response.update({
            "error": error.error_code,
            "message": error.message,
            "retry_possible": error.retry_possible
        })
        
        # Add specific guidance based on error type
        if isinstance(error, HTMLValidationError):
            error_response["details"] = "Please check your HTML content for invalid tags or excessive size"
        elif isinstance(error, PDFValidationError):
            error_response["details"] = "The generated PDF did not meet quality requirements"
        elif "timeout" in error.message.lower():
            error_response["retry_possible"] = True
            error_response["details"] = "The operation timed out. Try with simpler content or retry later"
        elif "network" in error.message.lower():
            error_response["retry_possible"] = True
            error_response["details"] = "Network connectivity issue. Please retry"
        elif "storage" in error.message.lower():
            error_response["retry_possible"] = True
            error_response["details"] = "File storage issue. Please retry or contact support"
    else:
        # Generic error handling
        error_response.update({
            "error": "internal_server_error",
            "message": "An internal server error occurred",
            "details": "Please try again later or contact support if the problem persists"
        })
    
    return error_response


class PDFGenerator:
    """Service for generating PDF files from HTML content"""
    
    def __init__(self, export_config: Optional[Dict] = None):
        """
        Initialize the PDF generator
        
        Args:
            export_config: Optional configuration for export formatting
        """
        self._browser = None
        self._playwright = None
        
        # Initialize export format manager for consistent styling
        self.export_manager = ExportFormatManager(export_config)
        
        # Initialize document formatter for title and cover page handling
        self.document_formatter = DocumentFormatter(export_config)
    
    async def __aenter__(self):
        """Async context manager entry"""
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(headless=True)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
    
    async def generate_pdf_from_html(self, html_content: str, title: Optional[str] = None) -> bytes:
        """
        Generate PDF bytes from HTML content with proper CSS styling and validation
        
        Args:
            html_content: The HTML content to convert to PDF
            title: Optional title for the PDF document
            
        Returns:
            bytes: The generated PDF as bytes
            
        Raises:
            PDFGenerationError: If PDF generation fails
            HTMLValidationError: If HTML content is invalid
            PDFValidationError: If generated PDF is invalid
        """
        request_start_time = datetime.now()
        logger.info(f"Starting PDF generation - Title: {title}, Content size: {len(html_content) if html_content else 0} chars")
        
        try:
            if not self._browser:
                raise PDFGenerationError(
                    "PDF generator not initialized. Use as async context manager.",
                    error_code="generator_not_initialized"
                )
            
            # Step 1: Validate and sanitize HTML content
            logger.debug("Validating HTML content...")
            validated_html = validate_html_content(html_content)
            logger.info("HTML content validation passed")
            
            # Create a new page with enhanced error handling
            page = await self._browser.new_page()
            
            try:
                # Step 2: Add CSS styling for better PDF formatting
                logger.debug("Adding PDF styling to HTML content...")
                styled_html = self._add_pdf_styling(validated_html, title)
                
                # Step 3: Set the HTML content with proper wait conditions and timeout
                logger.debug("Loading HTML content into browser page...")
                await asyncio.wait_for(
                    page.set_content(styled_html, wait_until="networkidle"),
                    timeout=PDFConfig.PAGE_LOAD_TIMEOUT / 1000  # Convert to seconds
                )
                logger.info("HTML content loaded successfully")
                
                # Step 4: Configure PDF options for optimal output
                pdf_options = {
                    "format": "A4",
                    "print_background": True,
                    "prefer_css_page_size": False,
                    "margin": {
                        "top": "2cm",
                        "right": "1.5cm",
                        "bottom": "2cm",
                        "left": "1.5cm"
                    }
                }
                
                # Add header and footer if title is provided
                if title:
                    pdf_options["display_header_footer"] = True
                    pdf_options["header_template"] = self._get_header_template(title)
                    pdf_options["footer_template"] = self._get_footer_template()
                
                # Step 5: Generate PDF with timeout
                logger.debug("Generating PDF from HTML content...")
                pdf_bytes = await asyncio.wait_for(
                    page.pdf(**pdf_options),
                    timeout=PDFConfig.PDF_GENERATION_TIMEOUT / 1000  # Convert to seconds
                )
                
                generation_time = (datetime.now() - request_start_time).total_seconds()
                logger.info(f"PDF generation completed in {generation_time:.2f} seconds")
                
                # Step 6: Validate generated PDF
                logger.debug("Validating generated PDF...")
                validate_pdf_output(pdf_bytes)
                logger.info(f"PDF validation passed - Final size: {len(pdf_bytes)} bytes")
                
                return pdf_bytes
                
            except asyncio.TimeoutError as e:
                error_msg = "PDF generation timed out - content may be too complex or large"
                logger.error(f"{error_msg}. Timeout after {PDFConfig.PDF_GENERATION_TIMEOUT/1000}s")
                raise PDFGenerationError(
                    error_msg,
                    error_code="pdf_generation_timeout",
                    retry_possible=True
                )
            except (HTMLValidationError, PDFValidationError):
                # Re-raise validation errors as-is
                raise
            except Exception as e:
                error_str = str(e)
                logger.error(f"Browser error during PDF generation: {error_str}")
                
                # Categorize different types of browser errors
                if "net::ERR_" in error_str:
                    raise PDFGenerationError(
                        f"Network error during PDF generation: {error_str}",
                        error_code="network_error",
                        retry_possible=True
                    )
                elif "Protocol error" in error_str or "Target closed" in error_str:
                    raise PDFGenerationError(
                        f"Browser protocol error: {error_str}",
                        error_code="browser_protocol_error",
                        retry_possible=True
                    )
                elif "Navigation failed" in error_str:
                    raise PDFGenerationError(
                        f"Failed to load content: {error_str}",
                        error_code="content_load_failed",
                        retry_possible=False
                    )
                else:
                    raise PDFGenerationError(
                        f"PDF generation failed: {error_str}",
                        error_code="pdf_generation_failed",
                        retry_possible=False
                    )
            finally:
                # Always close the page to prevent resource leaks
                try:
                    await page.close()
                    logger.debug("Browser page closed successfully")
                except Exception as e:
                    logger.warning(f"Failed to close browser page: {str(e)}")
                
        except (PDFGenerationError, HTMLValidationError, PDFValidationError) as e:
            # Re-raise our custom exceptions with proper logging
            logger.error(f"PDF generation failed: {str(e)}")
            raise
        except Exception as e:
            # Catch any other unexpected errors
            error_msg = f"Unexpected error in PDF generation: {str(e)}"
            logger.error(error_msg)
            raise PDFGenerationError(
                error_msg,
                error_code="unexpected_error",
                retry_possible=False
            )
    
    def _add_pdf_styling(self, html_content: str, title: Optional[str] = None) -> str:
        """
        Add CSS styling optimized for PDF output
        
        Args:
            html_content: Original HTML content
            title: Optional document title
            
        Returns:
            str: HTML content with PDF-optimized CSS styling
        """
        # Get CSS from the unified export format manager
        css_content = self.export_manager.get_css_template()
        
        # Add Playwright-specific page rules
        playwright_page_css = """
        @page {
            size: A4;
            margin: 0;
        }
        
        .pdf-content {
            padding: 1cm;
            min-height: calc(100vh - 2cm);
        }
        
        /* Print-specific styles */
        @media print {
            body {
                -webkit-print-color-adjust: exact;
                print-color-adjust: exact;
            }
        }
        """
        
        # Combine the unified CSS with Playwright-specific rules
        pdf_css = f"""
        <style>
            {css_content}
            {playwright_page_css}
        </style>
        """
        
        # Format document with proper title placement and cover page if needed
        if title:
            metadata = {"date": datetime.now().strftime("%B %d, %Y")}
            html_content = self.document_formatter.format_document(html_content, title, metadata)
        
        # Wrap content in a proper HTML structure if it's not already
        if not html_content.strip().lower().startswith('<!doctype') and not html_content.strip().lower().startswith('<html'):
            # Check if content already has body tags
            if '<body' not in html_content.lower():
                wrapped_content = f"""
                <!DOCTYPE html>
                <html lang="en">
                <head>
                    <meta charset="UTF-8">
                    <meta name="viewport" content="width=device-width, initial-scale=1.0">
                    {f'<title>{title}</title>' if title else '<title>Document</title>'}
                    {pdf_css}
                </head>
                <body>
                    <div class="pdf-content">
                        {html_content}
                    </div>
                </body>
                </html>
                """
            else:
                # Insert CSS into existing HTML structure
                if '<head>' in html_content.lower():
                    wrapped_content = html_content.replace('<head>', f'<head>{pdf_css}', 1)
                else:
                    wrapped_content = html_content.replace('<html>', f'<html><head>{pdf_css}</head>', 1)
        else:
            # HTML is already complete, just inject CSS
            if '<head>' in html_content.lower():
                wrapped_content = html_content.replace('</head>', f'{pdf_css}</head>', 1)
            else:
                wrapped_content = html_content.replace('<html>', f'<html><head>{pdf_css}</head>', 1)
        
        return wrapped_content
    
    def _get_header_template(self, title: str) -> str:
        """Generate header template for PDF"""
        return f"""
        <div style="font-size: 10px; padding: 5px 15px; width: 100%; 
                    border-bottom: 1px solid #ccc; display: flex; 
                    justify-content: space-between; align-items: center;">
            <span style="font-weight: bold;">{title}</span>
            <span>Generated on {datetime.now().strftime('%Y-%m-%d %H:%M')}</span>
        </div>
        """
    
    def _get_footer_template(self) -> str:
        """Generate footer template for PDF"""
        return """
        <div style="font-size: 10px; padding: 5px 15px; width: 100%; 
                    border-top: 1px solid #ccc; display: flex; 
                    justify-content: center; align-items: center;">
            <span>Page <span class="pageNumber"></span> of <span class="totalPages"></span></span>
        </div>
        """
        
    async def generate_pdf_with_cover_page(self, html_content: str, title: str, metadata: Optional[Dict] = None) -> bytes:
        """
        Generate PDF with a cover page
        
        Args:
            html_content: The HTML content for the document body
            title: Title for the cover page and document
            metadata: Optional metadata dictionary for the cover page
            
        Returns:
            bytes: The generated PDF as bytes
        """
        # Use the document formatter to handle cover page generation
        if metadata is None:
            metadata = {"date": datetime.now().strftime("%B %d, %Y")}
        
        # Save the current cover page mode
        original_mode = self.document_formatter.cover_page_mode
        
        try:
            # Force full cover page mode for this operation
            self.document_formatter.cover_page_mode = 'full'
            
            # Format the document with cover page
            formatted_html = self.document_formatter.format_document(html_content, title, metadata)
            
            # Generate PDF with formatted content
            return await self.generate_pdf_from_html(formatted_html, title)
        finally:
            # Restore original cover page mode
            self.document_formatter.cover_page_mode = original_mode


def sanitize_filename(filename: str, max_length: int = 100) -> str:
    """
    Sanitize filename for safe file system usage
    
    Args:
        filename: The original filename to sanitize
        max_length: Maximum length for the filename (default: 100)
        
    Returns:
        str: Sanitized filename safe for file system usage
    """
    if not filename or not filename.strip():
        # Use timestamp if no filename provided
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"document_{timestamp}.pdf"
    
    # Remove or replace invalid characters
    # Invalid characters for most file systems: < > : " | ? * \ /
    sanitized = re.sub(r'[<>:"|?*\\/]', '_', filename.strip())
    
    # Replace multiple spaces with single space
    sanitized = re.sub(r'\s+', ' ', sanitized)
    
    # Remove leading/trailing dots and spaces
    sanitized = sanitized.strip('. ')
    
    # Ensure it doesn't start with a dot (hidden file)
    if sanitized.startswith('.'):
        sanitized = 'document' + sanitized
    
    # Ensure .pdf extension first
    if not sanitized.lower().endswith('.pdf'):
        # Remove any existing extension first
        if '.' in sanitized:
            sanitized = sanitized.rsplit('.', 1)[0]
        sanitized += '.pdf'
    
    # Truncate if too long, preserving .pdf extension
    if len(sanitized) > max_length:
        # Reserve space for .pdf extension
        max_name_length = max_length - 4  # 4 chars for ".pdf"
        name_part = sanitized[:-4]  # Remove .pdf
        sanitized = name_part[:max_name_length] + '.pdf'
    
    # Final fallback if somehow empty
    if not sanitized or sanitized == '.pdf':
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        sanitized = f"document_{timestamp}.pdf"
    
    return sanitized


def generate_unique_filename(base_filename: str) -> str:
    """
    Generate a unique filename by adding timestamp
    
    Args:
        base_filename: The base filename to make unique
        
    Returns:
        str: Unique filename with timestamp
    """
    sanitized_base = sanitize_filename(base_filename)
    
    # Remove .pdf extension temporarily
    if sanitized_base.lower().endswith('.pdf'):
        name_part = sanitized_base[:-4]
    else:
        name_part = sanitized_base
    
    # Add timestamp for uniqueness
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]  # Include milliseconds
    unique_filename = f"{name_part}_{timestamp}.pdf"
    
    return unique_filename


# Semaphore to limit concurrent PDF generations
_pdf_generation_semaphore = asyncio.Semaphore(PDFConfig.MAX_CONCURRENT_GENERATIONS)

# Track temporary files created during PDF generation
_temp_files = []

def cleanup_temp_files(max_age_hours: int = None) -> int:
    """
    Clean up temporary files created during PDF generation
    
    Args:
        max_age_hours: Maximum age of files to keep (in hours)
                      If None, uses PDFConfig.TEMP_FILE_MAX_AGE_HOURS
    
    Returns:
        int: Number of files deleted
    """
    if max_age_hours is None:
        max_age_hours = PDFConfig.TEMP_FILE_MAX_AGE_HOURS
    
    # Ensure temp directory exists
    os.makedirs(PDFConfig.TEMP_DIR, exist_ok=True)
    
    # Calculate cutoff time
    cutoff_time = time.time() - (max_age_hours * 3600)
    deleted_count = 0
    
    try:
        # Clean tracked temp files first
        global _temp_files
        for temp_file in list(_temp_files):
            try:
                if os.path.exists(temp_file):
                    file_mtime = os.path.getmtime(temp_file)
                    if file_mtime < cutoff_time:
                        os.remove(temp_file)
                        _temp_files.remove(temp_file)
                        deleted_count += 1
                        logger.debug(f"Deleted tracked temp file: {temp_file}")
                else:
                    # File already gone, remove from tracking
                    _temp_files.remove(temp_file)
            except Exception as e:
                logger.warning(f"Error cleaning up temp file {temp_file}: {str(e)}")
        
        # Clean all files in temp directory older than cutoff
        for filename in os.listdir(PDFConfig.TEMP_DIR):
            file_path = os.path.join(PDFConfig.TEMP_DIR, filename)
            try:
                if os.path.isfile(file_path):
                    file_mtime = os.path.getmtime(file_path)
                    if file_mtime < cutoff_time:
                        os.remove(file_path)
                        deleted_count += 1
                        logger.debug(f"Deleted old temp file: {file_path}")
            except Exception as e:
                logger.warning(f"Error cleaning up temp directory file {file_path}: {str(e)}")
        
        logger.info(f"Temporary file cleanup completed: {deleted_count} files deleted")
        return deleted_count
        
    except Exception as e:
        logger.error(f"Error during temporary file cleanup: {str(e)}")
        return deleted_count


def check_system_resources() -> Dict[str, Any]:
    """
    Check system resources and trigger cleanup if needed
    
    Returns:
        Dict with resource usage information
    """
    try:
        # Get memory usage
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        
        # Get disk usage for temp directory
        temp_dir = PDFConfig.TEMP_DIR
        os.makedirs(temp_dir, exist_ok=True)
        disk = psutil.disk_usage(temp_dir)
        disk_percent = disk.percent
        
        # Get CPU usage
        cpu_percent = psutil.cpu_percent(interval=0.1)
        
        resources = {
            "memory_percent": memory_percent,
            "disk_percent": disk_percent,
            "cpu_percent": cpu_percent,
            "memory_critical": memory_percent > PDFConfig.MEMORY_THRESHOLD_PERCENT,
            "disk_critical": disk_percent > 90,  # 90% disk usage is critical
            "temp_files_count": len(_temp_files)
        }
        
        # Trigger cleanup if memory usage is high
        if resources["memory_critical"]:
            logger.warning(f"Memory usage critical ({memory_percent}%), triggering cleanup")
            # Force garbage collection
            gc.collect()
            # Clean up temp files
            deleted = cleanup_temp_files(max_age_hours=1)  # More aggressive cleanup (1 hour)
            resources["cleanup_triggered"] = True
            resources["files_deleted"] = deleted
        
        return resources
        
    except Exception as e:
        logger.error(f"Error checking system resources: {str(e)}")
        return {"error": str(e)}


async def optimize_large_html_content(html_content: str) -> str:
    """
    Optimize large HTML content for better performance
    
    Args:
        html_content: The HTML content to optimize
        
    Returns:
        str: Optimized HTML content
    """
    # Only optimize if content is large
    if len(html_content) < 100000:  # Less than 100KB
        return html_content
    
    try:
        # Parse with BeautifulSoup
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Remove comments
        for comment in soup.find_all(string=lambda text: isinstance(text, str) and text.strip().startswith('<!--')):
            comment.extract()
        
        # Remove unnecessary whitespace
        for tag in soup.find_all():
            if tag.string and isinstance(tag.string, str):
                tag.string = re.sub(r'\s+', ' ', tag.string.strip())
        
        # Limit image sizes
        for img in soup.find_all('img'):
            if img.get('width') and img.get('height'):
                try:
                    width = int(img['width'])
                    if width > 1000:
                        img['width'] = '1000'
                        if img.get('height'):
                            # Maintain aspect ratio
                            height = int(img['height'])
                            img['height'] = str(int(height * (1000 / width)))
                except (ValueError, TypeError):
                    pass
        
        # Return optimized HTML
        return str(soup)
        
    except Exception as e:
        logger.warning(f"Error optimizing HTML content: {str(e)}, using original content")
        return html_content


async def generate_pdf_from_html(html_content: str, title: Optional[str] = None, 
                                document_id: Optional[str] = None, 
                                user_id: Optional[str] = None) -> bytes:
    """
    Convenience function to generate PDF from HTML content with performance optimizations
    
    Args:
        html_content: The HTML content to convert to PDF
        title: Optional title for the PDF document
        document_id: Optional document ID for metrics tracking
        user_id: Optional user ID for metrics tracking
        
    Returns:
        bytes: The generated PDF as bytes
        
    Raises:
        PDFGenerationError: If PDF generation fails
    """
    start_time = time.time()
    pdf_size = None
    success = False
    error_type = None
    error_message = None
    
    try:
        # Check system resources before processing
        resources = check_system_resources()
        if resources.get("memory_critical", False):
            logger.warning("Memory usage critical, PDF generation may be affected")
        
        # Optimize large HTML content
        optimized_html = await optimize_large_html_content(html_content)
        
        # Use semaphore to limit concurrent generations
        async with _pdf_generation_semaphore:
            # Create a temporary file for any intermediate processing
            with tempfile.NamedTemporaryFile(suffix='.html', dir=PDFConfig.TEMP_DIR, delete=False) as temp_file:
                temp_path = temp_file.name
                _temp_files.append(temp_path)
                
                try:
                    # Generate PDF with optimized content
                    async with PDFGenerator() as generator:
                        pdf_bytes = await generator.generate_pdf_from_html(optimized_html, title)
                    
                    # Record success metrics
                    pdf_size = len(pdf_bytes)
                    success = True
                    
                    return pdf_bytes
                    
                finally:
                    # Clean up temporary file
                    try:
                        if os.path.exists(temp_path):
                            os.unlink(temp_path)
                            if temp_path in _temp_files:
                                _temp_files.remove(temp_path)
                    except Exception as e:
                        logger.warning(f"Failed to delete temporary file {temp_path}: {str(e)}")
    
    except Exception as e:
        error_message = str(e)
        if isinstance(e, PDFGenerationError):
            error_type = e.error_code
        elif isinstance(e, HTMLValidationError):
            error_type = "html_validation_error"
        elif isinstance(e, PDFValidationError):
            error_type = "pdf_validation_error"
        else:
            error_type = "unexpected_error"
        
        # Re-raise the exception
        raise
        
    finally:
        # Record metrics regardless of success or failure
        try:
            pdf_metrics.record_generation_attempt(
                start_time=start_time,
                success=success,
                pdf_size=pdf_size,
                error_type=error_type,
                error_message=error_message,
                document_id=document_id,
                user_id=user_id
            )
        except Exception as metrics_error:
            logger.error(f"Failed to record PDF metrics: {str(metrics_error)}")
        
        # Periodically clean up temp files (1% chance per request)
        if random.random() < 0.01:
            try:
                cleanup_temp_files()
            except Exception as cleanup_error:
                logger.error(f"Failed to clean up temp files: {str(cleanup_error)}")