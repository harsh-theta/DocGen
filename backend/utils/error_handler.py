"""
Error handling utilities for export operations.

This module provides standardized error handling, retry mechanisms,
and user-friendly error messages for export operations.
"""

import logging
import time
from typing import Dict, Any, Optional, Callable, Tuple, Union
import functools
import asyncio
from datetime import datetime
import uuid
import traceback

logger = logging.getLogger(__name__)

class ExportError(Exception):
    """Base exception for export-related errors with retry information."""
    
    def __init__(
        self, 
        message: str, 
        error_code: str = "export_error",
        retry_possible: bool = False,
        http_status: int = 500,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.retry_possible = retry_possible
        self.http_status = http_status
        self.details = details or {}
        self.timestamp = datetime.now().isoformat()


class PDFExportError(ExportError):
    """Exception for PDF export failures."""
    
    def __init__(
        self, 
        message: str, 
        error_code: str = "pdf_export_error",
        retry_possible: bool = False,
        http_status: int = 500,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            error_code=error_code,
            retry_possible=retry_possible,
            http_status=http_status,
            details=details
        )


class DOCXExportError(ExportError):
    """Exception for DOCX export failures."""
    
    def __init__(
        self, 
        message: str, 
        error_code: str = "docx_export_error",
        retry_possible: bool = False,
        http_status: int = 500,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            error_code=error_code,
            retry_possible=retry_possible,
            http_status=http_status,
            details=details
        )


def create_error_response(
    error: Exception,
    request_id: Optional[str] = None,
    format_type: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a standardized error response with user-friendly messages.
    
    Args:
        error: The exception that occurred
        request_id: Optional request ID for tracking
        format_type: Optional export format type ('pdf' or 'docx')
        
    Returns:
        Dict containing standardized error response with user-friendly messages
    """
    # Default error response
    error_response = {
        "error": "unknown_error",
        "message": "An unexpected error occurred during export",
        "details": None,
        "retry_possible": False,
        "timestamp": datetime.now().isoformat(),
        "user_message": "We couldn't export your document. Please try again later."
    }
    
    if request_id:
        error_response["request_id"] = request_id
    
    if format_type:
        error_response["format"] = format_type
    
    # Handle our custom export errors
    if isinstance(error, ExportError):
        error_response.update({
            "error": error.error_code,
            "message": error.message,
            "retry_possible": error.retry_possible,
            "details": error.details,
            "http_status": error.http_status
        })
        
        # Add user-friendly messages based on error code
        if error.error_code == "html_validation_failed":
            error_response["user_message"] = "Your document contains formatting that couldn't be processed. Try simplifying complex tables or formatting."
        elif error.error_code == "pdf_validation_failed":
            error_response["user_message"] = "The generated PDF didn't meet quality requirements. Please try again or simplify your document."
        elif error.error_code == "weasyprint_not_installed":
            error_response["user_message"] = "PDF export is temporarily unavailable. Please try again later or contact support."
        elif error.error_code == "font_error":
            error_response["user_message"] = "There was an issue with font rendering. Please try again or use simpler fonts."
        elif error.error_code == "css_error":
            error_response["user_message"] = "There was an issue with document styling. Try simplifying complex formatting."
        elif error.error_code == "memory_error":
            error_response["user_message"] = "Your document is too large to process. Try breaking it into smaller documents."
        elif error.error_code == "storage_error":
            error_response["user_message"] = "We couldn't save your exported document. Please try again later."
        elif error.error_code == "docx_table_error":
            error_response["user_message"] = "There was an issue with table formatting in your document. Try simplifying complex tables."
        elif "timeout" in error.message.lower():
            error_response["user_message"] = "The export process took too long. Try simplifying your document or try again later."
        elif "network" in error.message.lower():
            error_response["user_message"] = "A network issue occurred during export. Please check your connection and try again."
    
    # Handle WeasyPrint specific errors
    elif "weasyprint" in str(error).lower():
        error_response.update({
            "error": "pdf_generation_error",
            "message": str(error),
            "retry_possible": True,
            "user_message": "There was an issue generating your PDF. Please try again or simplify complex formatting."
        })
    
    # Handle docx specific errors
    elif "docx" in str(error).lower():
        error_response.update({
            "error": "docx_generation_error",
            "message": str(error),
            "retry_possible": True,
            "user_message": "There was an issue generating your DOCX file. Please try again or simplify complex formatting."
        })
    
    # Handle storage errors
    elif "storage" in str(error).lower() or "upload" in str(error).lower():
        error_response.update({
            "error": "storage_error",
            "message": str(error),
            "retry_possible": True,
            "user_message": "We couldn't save your exported document. Please try again later."
        })
    
    # Add format-specific context to user message if not already present
    if format_type and format_type.upper() not in error_response["user_message"]:
        error_response["user_message"] = f"{format_type.upper()} export: {error_response['user_message']}"
    
    return error_response


async def retry_async_operation(
    operation: Callable,
    max_retries: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0,
    request_id: Optional[str] = None,
    format_type: Optional[str] = None,
    *args, **kwargs
) -> Any:
    """
    Retry an async operation with exponential backoff.
    
    Args:
        operation: Async function to retry
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay between retries in seconds
        backoff_factor: Factor to increase delay with each retry
        request_id: Optional request ID for logging
        format_type: Optional export format type for logging
        *args, **kwargs: Arguments to pass to the operation
        
    Returns:
        Result of the operation if successful
        
    Raises:
        ExportError: If all retry attempts fail
    """
    retry_count = 0
    last_exception = None
    delay = initial_delay
    
    log_prefix = f"[{request_id}]" if request_id else ""
    format_str = f"({format_type})" if format_type else ""
    
    while retry_count <= max_retries:
        try:
            if retry_count > 0:
                logger.info(f"{log_prefix} Retry attempt {retry_count}/{max_retries} {format_str}")
            
            # Execute the operation
            result = await operation(*args, **kwargs)
            
            # If successful after retries, log it
            if retry_count > 0:
                logger.info(f"{log_prefix} Operation succeeded after {retry_count} retries {format_str}")
            
            return result
            
        except Exception as e:
            last_exception = e
            retry_count += 1
            
            # Check if we should retry based on the exception
            retry_possible = False
            if isinstance(e, ExportError):
                retry_possible = e.retry_possible
            else:
                # Determine if we should retry based on the error message
                error_str = str(e).lower()
                retry_possible = any(
                    term in error_str for term in 
                    ["timeout", "network", "connection", "temporary", "retry", "again"]
                )
            
            if not retry_possible or retry_count > max_retries:
                logger.warning(
                    f"{log_prefix} Operation failed after {retry_count-1} retries, "
                    f"no more retries possible {format_str}: {str(e)}"
                )
                break
            
            # Calculate backoff delay
            delay = initial_delay * (backoff_factor ** (retry_count - 1))
            
            logger.info(
                f"{log_prefix} Operation failed (attempt {retry_count}/{max_retries}), "
                f"retrying in {delay:.2f}s {format_str}: {str(e)}"
            )
            
            # Wait before retrying
            await asyncio.sleep(delay)
    
    # If we get here, all retries failed
    if isinstance(last_exception, ExportError):
        raise last_exception
    
    # Wrap other exceptions in ExportError
    error_code = f"{format_type}_export_failed" if format_type else "export_failed"
    raise ExportError(
        message=f"Operation failed after {max_retries} retry attempts: {str(last_exception)}",
        error_code=error_code,
        retry_possible=False,
        details={"original_error": str(last_exception), "traceback": traceback.format_exc()}
    )


def with_export_error_handling(format_type: str):
    """
    Decorator for export endpoints to standardize error handling.
    
    Args:
        format_type: Export format type ('pdf' or 'docx')
        
    Returns:
        Decorated function with standardized error handling
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            request_id = f"{format_type}_export_{uuid.uuid4().hex[:8]}"
            start_time = time.time()
            
            logger.info(f"[{request_id}] Starting {format_type.upper()} export")
            
            try:
                # Add request_id to kwargs if the function accepts it
                if 'request_id' in func.__code__.co_varnames:
                    kwargs['request_id'] = request_id
                
                # Execute the function
                result = await func(*args, **kwargs)
                
                # Log success
                duration = time.time() - start_time
                logger.info(f"[{request_id}] {format_type.upper()} export completed successfully in {duration:.2f}s")
                
                # Add success metadata to result
                if isinstance(result, dict):
                    result.update({
                        "success": True,
                        "request_id": request_id,
                        "duration_ms": int(duration * 1000),
                        "message": f"{format_type.upper()} export completed successfully"
                    })
                
                return result
                
            except Exception as e:
                # Log the error
                duration = time.time() - start_time
                logger.error(
                    f"[{request_id}] {format_type.upper()} export failed after {duration:.2f}s: {str(e)}\n"
                    f"{traceback.format_exc()}"
                )
                
                # Create standardized error response
                error_response = create_error_response(e, request_id, format_type)
                
                # Determine HTTP status code
                status_code = 500
                if isinstance(e, ExportError):
                    status_code = e.http_status
                
                # Import here to avoid circular imports
                from fastapi import HTTPException
                
                # Raise HTTPException with standardized error response
                raise HTTPException(
                    status_code=status_code,
                    detail=error_response
                )
                
        return wrapper
    return decorator