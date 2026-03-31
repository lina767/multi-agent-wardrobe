from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings

# Ensure SQLite directory exists
if settings.database_url.startswith("sqlite"):
    path_part = settings.database_url.replace("sqlite:///", "", 1)
    db_path = Path(path_part)
    if db_path.parent != Path("."):
        db_path.parent.mkdir(parents=True, exist_ok=True)

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}

engine = create_engine(
    settings.database_url,
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
