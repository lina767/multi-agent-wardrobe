from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import httpx

from app.config import settings

UPLOAD_DIR = Path(__file__).resolve().parents[1] / "data" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def upload_image(item_id: int, payload: bytes, extension: str, folder: str = "uploads") -> str:
    ext = extension.lower().lstrip(".")
    if settings.storage_backend == "supabase":
        return _upload_supabase(item_id, payload, ext, folder=folder)
    return _upload_local(item_id, payload, ext, folder=folder)


def delete_image(reference: str) -> None:
    if reference.startswith("supabase:"):
        _delete_supabase(reference.removeprefix("supabase:"))
        return
    _delete_local(reference)


def resolve_image_url(reference: str | None) -> str | None:
    if not reference:
        return None
    if reference.startswith("supabase:"):
        key = reference.removeprefix("supabase:")
        base = (settings.supabase_url or "").rstrip("/")
        if not base:
            return None
        return f"{base}/storage/v1/object/public/{settings.supabase_bucket}/{key}"
    return f"/media/{reference}"


def _upload_local(item_id: int, payload: bytes, ext: str, folder: str) -> str:
    filename = f"{item_id}_{uuid4().hex}.{ext}"
    out_dir = Path(__file__).resolve().parents[1] / "data" / folder
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / filename
    out_path.write_bytes(payload)
    return str(Path(folder) / filename)


def _delete_local(relative_path: str) -> None:
    try:
        path = (Path(__file__).resolve().parents[1] / "data" / relative_path).resolve()
        if path.exists():
            path.unlink()
    except OSError:
        pass


def _upload_supabase(item_id: int, payload: bytes, ext: str, folder: str) -> str:
    if not settings.supabase_url or not settings.supabase_service_key:
        raise RuntimeError("Supabase is selected but credentials are missing.")
    key = f"{folder}/items/{item_id}/{uuid4().hex}.{ext}"
    base = settings.supabase_url.rstrip("/")
    url = f"{base}/storage/v1/object/{settings.supabase_bucket}/{key}"
    headers = {
        "apikey": settings.supabase_service_key,
        "Authorization": f"Bearer {settings.supabase_service_key}",
        "Content-Type": "application/octet-stream",
        "x-upsert": "true",
    }
    resp = httpx.post(url, headers=headers, content=payload, timeout=20.0)
    if resp.status_code == 404 and "Bucket not found" in resp.text:
        _ensure_supabase_bucket()
        resp = httpx.post(url, headers=headers, content=payload, timeout=20.0)
    if resp.status_code >= 300:
        raise RuntimeError(f"Supabase upload failed ({resp.status_code}): {resp.text}")
    return f"supabase:{key}"


def _delete_supabase(key: str) -> None:
    if not settings.supabase_url or not settings.supabase_service_key:
        return
    base = settings.supabase_url.rstrip("/")
    url = f"{base}/storage/v1/object/{settings.supabase_bucket}/{key}"
    headers = {
        "apikey": settings.supabase_service_key,
        "Authorization": f"Bearer {settings.supabase_service_key}",
    }
    try:
        httpx.delete(url, headers=headers, timeout=10.0)
    except httpx.HTTPError:
        pass


def _ensure_supabase_bucket() -> None:
    if not settings.supabase_url or not settings.supabase_service_key:
        return
    base = settings.supabase_url.rstrip("/")
    headers = {
        "apikey": settings.supabase_service_key,
        "Authorization": f"Bearer {settings.supabase_service_key}",
        "Content-Type": "application/json",
    }
    # Idempotent best-effort create. If it already exists, Supabase returns 409.
    payload = {
        "id": settings.supabase_bucket,
        "name": settings.supabase_bucket,
        "public": True,
    }
    try:
        httpx.post(f"{base}/storage/v1/bucket", headers=headers, json=payload, timeout=10.0)
    except httpx.HTTPError:
        # Preserve original upload error path if bucket creation call fails.
        return
