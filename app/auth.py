import hashlib
import hmac
import secrets
from datetime import date, datetime, timedelta, timezone

import jwt
from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.config import settings
from app.models import ApiKey, UsageCounter, get_db


def generate_api_key() -> str:
    return secrets.token_urlsafe(32)


def hash_key(plaintext_key: str) -> str:
    return hashlib.sha256(plaintext_key.encode("utf-8")).hexdigest()


def verify_admin_secret(x_admin_secret: str = Header(...)) -> None:
    if not hmac.compare_digest(x_admin_secret, settings.ADMIN_SECRET):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Admin secret salah")


def authenticate_api_key(plaintext_key: str, db: Session) -> ApiKey:
    key_hash = hash_key(plaintext_key)
    api_key = db.query(ApiKey).filter(ApiKey.key_hash == key_hash).first()
    if api_key is None or api_key.is_revoked:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="API key tidak valid atau sudah dicabut")
    return api_key


def check_and_increment_quota(api_key: ApiKey, db: Session) -> None:
    today = date.today()
    counter = (
        db.query(UsageCounter)
        .filter(UsageCounter.api_key_id == api_key.id, UsageCounter.usage_date == today)
        .first()
    )
    if counter is None:
        counter = UsageCounter(api_key_id=api_key.id, usage_date=today, count=0)
        db.add(counter)
        db.flush()

    if counter.count >= api_key.daily_quota:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Kuota harian ({api_key.daily_quota} request) untuk API key ini sudah habis. Coba lagi besok.",
        )

    counter.count += 1
    db.commit()


def create_access_token(api_key: ApiKey) -> tuple[str, int]:
    now = datetime.now(timezone.utc)
    expires_in = settings.JWT_EXPIRY_SECONDS
    payload = {
        "sub": api_key.id,
        "label": api_key.label,
        "scope": "predict",
        "iat": now,
        "exp": now + timedelta(seconds=expires_in),
    }
    token = jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    return token, expires_in


def decode_access_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token sudah kedaluwarsa")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token tidak valid")


def get_current_api_key(
    authorization: str = Header(...),
    db: Session = Depends(get_db),
) -> ApiKey:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Header Authorization harus berupa Bearer token")

    token = authorization.removeprefix("Bearer ").strip()
    payload = decode_access_token(token)

    api_key = db.query(ApiKey).filter(ApiKey.id == payload.get("sub")).first()
    if api_key is None or api_key.is_revoked:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="API key untuk token ini tidak valid atau sudah dicabut")

    check_and_increment_quota(api_key, db)
    return api_key
