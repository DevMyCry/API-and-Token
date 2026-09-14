from datetime import datetime

from pydantic import BaseModel, Field


class ApiKeyCreateRequest(BaseModel):
    label: str = Field(..., min_length=1, max_length=200)
    daily_quota: int | None = Field(default=None, gt=0)


class ApiKeyCreateResponse(BaseModel):
    id: str
    label: str
    api_key: str
    daily_quota: int
    created_at: datetime


class ApiKeyPublic(BaseModel):
    id: str
    label: str
    daily_quota: int
    is_revoked: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class ApiKeyRotateResponse(BaseModel):
    id: str
    label: str
    api_key: str
    daily_quota: int


class TokenRequest(BaseModel):
    api_key: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class PredictRequest(BaseModel):
    input: str


class PredictResponse(BaseModel):
    result: str
