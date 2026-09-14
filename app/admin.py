from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import generate_api_key, hash_key, verify_admin_secret
from app.config import settings
from app.models import ApiKey, get_db
from app.schemas import (
    ApiKeyCreateRequest,
    ApiKeyCreateResponse,
    ApiKeyPublic,
    ApiKeyRotateResponse,
)

router = APIRouter(prefix="/admin/keys", tags=["admin"], dependencies=[Depends(verify_admin_secret)])


@router.post("", response_model=ApiKeyCreateResponse, status_code=status.HTTP_201_CREATED)
def create_key(payload: ApiKeyCreateRequest, db: Session = Depends(get_db)):
    plaintext_key = generate_api_key()
    api_key = ApiKey(
        label=payload.label,
        key_hash=hash_key(plaintext_key),
        quota_limit=payload.quota_limit or settings.DEFAULT_QUOTA_LIMIT,
        quota_period_seconds=payload.quota_period_seconds or settings.DEFAULT_QUOTA_PERIOD_SECONDS,
    )
    db.add(api_key)
    db.commit()
    db.refresh(api_key)

    return ApiKeyCreateResponse(
        id=api_key.id,
        label=api_key.label,
        api_key=plaintext_key,
        quota_limit=api_key.quota_limit,
        quota_period_seconds=api_key.quota_period_seconds,
        created_at=api_key.created_at,
    )


@router.get("", response_model=list[ApiKeyPublic])
def list_keys(db: Session = Depends(get_db)):
    return db.query(ApiKey).order_by(ApiKey.created_at.desc()).all()


@router.post("/{key_id}/revoke", response_model=ApiKeyPublic)
def revoke_key(key_id: str, db: Session = Depends(get_db)):
    api_key = db.query(ApiKey).filter(ApiKey.id == key_id).first()
    if api_key is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API key tidak ditemukan")

    api_key.is_revoked = True
    db.commit()
    db.refresh(api_key)
    return api_key


@router.post("/{key_id}/rotate", response_model=ApiKeyRotateResponse)
def rotate_key(key_id: str, db: Session = Depends(get_db)):
    api_key = db.query(ApiKey).filter(ApiKey.id == key_id).first()
    if api_key is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API key tidak ditemukan")

    plaintext_key = generate_api_key()
    api_key.key_hash = hash_key(plaintext_key)
    api_key.is_revoked = False
    db.commit()
    db.refresh(api_key)

    return ApiKeyRotateResponse(
        id=api_key.id,
        label=api_key.label,
        api_key=plaintext_key,
        quota_limit=api_key.quota_limit,
        quota_period_seconds=api_key.quota_period_seconds,
    )
