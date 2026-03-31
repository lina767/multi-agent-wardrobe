import pytest
import jwt
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.bootstrap import ensure_default_user
from app.config import settings
from app.db import session as session_module
from app.db.base import Base
from app.db.session import get_db


@pytest.fixture(autouse=True)
def fresh_db() -> None:
    """In-memory SQLite per test; single connection pool so all sessions see the same DB."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    session_module.engine = engine
    session_module.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db = session_module.SessionLocal()
    ensure_default_user(db)
    db.close()
    settings.supabase_jwt_secret = "test-supabase-secret-at-least-32-bytes"
    yield
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture
def client(fresh_db) -> TestClient:
    from app.main import app

    def override_get_db():
        db = session_module.SessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        token = jwt.encode(
            {"sub": "test-user-1", "email": "test-user@example.com", "role": "authenticated"},
            settings.supabase_jwt_secret,
            algorithm="HS256",
        )
        c.headers.update({"Authorization": f"Bearer {token}"})
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def unauth_client(fresh_db) -> TestClient:
    from app.main import app

    def override_get_db():
        db = session_module.SessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
