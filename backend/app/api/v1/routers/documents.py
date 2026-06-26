"""Document upload/download endpoints for KYC onboarding."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.v1.dependencies import get_current_user
from app.core.database import get_db
from app.infrastructure.db.models_onboarding import (
    OnboardingApplicationModel,
    OnboardingDocumentModel,
)
from app.infrastructure.external.document_storage import (
    ALLOWED_DOCUMENT_TYPES,
    ALLOWED_EXTENSIONS,
    MAX_FILE_SIZE,
    build_storage_key,
    compute_sha256,
    get_document_store,
)

router = APIRouter(prefix="/documents", tags=["documents"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class DocumentOut(BaseModel):
    id: uuid.UUID
    application_id: uuid.UUID
    document_type: str
    storage_key: str
    sha256: str
    uploaded_at: datetime
    download_url: str | None = None

    class Config:
        from_attributes = True


class DocumentListOut(BaseModel):
    application_id: uuid.UUID
    documents: list[DocumentOut]


# ── Upload ────────────────────────────────────────────────────────────────────

@router.post(
    "/applications/{application_id}/upload",
    response_model=DocumentOut,
    status_code=201,
)
async def upload_document(
    application_id: uuid.UUID,
    document_type: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Upload a KYC document for an onboarding application.

    Supported document_type values: pan_card, aadhaar, bank_proof,
    demat_cmr, pms_agreement, address_proof, photo, other.
    """
    # Validate document type
    if document_type not in ALLOWED_DOCUMENT_TYPES:
        raise HTTPException(
            422,
            f"Invalid document_type. Allowed: {', '.join(sorted(ALLOWED_DOCUMENT_TYPES))}",
        )

    # Validate file extension
    ext = "." + (file.filename or "file.pdf").rsplit(".", 1)[-1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            422,
            f"File type '{ext}' not allowed. Accepted: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )

    # Verify application exists
    app = db.get(OnboardingApplicationModel, application_id)
    if app is None:
        raise HTTPException(404, "Onboarding application not found")

    # Read file content
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(413, f"File too large. Maximum size: {MAX_FILE_SIZE // (1024*1024)} MB")
    if len(content) == 0:
        raise HTTPException(422, "Empty file")

    # Store the file
    store = get_document_store()
    storage_key = build_storage_key(application_id, document_type, file.filename or "document")
    sha256 = compute_sha256(content)

    store.save(storage_key, content)

    # Check for existing document of the same type (replace it)
    existing = db.scalar(
        select(OnboardingDocumentModel).where(
            OnboardingDocumentModel.application_id == application_id,
            OnboardingDocumentModel.document_type == document_type,
        )
    )
    if existing:
        # Delete old file from storage
        try:
            store.delete(existing.storage_key)
        except Exception:
            pass  # best effort
        existing.storage_key = storage_key
        existing.sha256 = sha256
        existing.uploaded_at = datetime.now(timezone.utc)
        doc = existing
    else:
        doc = OnboardingDocumentModel(
            id=uuid.uuid4(),
            application_id=application_id,
            document_type=document_type,
            storage_key=storage_key,
            sha256=sha256,
            uploaded_at=datetime.now(timezone.utc),
        )
        db.add(doc)

    db.flush()

    return DocumentOut(
        id=doc.id,
        application_id=doc.application_id,
        document_type=doc.document_type,
        storage_key=doc.storage_key,
        sha256=doc.sha256,
        uploaded_at=doc.uploaded_at,
        download_url=store.get_url(doc.storage_key),
    )


# ── List ──────────────────────────────────────────────────────────────────────

@router.get(
    "/applications/{application_id}",
    response_model=DocumentListOut,
)
def list_documents(
    application_id: uuid.UUID,
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """List all documents uploaded for an onboarding application."""
    app = db.get(OnboardingApplicationModel, application_id)
    if app is None:
        raise HTTPException(404, "Onboarding application not found")

    docs = db.scalars(
        select(OnboardingDocumentModel)
        .where(OnboardingDocumentModel.application_id == application_id)
        .order_by(OnboardingDocumentModel.uploaded_at)
    ).all()

    store = get_document_store()
    return DocumentListOut(
        application_id=application_id,
        documents=[
            DocumentOut(
                id=d.id,
                application_id=d.application_id,
                document_type=d.document_type,
                storage_key=d.storage_key,
                sha256=d.sha256,
                uploaded_at=d.uploaded_at,
                download_url=store.get_url(d.storage_key),
            )
            for d in docs
        ],
    )


# ── Download ──────────────────────────────────────────────────────────────────

@router.get("/download/{key:path}")
def download_document(
    key: str,
    _user: dict = Depends(get_current_user),
):
    """Download a document by its storage key (local storage only)."""
    from fastapi.responses import Response

    store = get_document_store()
    try:
        data = store.get(key)
    except FileNotFoundError:
        raise HTTPException(404, "Document not found")

    # Determine content type from extension
    ext = key.rsplit(".", 1)[-1].lower()
    content_types = {
        "pdf": "application/pdf",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "png": "image/png",
        "webp": "image/webp",
    }
    content_type = content_types.get(ext, "application/octet-stream")
    filename = key.rsplit("/", 1)[-1]

    return Response(
        content=data,
        media_type=content_type,
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )


# ── Delete ────────────────────────────────────────────────────────────────────

@router.delete("/documents/{document_id}", status_code=204)
def delete_document(
    document_id: uuid.UUID,
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Delete a specific document."""
    doc = db.get(OnboardingDocumentModel, document_id)
    if doc is None:
        raise HTTPException(404, "Document not found")

    store = get_document_store()
    try:
        store.delete(doc.storage_key)
    except Exception:
        pass  # best effort

    db.delete(doc)
    db.flush()
