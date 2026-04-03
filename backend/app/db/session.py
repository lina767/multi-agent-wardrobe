from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings

def _normalize_database_url(raw_url: str) -> str:
    if not raw_url.startswith("sqlite"):
        return raw_url
    prefix = "sqlite:///"
    if not raw_url.startswith(prefix):
        return raw_url
    path_part = raw_url.replace(prefix, "", 1)
    db_path = Path(path_part)
    if not db_path.is_absolute():
        # Resolve relative sqlite paths against backend root to avoid cwd-dependent db splits.
        backend_root = Path(__file__).resolve().parents[2]
        db_path = (backend_root / db_path).resolve()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return f"{prefix}{db_path}"


DATABASE_URL = _normalize_database_url(settings.database_url)

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    from app.db.base import Base  # noqa: PLC0415
    from app.db import models as _legacy_models  # noqa: F401, PLC0415
    from app import models as _new_models  # noqa: F401, PLC0415

    Base.metadata.create_all(bind=engine)
