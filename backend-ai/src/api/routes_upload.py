"""File upload API route for document analysis."""

import hashlib
import logging
import os
from pathlib import Path
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from src.db.database import SessionLocal
from src.db.models import UserUpload

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    user_id: str = Form(...),
    session_id: Optional[str] = Form(None),
):
    """Upload a document for AI analysis.

    Saves the file, creates a DB record, then parses / chunks / embeds
    the document into Qdrant so it can be queried via the doc_insight agent.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    allowed = {".pdf", ".pptx", ".ppt", ".txt", ".csv", ".xlsx"}
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {ext}. Allowed: {', '.join(allowed)}",
        )

    content = await file.read()
    if len(content) > 50 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large (max 50MB)")

    doc_hash = hashlib.sha256(content).hexdigest()
    safe_name = f"{doc_hash[:16]}_{file.filename}"
    file_path = UPLOAD_DIR / safe_name

    with open(file_path, "wb") as f:
        f.write(content)

    db = SessionLocal()
    try:
        upload = UserUpload(
            user_id=UUID(user_id),
            session_id=UUID(session_id) if session_id else None,
            filename=file.filename,
            file_type=ext.lstrip("."),
            file_size_bytes=len(content),
            raw_uri=str(file_path),
            document_hash=doc_hash,
            status="uploaded",
        )
        db.add(upload)
        db.commit()
        db.refresh(upload)

        upload_id_str = str(upload.id)
        file_type = ext.lstrip(".")

        # Parse, chunk, embed, and index into Qdrant
        try:
            from src.services.document_processor import DocumentProcessor

            processor = DocumentProcessor()
            chunk_count = processor.process(
                file_path=str(file_path),
                user_id=user_id,
                upload_id=upload_id_str,
                file_type=file_type,
            )
            upload.status = "indexed"
            db.commit()
            logger.info("Indexed %d chunks for upload %s", chunk_count, upload_id_str)
        except Exception as proc_err:
            logger.warning("Document processing failed (upload saved): %s", proc_err)
            upload.status = "uploaded"
            db.commit()

        return {
            "upload_id": upload_id_str,
            "filename": file.filename,
            "status": upload.status,
            "file_size": len(content),
            "hash": doc_hash[:16],
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()
