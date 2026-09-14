from datetime import datetime

from pydantic import BaseModel, Field


class ApiKeyCreateRequest(BaseModel):
    label: str = Field(..., min_length=1, max_length=200)
    quota_limit: int | None = Field(default=None, gt=0, description="Jumlah request maksimum per periode")
    quota_period_seconds: int | None = Field(
        default=None, gt=0, description="Panjang periode kuota dalam detik (mis. 7200 = 2 jam)"
    )


class ApiKeyCreateResponse(BaseModel):
    id: str
    label: str
    api_key: str
    quota_limit: int
    quota_period_seconds: int
    created_at: datetime


class ApiKeyPublic(BaseModel):
    id: str
    label: str
    quota_limit: int
    quota_period_seconds: int
    is_revoked: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class ApiKeyRotateResponse(BaseModel):
    id: str
    label: str
    api_key: str
    quota_limit: int
    quota_period_seconds: int


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
