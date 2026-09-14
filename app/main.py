import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from app.admin import router as admin_router
from app.auth import (
    authenticate_api_key,
    check_and_increment_quota,
    create_access_token,
    get_api_key_from_x_api_key,
    get_current_api_key,
)
from app.models import ApiKey, get_db, init_db
from app.schemas import (
    MessagesRequest,
    PredictRequest,
    PredictResponse,
    TokenRequest,
    TokenResponse,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="API & Token Provider", version="1.0.0", lifespan=lifespan)
app.include_router(admin_router)

STATIC_DIR = Path(__file__).resolve().parent / "static"
app.mount("/admin/ui", StaticFiles(directory=STATIC_DIR, html=True), name="admin-ui")


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


@app.post("/v1/messages")
def messages(payload: MessagesRequest, api_key: ApiKey = Depends(get_api_key_from_x_api_key)):
    """Endpoint kompatibilitas untuk client eksternal yang bicara format Anthropic Messages API.

    Beda dengan /v1/predict, endpoint ini menerima API key langsung lewat header
    `x-api-key` (tanpa exchange JWT) supaya cocok dengan client generic yang cuma
    punya satu kolom "API key" — persis cara kerja API key Anthropic asli.
    """
    last_user_text = ""
    for message in reversed(payload.messages):
        if message.role != "user":
            continue
        content = message.content
        if isinstance(content, str):
            last_user_text = content
        elif isinstance(content, list):
            last_user_text = " ".join(
                block.get("text", "") for block in content if isinstance(block, dict)
            ).strip()
        break

    # Placeholder: panggil model AI sendiri di sini, lalu ganti teks di bawah dengan hasilnya.
    reply_text = (
        "[Placeholder] Model AI Anda belum dipasang di endpoint ini. "
        f"Pesan yang diterima: {last_user_text or '(kosong)'}"
    )

    return {
        "id": f"msg_{uuid.uuid4().hex}",
        "type": "message",
        "role": "assistant",
        "model": payload.model or "self-hosted-placeholder",
        "content": [{"type": "text", "text": reply_text}],
        "stop_reason": "end_turn",
        "stop_sequence": None,
        "usage": {"input_tokens": 0, "output_tokens": 0},
    }
