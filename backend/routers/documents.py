from fastapi import APIRouter, UploadFile, File, HTTPException, Request
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from backend.core.config import settings
import re
from storage3.exceptions import StorageApiError
import uuid
from backend.models.document import Document
from backend.core.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends
from backend.services.auth import get_current_user
from backend.models.user import User
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse
import io
from docx import Document as DocxDocument
from docx.shared import Inches
import html2text
import tempfile
import os
import logging
import time
import random

# Initialize logger for this module
logger = logging.getLogger(__name__)

router = APIRouter()

dummy_documents = [
    {
        "id": "1",
        "name": "Sample.docx",
        "created_at": datetime.utcnow().isoformat(),
        "type": "original",
        "status": "Uploaded",
        "original_file_url": "https://example.com/sample.docx",
        "ai_content": None,
        "final_file_url": None,
        "parsed_structure": "<p>Sample content</p>",
    },
    {
        "id": "2",
        "name": "Generated.pdf",
        "created_at": datetime.utcnow().isoformat(),
        "type": "generated",
        "status": "Generated",
        "original_file_url": None,
        "ai_content": "<p>Generated content</p>",
        "final_file_url": "https://example.com/generated.pdf",
        "parsed_structure": None,
    },
]

class DocumentResponse(BaseModel):
    id: str
    name: str
    created_at: str
    type: str
    status: Optional[str]
    original_file_url: Optional[str]
    ai_content: Optional[str]
    final_file_url: Optional[str]
    parsed_structure: Optional[str]

@router.post("/upload-doc")
async def upload_doc(request: Request, file: UploadFile = File(...), db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required.")
    # File type validation
    allowed_extensions = {"pdf", "docx", "doc"}
    if "." not in file.filename or file.filename.rsplit(".", 1)[1].lower() not in allowed_extensions:
        raise HTTPException(status_code=400, detail="Only .pdf, .docx, and .doc files are allowed.")
    supabase = request.app.state.supabase
    bucket = settings.SUPABASE_BUCKET
    contents = await file.read()
    # Sanitize filename and append uuid
    base, ext = (str(file.filename).rsplit('.', 1) + [""])[:2]
    safe_base = re.sub(r'[^A-Za-z0-9._-]', '_', base)
    unique_filename = f"{safe_base}_{uuid.uuid4().hex}"
    if ext:
        unique_filename += f".{ext}"
    try:
        res = supabase.storage.from_(bucket).upload(unique_filename, contents)
    except StorageApiError as e:
        error_info = e.args[0] if e.args else {}
        message = error_info.get("message") if isinstance(error_info, dict) else str(error_info)
        raise HTTPException(status_code=500, detail=f"Failed to upload file: {message}")
    public_url = supabase.storage.from_(bucket).get_public_url(unique_filename)
    user_id = current_user.id
    doc = Document(
        user_id=user_id,
        name=file.filename,
        stored_filename=unique_filename,
        created_at=datetime.utcnow(),
        type="original",
        status="Uploaded",
        original_file_url=public_url,
        ai_content=None,
        final_file_url=None,
        parsed_structure=None
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)
    return {
        "id": str(doc.id),
        "name": doc.name,
        "created_at": doc.created_at.isoformat(),
        "type": doc.type,
        "status": doc.status,
        "original_file_url": doc.original_file_url,
        "ai_content": doc.ai_content,
        "final_file_url": doc.final_file_url,
        "parsed_structure": doc.parsed_structure,
        "stored_filename": doc.stored_filename
    }

@router.get("/documents", response_model=List[DocumentResponse])
async def list_documents(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    user_id = current_user.id
    result = await db.execute(
        Document.__table__.select().where(Document.user_id == user_id)
    )
    docs = result.fetchall()
    return [
        {
            "id": str(row.id),
            "name": row.name,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "type": row.type,
            "status": row.status,
            "original_file_url": row.original_file_url,
            "ai_content": row.ai_content,
            "final_file_url": row.final_file_url,
            "parsed_structure": row.parsed_structure,
            "stored_filename": row.stored_filename
        }
        for row in docs
    ]

@router.get("/session/{id}")
async def get_document(id: str, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    user_id = current_user.id
    result = await db.execute(
        Document.__table__.select().where(Document.id == id).where(Document.user_id == user_id)
    )
    row = result.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Document not found")
    return {
        "id": str(row.id),
        "name": row.name,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "type": row.type,
        "status": row.status,
        "original_file_url": row.original_file_url,
        "ai_content": row.ai_content,
        "final_file_url": row.final_file_url,
        "parsed_structure": row.parsed_structure,
        "stored_filename": row.stored_filename
    }

class SaveEditsRequest(BaseModel):
    id: str
    content: str

@router.post("/save-edits")
async def save_edits(data: SaveEditsRequest, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    user_id = current_user.id
    result = await db.execute(
        Document.__table__.select().where(Document.id == data.id).where(Document.user_id == user_id)
    )
    row = result.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Document not found")
    await db.execute(
        Document.__table__.update().where(Document.id == data.id).where(Document.user_id == user_id).values(ai_content=data.content)
    )
    await db.commit()
    return {"message": "Edits saved"}

# New endpoint to directly download PDF files
@router.get("/download/pdf/{id}")
async def download_pdf(id: str, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Direct PDF download endpoint that serves the file with proper headers
    to force download instead of viewing in browser
    """
    request_id = f"pdf_download_{id}_{uuid.uuid4().hex[:8]}"
    logger.info(f"[{request_id}] Starting direct PDF download for document {id}")
    
    try:
        # Import PDF generation service
        from backend.services.pdf_generator import (
            generate_pdf_from_html,
            PDFGenerationError
        )
        
        # Fetch document
        user_id = current_user.id
        result = await db.execute(
            Document.__table__.select().where(Document.id == id).where(Document.user_id == user_id)
        )
        row = result.fetchone()
        
        if not row:
            logger.warning(f"[{request_id}] Document not found for user {user_id}, document {id}")
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Get content
        content = row.ai_content
        if not content or not content.strip():
            content = "<p>No content available for this document.</p>"
        
        document_title = row.name or "Document"
        
        # Generate PDF
        logger.debug(f"[{request_id}] Generating PDF for direct download")
        pdf_bytes = await generate_pdf_from_html(content, document_title, document_id=id, user_id=user_id)
        
        # Create a temporary file to serve
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
        temp_file.write(pdf_bytes)
        temp_file.close()
        
        # Sanitize filename for download
        safe_filename = re.sub(r'[^A-Za-z0-9._-]', '_', document_title)
        download_filename = f"{safe_filename}.pdf"
        
        logger.info(f"[{request_id}] Serving PDF file directly: {download_filename}")
        
        # Return file response with headers that force download
        return FileResponse(
            path=temp_file.name,
            filename=download_filename,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{download_filename}"',
                "Content-Type": "application/pdf"
            }
        )
        
    except Exception as e:
        logger.error(f"[{request_id}] Error serving PDF file: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to generate PDF: {str(e)}")

@router.post("/export/pdf/{id}")
async def export_pdf(id: str, request: Request, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Export document as PDF file with comprehensive error handling and validation
    
    Generates a proper PDF file from the document content using HTML-to-PDF conversion.
    Returns a downloadable PDF file URL with detailed error handling.
    Includes rate limiting, performance optimizations, and metrics collection.
    """
    request_id = f"pdf_export_{id}_{uuid.uuid4().hex[:8]}"
    start_time = time.time()
    logger.info(f"[{request_id}] Starting PDF export request for document {id}")
    
    try:
        # Import enhanced PDF generation services and utilities
        from backend.services.pdf_generator import (
            generate_pdf_from_html, 
            generate_unique_filename, 
            PDFGenerationError,
            HTMLValidationError,
            PDFValidationError,
            create_error_response,
            cleanup_temp_files,
            check_system_resources
        )
        from backend.utils.rate_limiter import rate_limiter
        from backend.utils.metrics import pdf_metrics
        
        # Step 0: Apply rate limiting
        user_id = current_user.id
        is_limited, retry_after = rate_limiter.is_rate_limited(user_id, "pdf_export")
        
        if is_limited:
            logger.warning(f"[{request_id}] Rate limit exceeded for user {user_id}")
            pdf_metrics.record_rate_limit_event(user_id)
            
            error_response = {
                "error": "rate_limit_exceeded",
                "message": f"PDF export rate limit exceeded. Please try again later.",
                "details": f"You can try again in {retry_after} seconds.",
                "retry_possible": True,
                "retry_after": retry_after,
                "request_id": request_id
            }
            
            # Return 429 Too Many Requests
            raise HTTPException(status_code=429, detail=error_response)
        
        # Step 1: Fetch and validate document
        user_id = current_user.id
        logger.debug(f"[{request_id}] Fetching document for user {user_id}")
        
        result = await db.execute(
            Document.__table__.select().where(Document.id == id).where(Document.user_id == user_id)
        )
        row = result.fetchone()
        
        if not row:
            logger.warning(f"[{request_id}] Document not found for user {user_id}, document {id}")
            raise HTTPException(
                status_code=404, 
                detail={
                    "error": "document_not_found",
                    "message": "Document not found or you don't have permission to access it",
                    "retry_possible": False
                }
            )
        
        # Step 2: Validate and prepare content
        content = row.ai_content
        if not content or not content.strip():
            logger.info(f"[{request_id}] No content available for document {id}, using default message")
            content = "<p>No content available for this document.</p>"
        
        document_title = row.name or "Document"
        logger.info(f"[{request_id}] Processing document: {document_title} (Content size: {len(content)} chars)")
        
        # Step 2.5: Check system resources before processing
        resources = check_system_resources()
        if resources.get("memory_critical", False):
            logger.warning(f"[{request_id}] Memory usage critical before PDF generation: {resources.get('memory_percent')}%")
        
        # Step 3: Generate PDF with enhanced error handling
        try:
            logger.debug(f"[{request_id}] Starting PDF generation...")
            # Pass document_id and user_id for metrics tracking
            pdf_bytes = await generate_pdf_from_html(
                content, 
                document_title,
                document_id=id,
                user_id=user_id
            )
            logger.info(f"[{request_id}] PDF generation successful - Size: {len(pdf_bytes)} bytes")
            
        except HTMLValidationError as e:
            logger.error(f"[{request_id}] HTML validation failed: {str(e)}")
            error_response = create_error_response(e, request_id)
            raise HTTPException(status_code=400, detail=error_response)
            
        except PDFValidationError as e:
            logger.error(f"[{request_id}] PDF validation failed: {str(e)}")
            error_response = create_error_response(e, request_id)
            raise HTTPException(status_code=422, detail=error_response)
            
        except PDFGenerationError as e:
            logger.error(f"[{request_id}] PDF generation failed: {str(e)}")
            error_response = create_error_response(e, request_id)
            
            # Use appropriate HTTP status code based on error type
            if e.error_code == "pdf_generation_timeout":
                status_code = 408  # Request Timeout
            elif e.error_code in ["network_error", "browser_protocol_error"]:
                status_code = 503  # Service Unavailable
            else:
                status_code = 500  # Internal Server Error
                
            raise HTTPException(status_code=status_code, detail=error_response)
            
        except Exception as e:
            logger.error(f"[{request_id}] Unexpected error during PDF generation: {str(e)}")
            error_response = create_error_response(e, request_id)
            raise HTTPException(status_code=500, detail=error_response)
        
        # Step 4: Generate unique filename and validate
        base_filename = f"{document_title}.pdf"
        unique_filename = generate_unique_filename(base_filename)
        logger.debug(f"[{request_id}] Generated unique filename: {unique_filename}")
        
        # Step 5: Upload PDF to Supabase Storage with error handling
        supabase = request.app.state.supabase
        bucket = settings.SUPABASE_BUCKET
        
        try:
            logger.debug(f"[{request_id}] Uploading PDF to storage...")
            # Set explicit content type for PDF files to ensure proper handling by browsers
            file_options = {
                "contentType": "application/pdf",
                "cacheControl": "3600"
            }
            upload_result = supabase.storage.from_(bucket).upload(
                unique_filename, 
                pdf_bytes, 
                file_options=file_options
            )
            logger.info(f"[{request_id}] PDF uploaded successfully to storage")
            
            # Get public URL for the PDF
            public_url = supabase.storage.from_(bucket).get_public_url(unique_filename)
            logger.debug(f"[{request_id}] Generated public URL: {public_url}")
            
        except StorageApiError as e:
            logger.error(f"[{request_id}] Storage upload failed: {str(e)}")
            error_info = e.args[0] if e.args else {}
            message = error_info.get("message") if isinstance(error_info, dict) else str(error_info)
            
            error_response = {
                "error": "storage_upload_failed",
                "message": f"Failed to save PDF file: {message}",
                "details": "There was an issue with file storage. Please try again.",
                "retry_possible": True,
                "request_id": request_id
            }
            raise HTTPException(status_code=503, detail=error_response)
            
        except Exception as e:
            logger.error(f"[{request_id}] Unexpected storage error: {str(e)}")
            error_response = {
                "error": "storage_error",
                "message": "Failed to save PDF file due to an unexpected storage error",
                "details": "Please try again later or contact support if the problem persists",
                "retry_possible": True,
                "request_id": request_id
            }
            raise HTTPException(status_code=500, detail=error_response)
        
        # Step 6: Update document record with PDF URL
        try:
            logger.debug(f"[{request_id}] Updating document record with PDF URL...")
            await db.execute(
                Document.__table__.update()
                .where(Document.id == id)
                .where(Document.user_id == user_id)
                .values(final_file_url=public_url)
            )
            await db.commit()
            logger.info(f"[{request_id}] Document record updated successfully")
            
        except Exception as e:
            logger.error(f"[{request_id}] Database update failed: {str(e)}")
            # Don't fail the request if DB update fails, PDF was generated successfully
            logger.warning(f"[{request_id}] PDF was generated successfully but database update failed")
        
        # Step 7: Perform cleanup and collect final metrics
        try:
            # Trigger cleanup of temporary files (with low probability to avoid doing it on every request)
            if random.random() < 0.05:  # 5% chance to run cleanup
                logger.debug(f"[{request_id}] Triggering temporary file cleanup")
                cleanup_result = cleanup_temp_files()
                logger.info(f"[{request_id}] Cleanup completed: {cleanup_result} files removed")
            
            # Check system resources after processing
            post_resources = check_system_resources()
            if post_resources.get("memory_critical", False):
                logger.warning(f"[{request_id}] Memory usage still critical after PDF generation: {post_resources.get('memory_percent')}%")
        except Exception as e:
            # Don't fail the request if cleanup fails
            logger.error(f"[{request_id}] Error during cleanup: {str(e)}")
        
        # Step 8: Return success response with comprehensive information
        response_data = {
            "success": True,
            "url": public_url,
            "filename": unique_filename,
            "message": "Document successfully exported as PDF",
            "size": len(pdf_bytes),
            "document_title": document_title,
            "request_id": request_id,
            "generated_at": datetime.utcnow().isoformat(),
            "processing_time_ms": int((time.time() - start_time) * 1000),
            # Add direct download flag to prevent Google Drive viewer
            "direct_download": True,
            # Add direct download URL that bypasses Supabase storage
            "direct_download_url": f"/download/pdf/{id}"
        }
        
        logger.info(f"[{request_id}] PDF export completed successfully in {response_data['processing_time_ms']}ms")
        return response_data
        
    except HTTPException:
        # Re-raise HTTP exceptions (they already have proper status codes and messages)
        raise
    except Exception as e:
        # Catch any other unexpected errors with comprehensive logging
        logger.error(f"[{request_id}] Unexpected error in PDF export: {str(e)}", exc_info=True)
        
        error_response = {
            "error": "unexpected_error",
            "message": "PDF export failed due to an unexpected error",
            "details": "Please try again later or contact support if the problem persists",
            "retry_possible": True,
            "request_id": request_id
        }
        raise HTTPException(status_code=500, detail=error_response)

@router.post("/export/docx/{id}")
async def export_docx(id: str, request: Request, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    try:
        user_id = current_user.id
        result = await db.execute(
            Document.__table__.select().where(Document.id == id).where(Document.user_id == user_id)
        )
        row = result.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Document not found")
        
        content = row.ai_content or "<p>No content available</p>"
        
        # Convert HTML to plain text for DOCX
        h = html2text.HTML2Text()
        h.ignore_links = False
        h.body_width = 0  # Don't wrap lines
        plain_text = h.handle(content)
        
        # Create DOCX document
        docx_buffer = io.BytesIO()
        doc = DocxDocument()
        
        # Add document title
        title = doc.add_heading(row.name or 'Document', 0)
        
        # Add content paragraphs
        if plain_text.strip():
            # Split by double newlines to create paragraphs
            paragraphs = plain_text.split('\n\n')
            for para_text in paragraphs:
                if para_text.strip():
                    doc.add_paragraph(para_text.strip())
        else:
            doc.add_paragraph("No content available")
        
        doc.save(docx_buffer)
        docx_buffer.seek(0)
        
        # Save to Supabase Storage
        supabase = request.app.state.supabase
        bucket = settings.SUPABASE_BUCKET
        filename = f"exported_{id}_{uuid.uuid4().hex}.docx"
        supabase.storage.from_(bucket).upload(filename, docx_buffer.read())
        public_url = supabase.storage.from_(bucket).get_public_url(filename)
        
        # Update DB
        await db.execute(
            Document.__table__.update().where(Document.id == id).where(Document.user_id == user_id).values(final_file_url=public_url)
        )
        await db.commit()
        
        return {"url": public_url}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DOCX export failed: {str(e)}")

@router.post("/export/markdown/{id}")
async def export_markdown(id: str, request: Request, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    user_id = current_user.id
    result = await db.execute(
        Document.__table__.select().where(Document.id == id).where(Document.user_id == user_id)
    )
    row = result.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Document not found")
    content = row.ai_content or ""
    # Save as Markdown file (assume content is already Markdown or plain text)
    md_bytes = content.encode("utf-8")
    supabase = request.app.state.supabase
    bucket = settings.SUPABASE_BUCKET
    filename = f"exported_{id}_{uuid.uuid4().hex}.md"
    supabase.storage.from_(bucket).upload(filename, md_bytes)
    public_url = supabase.storage.from_(bucket).get_public_url(filename)
    # Update DB
    await db.execute(
        Document.__table__.update().where(Document.id == id).where(Document.user_id == user_id).values(final_file_url=public_url)
    )
    await db.commit()
    return {"url": public_url} 