import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import embeddings, feedback, health, recommendations, wardrobe
from app.bootstrap import ensure_default_user
from app.config import settings
from app.db.session import init_db
from app.db.migrate import ensure_agent_schema, ensure_inventory_schema, ensure_temporal_schema, ensure_user_schema
from app.logging_config import configure_logging
from app.routers import analytics, auth, profile, suggestions
from app.services.vision_pipeline import vision_pipeline

configure_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    # Resolve SessionLocal via package at runtime so tests can rebind in-memory engine.
    from app.db import session as db_session

    db = db_session.SessionLocal()
    try:
        ensure_inventory_schema(db)
        ensure_user_schema(db)
        ensure_agent_schema(db)
        ensure_temporal_schema(db)
        ensure_default_user(db)
        if settings.vision_enabled:
            await vision_pipeline.start()
        logger.info("application_startup", extra={"event": "startup", "user": "default_user"})
    finally:
        db.close()
    yield
    await vision_pipeline.stop()
    logger.info("application_shutdown", extra={"event": "shutdown"})


app = FastAPI(title="Fashion Multi-Agent API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API_PREFIX = "/api/v1"
LEGACY_PREFIX = "/v1"

app.include_router(health.router, prefix=API_PREFIX)
app.include_router(wardrobe.router, prefix=API_PREFIX)
app.include_router(recommendations.router, prefix=API_PREFIX)
app.include_router(feedback.router, prefix=API_PREFIX)
app.include_router(embeddings.router, prefix=API_PREFIX)
app.include_router(profile.router, prefix=API_PREFIX)
app.include_router(suggestions.router, prefix=API_PREFIX)
app.include_router(analytics.router, prefix=API_PREFIX)
app.include_router(auth.router, prefix=API_PREFIX)

# Keep legacy paths available but hidden from OpenAPI.
app.include_router(health.router, prefix=LEGACY_PREFIX, include_in_schema=False)
app.include_router(wardrobe.router, prefix=LEGACY_PREFIX, include_in_schema=False)
app.include_router(recommendations.router, prefix=LEGACY_PREFIX, include_in_schema=False)
app.include_router(feedback.router, prefix=LEGACY_PREFIX, include_in_schema=False)
app.include_router(embeddings.router, prefix=LEGACY_PREFIX, include_in_schema=False)
app.include_router(profile.router, prefix=LEGACY_PREFIX, include_in_schema=False)
app.include_router(suggestions.router, prefix=LEGACY_PREFIX, include_in_schema=False)
app.include_router(analytics.router, prefix=LEGACY_PREFIX, include_in_schema=False)
app.include_router(auth.router, prefix=LEGACY_PREFIX, include_in_schema=False)

APP_DIR = Path(__file__).resolve().parent
BASE_DIR = APP_DIR.parent
ROOT_DIR = BASE_DIR.parent
FRONTEND_DIR = ROOT_DIR / "frontend"
if not FRONTEND_DIR.exists():
    FRONTEND_DIR = APP_DIR / "frontend"
FRONTEND_DIST_DIR = FRONTEND_DIR / "dist"
MEDIA_DIR = BASE_DIR / "data"
FRONTEND_DIR.mkdir(parents=True, exist_ok=True)
MEDIA_DIR.mkdir(parents=True, exist_ok=True)

app.mount("/media", StaticFiles(directory=str(MEDIA_DIR)), name="media")
app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIST_DIR / "assets"), check_dir=False), name="frontend-assets")


@app.get("/", include_in_schema=False)
def frontend_index():
    index = FRONTEND_DIST_DIR / "index.html"
    if index.exists():
        return FileResponse(index)

    return {"message": "Frontend build not found. Run frontend build or use Vite dev server."}


@app.get("/{full_path:path}", include_in_schema=False)
def frontend_spa_fallback(full_path: str, request: Request):
    if full_path.startswith(("api/", "v1/", "docs", "openapi.json", "media/", "assets/")):
        raise HTTPException(status_code=404, detail="Not Found")
    index = FRONTEND_DIST_DIR / "index.html"
    if index.exists():
        return FileResponse(index)
    return {"message": "Frontend build not found. Run frontend build or use Vite dev server."}
