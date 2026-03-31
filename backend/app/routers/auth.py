from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.schemas import EmailUpdate
from app.db.models import User
from app.db.session import get_db
from app.dependencies import get_current_user

router = APIRouter(tags=["auth"])


@router.get("/auth/me")
def auth_me(
    user: User = Depends(get_current_user),
) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "display_name": user.display_name,
        "supabase_user_id": user.supabase_user_id,
        "is_active": user.is_active,
    }


@router.post("/auth/logout")
def auth_logout() -> dict:
    # JWT sessions are managed by Supabase client-side. Endpoint exists for symmetric frontend flow.
    return {"status": "ok"}


@router.patch("/settings/email")
def update_email(
    body: EmailUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    normalized = body.email.strip().lower()
    if "@" not in normalized:
        raise HTTPException(status_code=400, detail="Invalid email")
    user.email = normalized
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Email is already in use") from exc
    db.refresh(user)
    return {
        "id": user.id,
        "email": user.email,
    }
