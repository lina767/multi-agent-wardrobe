from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import jwt
from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.db.models import User
from app.config import settings
from app.db.session import get_db


def _extract_bearer_token(authorization: str | None) -> str:
    if not authorization:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing Authorization header")
    prefix = "bearer "
    if not authorization.lower().startswith(prefix):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Authorization scheme")
    token = authorization[len(prefix) :].strip()
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")
    return token


def _decode_supabase_jwt(token: str) -> dict[str, Any]:
    if not settings.supabase_jwt_secret:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Auth not configured")
    try:
        # Supabase access tokens are HS256 by default for local projects.
        payload = jwt.decode(
            token,
            settings.supabase_jwt_secret,
            algorithms=["HS256"],
            options={"verify_aud": False},
        )
    except jwt.InvalidTokenError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc
    return payload


def _upsert_user_from_claims(db: Session, claims: dict[str, Any]) -> User:
    sub = str(claims.get("sub") or "").strip()
    email = str(claims.get("email") or "").strip().lower()
    if not sub:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token missing subject")

    user = db.query(User).filter(User.supabase_user_id == sub).first()
    if not user and email:
        user = db.query(User).filter(User.email == email).first()
    if user:
        user.supabase_user_id = sub
        if email:
            user.email = email
        user.last_login_at = datetime.now(UTC)
        user.is_active = True
        db.commit()
        db.refresh(user)
        return user

    username_seed = f"sb_{sub.replace('-', '')[:24] or 'user'}"
    candidate = username_seed
    suffix = 1
    while db.query(User).filter(User.username == candidate).first():
        suffix += 1
        candidate = f"{username_seed}_{suffix}"
    user = User(
        username=candidate,
        display_name=email.split("@")[0] if email and "@" in email else "Wardrobe User",
        preferences_json={},
        supabase_user_id=sub,
        email=email or None,
        is_active=True,
        last_login_at=datetime.now(UTC),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_current_user_id(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> int:
    token = _extract_bearer_token(authorization)
    claims = _decode_supabase_jwt(token)
    user = _upsert_user_from_claims(db, claims)
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is inactive")
    return user.id


def get_current_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> User:
    token = _extract_bearer_token(authorization)
    claims = _decode_supabase_jwt(token)
    user = _upsert_user_from_claims(db, claims)
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is inactive")
    return user
