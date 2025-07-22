"""
WeasyPrint PDF Generation Service

This service handles HTML-to-PDF conversion using WeasyPrint with Inter font support.
Provides functionality to generate PDF files from HTML content with proper formatting.
Includes error handling, validation, and consistent styling.
"""

import logging
import re
import os
import tempfile
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple, Union
from pathlib import Path
import html
from bs4 import BeautifulSoup
import bleach

# Try to import WeasyPrint, but provide a helpful error if it's not installed
try:
    from weasyprint import HTML, CSS
    from weasyprint.text.fonts import FontConfiguration
    WEASYPRINT_AVAILABLE = True
except ImportError:
    WEASYPRINT_AVAILABLE = False
    import warnings
    warnings.warn(
        "WeasyPrint is not installed. Please install it with 'pip install weasyprint>=60.0'. "
        "PDF generation will not be available until WeasyPrint is installed."
    )

# Import shared utilities
from backend.utils.metrics import pdf_metrics
from backend.services.export_manager import ExportFormatManager
from backend.services.document_formatter import DocumentFormatter

logger = logging.getLogger(__name__)

# Configuration constants for validation and limits
class WeasyPrintConfig:
    # File size limits (in bytes)
    MAX_PDF_SIZE = 50 * 1024 * 1024  # 50MB
    MIN_PDF_SIZE = 100  # 100 bytes minimum
    
    # Content limits
    MAX_HTML_SIZE = 10 * 1024 * 1024  # 10MB HTML content
    MIN_HTML_SIZE = 1  # 1 byte minimum
    
    # Font configuration
    FONT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static", "fonts")
    INTER_FONT_PATH = os.path.join(FONT_DIR, "Inter-Regular.ttf")
    INTER_BOLD_PATH = os.path.join(FONT_DIR, "Inter-Bold.ttf")
    INTER_ITALIC_PATH = os.path.join(FONT_DIR, "Inter-Italic.ttf")
    
    # Temp directory for PDF generation
    TEMP_DIR = os.path.join(tempfile.gettempdir(), "weasyprint_generator")
    
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


class WeasyPrintError(Exception):
    """Custom exception for WeasyPrint PDF generation failures"""
    def __init__(self, message: str, error_code: str = "pdf_generation_failed", retry_possible: bool = False):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.retry_possible = retry_possible


class PDFValidationError(WeasyPrintError):
    """Exception for PDF validation failures"""
    def __init__(self, message: str, error_code: str = "pdf_validation_failed"):
        super().__init__(message, error_code, retry_possible=False)


class HTMLValidationError(WeasyPrintError):
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
        if content_size < WeasyPrintConfig.MIN_HTML_SIZE:
            raise HTMLValidationError("HTML content is too small")
        
        if content_size > WeasyPrintConfig.MAX_HTML_SIZE:
            raise HTMLValidationError(
                f"HTML content is too large ({content_size} bytes). Maximum allowed: {WeasyPrintConfig.MAX_HTML_SIZE} bytes"
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
                tags=WeasyPrintConfig.ALLOWED_HTML_TAGS,
                attributes=WeasyPrintConfig.ALLOWED_HTML_ATTRIBUTES,
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
        if pdf_size < WeasyPrintConfig.MIN_PDF_SIZE:
            raise PDFValidationError(f"Generated PDF is too small ({pdf_size} bytes). Minimum: {WeasyPrintConfig.MIN_PDF_SIZE} bytes")
        
        if pdf_size > WeasyPrintConfig.MAX_PDF_SIZE:
            raise PDFValidationError(
                f"Generated PDF is too large ({pdf_size} bytes). Maximum allowed: {WeasyPrintConfig.MAX_PDF_SIZE} bytes"
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
    
    if isinstance(error, (WeasyPrintError, PDFValidationError, HTMLValidationError)):
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
        elif "font" in error.message.lower():
            error_response["retry_possible"] = True
            error_response["details"] = "Font loading issue. Please check font configuration"
        elif "css" in error.message.lower():
            error_response["retry_possible"] = False
            error_response["details"] = "CSS processing error. Please check your styles"
    else:
        # Generic error handling
        error_response.update({
            "error": "internal_server_error",
            "message": "An internal server error occurred",
            "details": "Please try again later or contact support if the problem persists"
        })
    
    return error_response


def ensure_font_directory():
    """
    Ensure the font directory exists and create it if needed
    """
    os.makedirs(WeasyPrintConfig.FONT_DIR, exist_ok=True)


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


class WeasyPrintGenerator:
    """Service for generating PDF files from HTML content using WeasyPrint with Inter font support"""
    
    def __init__(self, export_config: Optional[Dict] = None):
        """
        Initialize the WeasyPrint generator with font configuration
        
        Args:
            export_config: Optional configuration for export formatting
        """
        # Check if WeasyPrint is available
        if not WEASYPRINT_AVAILABLE:
            logger.error("WeasyPrint is not installed. PDF generation will not be available.")
            self.font_config = None
            return
            
        # Ensure font directory exists
        ensure_font_directory()
        
        # Initialize font configuration
        self.font_config = FontConfiguration()
        
        # Initialize export format manager for consistent styling
        self.export_manager = ExportFormatManager(export_config)
        
        # Initialize document formatter for title and cover page handling
        self.document_formatter = DocumentFormatter(export_config)
        
        # Ensure temp directory exists
        os.makedirs(WeasyPrintConfig.TEMP_DIR, exist_ok=True)
        
        logger.info("WeasyPrint PDF generator initialized with unified export formatting")
    
    def generate_pdf_from_html(self, html_content: str, title: Optional[str] = None) -> bytes:
        """
        Generate PDF bytes from HTML content with proper CSS styling and validation
        
        Args:
            html_content: The HTML content to convert to PDF
            title: Optional title for the PDF document
            
        Returns:
            bytes: The generated PDF as bytes
            
        Raises:
            WeasyPrintError: If PDF generation fails
            HTMLValidationError: If HTML content is invalid
            PDFValidationError: If generated PDF is invalid
        """
        # Check if WeasyPrint is available
        if not WEASYPRINT_AVAILABLE:
            error_msg = "WeasyPrint is not installed. Please install it with 'pip install weasyprint>=60.0'"
            logger.error(error_msg)
            raise WeasyPrintError(
                error_msg,
                error_code="weasyprint_not_installed",
                retry_possible=False
            )
            
        request_start_time = datetime.now()
        logger.info(f"Starting WeasyPrint PDF generation - Title: {title}, Content size: {len(html_content) if html_content else 0} chars")
        
        try:
            # Step 1: Validate and sanitize HTML content
            logger.debug("Validating HTML content...")
            validated_html = validate_html_content(html_content)
            logger.info("HTML content validation passed")
            
            # Step 2: Add CSS styling for better PDF formatting with Inter font
            logger.debug("Adding PDF styling to HTML content...")
            styled_html = self._add_pdf_styling(validated_html, title)
            
            # Step 3: Create a temporary file for the HTML content
            with tempfile.NamedTemporaryFile(suffix='.html', dir=WeasyPrintConfig.TEMP_DIR, delete=False) as temp_html:
                temp_html_path = temp_html.name
                temp_html.write(styled_html.encode('utf-8'))
            
            try:
                # Step 4: Generate PDF using WeasyPrint with Inter font
                logger.debug("Generating PDF with WeasyPrint...")
                
                # Create HTML object from the temporary file
                html = HTML(filename=temp_html_path)
                
                # Add custom CSS with font configuration
                css = CSS(string=self._get_font_css(), font_config=self.font_config)
                
                # Generate PDF
                pdf_bytes = html.write_pdf(
                    stylesheets=[css],
                    font_config=self.font_config
                )
                
                generation_time = (datetime.now() - request_start_time).total_seconds()
                logger.info(f"PDF generation completed in {generation_time:.2f} seconds")
                
                # Step 5: Validate generated PDF
                logger.debug("Validating generated PDF...")
                validate_pdf_output(pdf_bytes)
                logger.info(f"PDF validation passed - Final size: {len(pdf_bytes)} bytes")
                
                # Track metrics
                pdf_metrics.record_generation(
                    format="pdf",
                    generator="weasyprint",
                    size_bytes=len(pdf_bytes),
                    generation_time_ms=int(generation_time * 1000),
                    success=True
                )
                
                return pdf_bytes
                
            except Exception as e:
                error_str = str(e)
                logger.error(f"WeasyPrint error during PDF generation: {error_str}")
                
                # Track failed metrics
                pdf_metrics.record_generation(
                    format="pdf",
                    generator="weasyprint",
                    size_bytes=0,
                    generation_time_ms=int((datetime.now() - request_start_time).total_seconds() * 1000),
                    success=False,
                    error=error_str
                )
                
                # Categorize different types of WeasyPrint errors
                if "font" in error_str.lower():
                    raise WeasyPrintError(
                        f"Font error during PDF generation: {error_str}",
                        error_code="font_error",
                        retry_possible=True
                    )
                elif "css" in error_str.lower():
                    raise WeasyPrintError(
                        f"CSS error during PDF generation: {error_str}",
                        error_code="css_error",
                        retry_possible=False
                    )
                elif "memory" in error_str.lower():
                    raise WeasyPrintError(
                        f"Memory error during PDF generation: {error_str}",
                        error_code="memory_error",
                        retry_possible=True
                    )
                else:
                    raise WeasyPrintError(
                        f"PDF generation failed: {error_str}",
                        error_code="pdf_generation_failed",
                        retry_possible=False
                    )
            finally:
                # Clean up temporary HTML file
                try:
                    if os.path.exists(temp_html_path):
                        os.unlink(temp_html_path)
                except Exception as e:
                    logger.warning(f"Failed to delete temporary HTML file: {str(e)}")
                
        except (WeasyPrintError, HTMLValidationError, PDFValidationError) as e:
            # Re-raise our custom exceptions with proper logging
            logger.error(f"PDF generation failed: {str(e)}")
            raise
        except Exception as e:
            # Catch any other unexpected errors
            error_msg = f"Unexpected error in PDF generation: {str(e)}"
            logger.error(error_msg)
            raise WeasyPrintError(
                error_msg,
                error_code="unexpected_error",
                retry_possible=False
            )
    
    def _add_pdf_styling(self, html_content: str, title: Optional[str] = None) -> str:
        """
        Add CSS styling optimized for PDF output with Inter font
        
        Args:
            html_content: Original HTML content
            title: Optional document title
            
        Returns:
            str: HTML content with PDF-optimized CSS styling
        """
        # Get CSS from the unified export format manager
        css_content = self.export_manager.get_css_template()
        
        # Add WeasyPrint-specific page rules
        weasyprint_page_css = """
        @page {
            size: A4;
            margin: 2cm 1.5cm;
            @top-center {
                content: string(title);
                font-family: 'Inter', sans-serif;
                font-size: 9pt;
                color: #666;
            }
            @bottom-center {
                content: "Page " counter(page) " of " counter(pages);
                font-family: 'Inter', sans-serif;
                font-size: 9pt;
                color: #666;
            }
        }
        
        /* Cover page specific styling */
        @page cover {
            @top-center { content: ''; }
            @bottom-center { content: ''; }
        }
        
        /* Set title for page headers */
        h1 { string-set: title content(); }
        """
        
        # Combine the unified CSS with WeasyPrint-specific rules
        pdf_css = f"""
        <style>
            {css_content}
            {weasyprint_page_css}
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
                    {html_content}
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
    
    def _get_font_css(self) -> str:
        """
        Get CSS for Inter font configuration
        
        Returns:
            str: CSS with Inter font configuration
        """
        return """
        @font-face {
            font-family: 'Inter';
            src: url('file://{0}') format('truetype');
            font-weight: normal;
            font-style: normal;
        }
        
        @font-face {
            font-family: 'Inter';
            src: url('file://{1}') format('truetype');
            font-weight: bold;
            font-style: normal;
        }
        
        @font-face {
            font-family: 'Inter';
            src: url('file://{2}') format('truetype');
            font-weight: normal;
            font-style: italic;
        }
        """.format(
            WeasyPrintConfig.INTER_FONT_PATH,
            WeasyPrintConfig.INTER_BOLD_PATH,
            WeasyPrintConfig.INTER_ITALIC_PATH
        )
    
    def generate_pdf_with_cover_page(self, html_content: str, title: str, metadata: Optional[Dict] = None) -> bytes:
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
            return self.generate_pdf_from_html(formatted_html, title)
        finally:
            # Restore original cover page mode
            self.document_formatter.cover_page_mode = original_mode