import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import feedback, health, recommendations, wardrobe
from app.bootstrap import ensure_default_user
from app.config import settings
from app.db.session import init_db
from app.db.migrate import ensure_agent_schema, ensure_inventory_schema
from app.logging_config import configure_logging
from app.routers import analytics, profile, suggestions

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
        ensure_agent_schema(db)
        ensure_default_user(db)
        logger.info("application_startup", extra={"event": "startup", "user": "default_user"})
    finally:
        db.close()
    yield
    logger.info("application_shutdown", extra={"event": "shutdown"})


app = FastAPI(title="Fashion Multi-Agent API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/v1")
app.include_router(wardrobe.router, prefix="/v1")
app.include_router(recommendations.router, prefix="/v1")
app.include_router(feedback.router, prefix="/v1")
app.include_router(profile.router, prefix="/api/v1")
app.include_router(suggestions.router, prefix="/api/v1")
app.include_router(analytics.router, prefix="/api/v1")

APP_DIR = Path(__file__).resolve().parent
BASE_DIR = APP_DIR.parent
FRONTEND_DIR = APP_DIR / "frontend"
MEDIA_DIR = BASE_DIR / "data"
FRONTEND_DIR.mkdir(parents=True, exist_ok=True)
MEDIA_DIR.mkdir(parents=True, exist_ok=True)

app.mount("/media", StaticFiles(directory=str(MEDIA_DIR)), name="media")


@app.get("/", include_in_schema=False)
def frontend_index():
    index = FRONTEND_DIR / "index.html"
    if index.exists():
        return FileResponse(index)
    return {"message": "Frontend not found. Open /docs for API."}
