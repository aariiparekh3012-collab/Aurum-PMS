"""Document storage abstraction — local filesystem or S3/MinIO.

Provides a unified interface for storing and retrieving KYC documents.
The backend is selected via the DOCUMENT_STORAGE_BACKEND env var:
  - "local" (default) — stores files under DOCUMENT_STORAGE_PATH
  - "s3"              — stores files in an S3/MinIO bucket

All files are stored with a structured key:
  documents/{application_id}/{document_type}/{uuid}_{original_name}
"""
from __future__ import annotations

import hashlib
import os
import shutil
import uuid
from abc import ABC, abstractmethod
from pathlib import Path

from app.core.config import get_settings


class DocumentStore(ABC):
    """Abstract document storage interface."""

    @abstractmethod
    def save(self, key: str, data: bytes) -> str:
        """Save file data under the given key. Returns the final storage key."""
        ...

    @abstractmethod
    def get(self, key: str) -> bytes:
        """Retrieve file data by key."""
        ...

    @abstractmethod
    def delete(self, key: str) -> None:
        """Delete a file by key."""
        ...

    @abstractmethod
    def get_url(self, key: str, expires_in: int = 3600) -> str:
        """Get a (possibly pre-signed) URL for the file."""
        ...


class LocalDocumentStore(DocumentStore):
    """Store documents on the local filesystem."""

    def __init__(self, base_path: str | None = None):
        self._base = Path(base_path or os.getenv(
            "DOCUMENT_STORAGE_PATH",
            str(Path(__file__).resolve().parents[4] / "document_uploads"),
        ))
        self._base.mkdir(parents=True, exist_ok=True)

    def save(self, key: str, data: bytes) -> str:
        dest = self._base / key
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        return key

    def get(self, key: str) -> bytes:
        path = self._base / key
        if not path.exists():
            raise FileNotFoundError(f"Document not found: {key}")
        return path.read_bytes()

    def delete(self, key: str) -> None:
        path = self._base / key
        if path.exists():
            path.unlink()

    def get_url(self, key: str, expires_in: int = 3600) -> str:
        # For local storage, return a relative API path
        return f"/api/v1/documents/download/{key}"


class S3DocumentStore(DocumentStore):
    """Store documents in S3/MinIO."""

    def __init__(self):
        import boto3
        settings = get_settings()
        self._bucket = os.getenv("DOCUMENT_S3_BUCKET", "pms-documents")

        endpoint_url = os.getenv("DOCUMENT_S3_ENDPOINT")
        kwargs = {}
        if endpoint_url:
            kwargs["endpoint_url"] = endpoint_url

        self._client = boto3.client(
            "s3",
            aws_access_key_id=os.getenv("DOCUMENT_S3_ACCESS_KEY", ""),
            aws_secret_access_key=os.getenv("DOCUMENT_S3_SECRET_KEY", ""),
            region_name=os.getenv("DOCUMENT_S3_REGION", "ap-south-1"),
            **kwargs,
        )

    def save(self, key: str, data: bytes) -> str:
        self._client.put_object(Bucket=self._bucket, Key=key, Body=data)
        return key

    def get(self, key: str) -> bytes:
        resp = self._client.get_object(Bucket=self._bucket, Key=key)
        return resp["Body"].read()

    def delete(self, key: str) -> None:
        self._client.delete_object(Bucket=self._bucket, Key=key)

    def get_url(self, key: str, expires_in: int = 3600) -> str:
        return self._client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self._bucket, "Key": key},
            ExpiresIn=expires_in,
        )


# ── Factory ──────────────────────────────────────────────────────────────────

_store: DocumentStore | None = None


def get_document_store() -> DocumentStore:
    """Get the configured document store (singleton)."""
    global _store
    if _store is None:
        backend = os.getenv("DOCUMENT_STORAGE_BACKEND", "local").lower()
        if backend == "s3":
            _store = S3DocumentStore()
        else:
            _store = LocalDocumentStore()
    return _store


# ── Helpers ──────────────────────────────────────────────────────────────────

ALLOWED_DOCUMENT_TYPES = {
    "pan_card",
    "aadhaar",
    "bank_proof",
    "demat_cmr",
    "pms_agreement",
    "address_proof",
    "photo",
    "other",
}

ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".webp"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


def build_storage_key(
    application_id: uuid.UUID,
    document_type: str,
    original_filename: str,
) -> str:
    """Build a structured storage key."""
    ext = Path(original_filename).suffix.lower() or ".pdf"
    file_id = uuid.uuid4().hex[:12]
    safe_name = Path(original_filename).stem[:50].replace(" ", "_")
    return f"documents/{application_id}/{document_type}/{file_id}_{safe_name}{ext}"


def compute_sha256(data: bytes) -> str:
    """SHA-256 hex digest of file content."""
    return hashlib.sha256(data).hexdigest()
