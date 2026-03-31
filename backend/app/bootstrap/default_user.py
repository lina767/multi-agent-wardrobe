"""Ensure single local user exists (no auth)."""

from sqlalchemy.orm import Session

from app.db.models import User

DEFAULT_USERNAME = "default_user"


def ensure_default_user(db: Session) -> User:
    user = db.query(User).filter(User.username == DEFAULT_USERNAME).first()
    if user:
        return user
    user = User(username=DEFAULT_USERNAME, display_name="Local User", preferences_json={})
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_default_user_id(db: Session) -> int:
    return ensure_default_user(db).id
