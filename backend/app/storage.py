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
    ensured, ensure_detail = _ensure_supabase_bucket()
    if not ensured:
        raise RuntimeError(
            "Supabase bucket bootstrap failed "
            f"(bucket='{settings.supabase_bucket}', base='{base}'): {ensure_detail}"
        )
    resp = httpx.post(url, headers=headers, content=payload, timeout=20.0)
    if resp.status_code == 404 and "Bucket not found" in resp.text:
        created, create_detail = _ensure_supabase_bucket()
        if not created:
            raise RuntimeError(
                "Supabase bucket bootstrap failed "
                f"(bucket='{settings.supabase_bucket}', base='{base}'): {create_detail}"
            )
        resp = httpx.post(url, headers=headers, content=payload, timeout=20.0)
    if resp.status_code >= 300:
        raise RuntimeError(
            f"Supabase upload failed ({resp.status_code}) "
            f"(bucket='{settings.supabase_bucket}', base='{base}'): {resp.text}"
        )
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


def _ensure_supabase_bucket() -> tuple[bool, str]:
    if not settings.supabase_url or not settings.supabase_service_key:
        return False, "missing supabase_url or supabase_service_key"
    base = settings.supabase_url.rstrip("/")
    headers = {
        "apikey": settings.supabase_service_key,
        "Authorization": f"Bearer {settings.supabase_service_key}",
        "Content-Type": "application/json",
    }
    bucket = settings.supabase_bucket
    try:
        existing = httpx.get(f"{base}/storage/v1/bucket/{bucket}", headers=headers, timeout=10.0)
    except httpx.HTTPError:
        return False, "network error while checking bucket"

    if existing.status_code == 200:
        try:
            body = existing.json()
        except ValueError:
            body = {}
        is_public = bool((body or {}).get("public"))
        if is_public:
            return True, "ok"
        payload = {"id": bucket, "name": bucket, "public": True}
        try:
            update = httpx.put(f"{base}/storage/v1/bucket/{bucket}", headers=headers, json=payload, timeout=10.0)
        except httpx.HTTPError:
            return False, "network error while updating bucket visibility"
        if update.status_code in {200, 204}:
            return True, "ok"
        return False, f"set bucket public failed ({update.status_code}): {update.text}"

    if existing.status_code not in {400, 404}:
        return False, f"check bucket failed ({existing.status_code}): {existing.text}"

    create_payload = {
        "id": bucket,
        "name": bucket,
        "public": True,
    }
    try:
        created = httpx.post(f"{base}/storage/v1/bucket", headers=headers, json=create_payload, timeout=10.0)
    except httpx.HTTPError:
        return False, "network error while creating bucket"
    if created.status_code in {200, 201, 409}:
        return True, "ok"
    return False, f"create bucket failed ({created.status_code}): {created.text}"
