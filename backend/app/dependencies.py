from fastapi import Depends
from sqlalchemy.orm import Session

from app.bootstrap import get_default_user_id
from app.db.session import get_db


def get_single_user_id(db: Session = Depends(get_db)) -> int:
    """Single-tenant local deployment: always the default user row."""
    return get_default_user_id(db)
