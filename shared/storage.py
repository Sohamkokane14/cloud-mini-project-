"""Image storage abstraction for local mock files and Azure Blob Storage."""

from __future__ import annotations

import os
from pathlib import Path
from uuid import uuid4

from shared.config import APP_MODE, get_secret


CONTAINER_NAME = "item-images"


def _uploads_path() -> Path:
    """Return the local upload directory used only in mock mode."""
    return Path(__file__).resolve().parents[1] / "local_uploads"


def _safe_extension(filename: str) -> str:
    """Keep only a simple image-file extension, defaulting to .jpg."""
    suffix = Path(filename or "").suffix.lower()
    return suffix if suffix in {".jpg", ".jpeg", ".png"} else ".jpg"


def _container_client():
    """Create an Azure Blob container client lazily for non-mock modes."""
    try:
        from azure.storage.blob import BlobServiceClient
    except ImportError as error:
        raise RuntimeError("azure-storage-blob is not installed") from error
    return BlobServiceClient.from_connection_string(
        get_secret("StorageConnectionString")
    ).get_container_client(CONTAINER_NAME)


def upload_image(file_storage) -> str:
    """Save an uploaded JPG/PNG and return its public URL/path."""
    if file_storage is None or not getattr(file_storage, "filename", ""):
        return ""
    blob_name = f"{uuid4().hex}{_safe_extension(file_storage.filename)}"
    if APP_MODE == "mock":
        directory = _uploads_path()
        directory.mkdir(parents=True, exist_ok=True)
        file_storage.save(directory / blob_name)
        return f"/local_uploads/{blob_name}"
    client = _container_client().get_blob_client(blob_name)
    client.upload_blob(file_storage.stream, overwrite=False)
    return client.url


def delete_image(url: str) -> None:
    """Delete an image when it belongs to the configured storage backend."""
    if not url:
        return
    if APP_MODE == "mock":
        prefix = "/local_uploads/"
        if url.startswith(prefix):
            target = _uploads_path() / Path(url).name
            if target.exists():
                target.unlink()
        return
    _container_client().delete_blob(url.rsplit("/", 1)[-1])
