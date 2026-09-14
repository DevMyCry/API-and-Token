from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from sqlalchemy.orm import Session

from app.admin import router as admin_router
from app.auth import (
    authenticate_api_key,
    check_and_increment_quota,
    create_access_token,
    get_current_api_key,
)
from app.models import ApiKey, get_db, init_db
from app.schemas import PredictRequest, PredictResponse, TokenRequest, TokenResponse


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="API & Token Provider", version="1.0.0", lifespan=lifespan)
app.include_router(admin_router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/auth/token", response_model=TokenResponse)
def issue_token(payload: TokenRequest, db: Session = Depends(get_db)):
    api_key = authenticate_api_key(payload.api_key, db)
    check_and_increment_quota(api_key, db)
    access_token, expires_in = create_access_token(api_key)
    return TokenResponse(access_token=access_token, expires_in=expires_in)


@app.post("/v1/predict", response_model=PredictResponse)
def predict(payload: PredictRequest, api_key: ApiKey = Depends(get_current_api_key)):
    # Placeholder: panggil model AI sendiri di sini.
    return PredictResponse(result=f"echo: {payload.input}")
