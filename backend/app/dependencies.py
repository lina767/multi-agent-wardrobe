from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import httpx
import jwt
from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session
from jwt import PyJWKClient

from app.db.models import User
from app.config import settings
from app.db.session import get_db

_JWK_CLIENT: PyJWKClient | None = None


def _validate_with_supabase_userinfo(token: str) -> dict[str, Any] | None:
    if not settings.supabase_url:
        return None
    apikey = settings.supabase_anon_key or settings.supabase_service_key
    if not apikey:
        return None
    url = f"{settings.supabase_url.rstrip('/')}/auth/v1/user"
    try:
        response = httpx.get(
            url,
            headers={
                "Authorization": f"Bearer {token}",
                "apikey": apikey,
            },
            timeout=8.0,
        )
    except Exception:
        return None
    if response.status_code >= 400:
        return None
    payload = response.json()
    if not isinstance(payload, dict):
        return None
    # Normalize to JWT-like claims shape expected downstream.
    payload.setdefault("sub", payload.get("id"))
    payload.setdefault("email", payload.get("email"))
    return payload


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
    if settings.supabase_jwt_secret:
        try:
            # Local Supabase tokens are usually HS256.
            return jwt.decode(
                token,
                settings.supabase_jwt_secret,
                algorithms=["HS256"],
                options={"verify_aud": False},
            )
        except jwt.InvalidTokenError as exc:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc

    if settings.supabase_url:
        global _JWK_CLIENT
        if _JWK_CLIENT is None:
            jwks_url = f"{settings.supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json"
            _JWK_CLIENT = PyJWKClient(jwks_url)
        try:
            signing_key = _JWK_CLIENT.get_signing_key_from_jwt(token)
            return jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                options={"verify_aud": False},
            )
        except jwt.InvalidTokenError as exc:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc
        except Exception as exc:
            fallback_claims = _validate_with_supabase_userinfo(token)
            if fallback_claims:
                return fallback_claims
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unable to validate token") from exc

    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Auth not configured: set WARDROBE_SUPABASE_JWT_SECRET or WARDROBE_SUPABASE_URL",
    )


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
