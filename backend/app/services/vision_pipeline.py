from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass

from app.config import settings
from app.db import session as db_session
from app.db.models import WardrobeItem
from app.services.hf_vision_service import HuggingFaceVisionService
from app.storage import upload_image

logger = logging.getLogger(__name__)


@dataclass
class VisionJob:
    item_id: int
    image_bytes: bytes
    extension: str


class VisionPipeline:
    def __init__(self) -> None:
        self._queue: asyncio.Queue[VisionJob] = asyncio.Queue()
        self._worker_task: asyncio.Task[None] | None = None
        self._stopping = asyncio.Event()
        self._service = HuggingFaceVisionService()

    async def start(self) -> None:
        if not settings.vision_enabled or self._worker_task:
            return
        self._stopping.clear()
        self._worker_task = asyncio.create_task(self._worker_loop())

    async def stop(self) -> None:
        if not self._worker_task:
            return
        self._stopping.set()
        await self._queue.put(VisionJob(item_id=-1, image_bytes=b"", extension="png"))
        await self._worker_task
        self._worker_task = None

    async def enqueue(self, item_id: int, image_bytes: bytes, extension: str) -> None:
        if not settings.vision_enabled:
            return
        await self._queue.put(VisionJob(item_id=item_id, image_bytes=image_bytes, extension=extension))

    async def _worker_loop(self) -> None:
        while True:
            job = await self._queue.get()
            if self._stopping.is_set() and job.item_id == -1:
                self._queue.task_done()
                return
            try:
                await self._process_job(job)
            except Exception as exc:
                logger.exception("vision_job_unhandled", extra={"item_id": job.item_id, "error": str(exc)})
            finally:
                self._queue.task_done()

    async def _process_job(self, job: VisionJob) -> None:
        db = db_session.SessionLocal()
        row = db.query(WardrobeItem).filter(WardrobeItem.id == job.item_id).first()
        if not row:
            db.close()
            return
        row.vision_status = "processing"
        row.vision_error = None
        db.commit()
        try:
            tags = await self._service.predict_tags(job.image_bytes)
            segmented = await self._service.remove_background(job.image_bytes)
            processed_ref = upload_image(job.item_id, segmented, job.extension, folder="processed")

            row = db.query(WardrobeItem).filter(WardrobeItem.id == job.item_id).first()
            if not row:
                return
            if tags.category:
                row.category = tags.category
            if tags.color_families:
                row.color_families_json = tags.color_families
            if tags.style_tags:
                row.style_tags_json = tags.style_tags
            if tags.material:
                row.material = tags.material
            row.processed_image_path = processed_ref
            row.vision_status = "done"
            row.vision_error = None
            db.commit()
        except Exception as exc:
            row = db.query(WardrobeItem).filter(WardrobeItem.id == job.item_id).first()
            if row:
                row.vision_status = "failed"
                row.vision_error = str(exc)[:255]
                db.commit()
            logger.warning("vision_job_failed", extra={"item_id": job.item_id, "error": str(exc)})
        finally:
            db.close()


vision_pipeline = VisionPipeline()
