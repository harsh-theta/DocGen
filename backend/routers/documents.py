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