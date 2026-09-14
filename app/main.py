import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from app.admin import router as admin_router
from app.auth import (
    authenticate_api_key,
    check_and_increment_quota,
    create_access_token,
    get_api_key_from_bearer,
    get_api_key_from_x_api_key,
    get_current_api_key,
)
from app.models import ApiKey, get_db, init_db
from app.schemas import (
    ChatCompletionsRequest,
    MessageInput,
    MessagesRequest,
    PredictRequest,
    PredictResponse,
    ResponsesRequest,
    TokenRequest,
    TokenResponse,
)


def _extract_last_user_text(messages: list[MessageInput]) -> str:
    for message in reversed(messages):
        if message.role != "user":
            continue
        content = message.content
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            return " ".join(
                block.get("text", "") for block in content if isinstance(block, dict)
            ).strip()
        break
    return ""


def _extract_responses_input_text(input_value: Any) -> str:
    if isinstance(input_value, str):
        return input_value
    if isinstance(input_value, list):
        for item in reversed(input_value):
            if not isinstance(item, dict) or item.get("role") != "user":
                continue
            content = item.get("content")
            if isinstance(content, str):
                return content
            if isinstance(content, list):
                return " ".join(
                    block.get("text", "") for block in content if isinstance(block, dict)
                ).strip()
    return ""


def _placeholder_reply(user_text: str) -> str:
    # Placeholder: panggil model AI sendiri di sini, lalu ganti teks ini dengan hasilnya.
    return (
        "[Placeholder] Model AI Anda belum dipasang di endpoint ini. "
        f"Pesan yang diterima: {user_text or '(kosong)'}"
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
    """Kompatibilitas format "Anthropic messages" — API key lewat header x-api-key."""
    reply_text = _placeholder_reply(_extract_last_user_text(payload.messages))

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


@app.post("/chat/completions")
@app.post("/v1/chat/completions")
def chat_completions(payload: ChatCompletionsRequest, api_key: ApiKey = Depends(get_api_key_from_bearer)):
    """Kompatibilitas format "Chat completions" ala OpenAI — Authorization: Bearer <API key>."""
    reply_text = _placeholder_reply(_extract_last_user_text(payload.messages))

    return {
        "id": f"chatcmpl-{uuid.uuid4().hex}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": payload.model or "self-hosted-placeholder",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": reply_text},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
    }


@app.post("/responses")
@app.post("/v1/responses")
def responses(payload: ResponsesRequest, api_key: ApiKey = Depends(get_api_key_from_bearer)):
    """Kompatibilitas format "Responses" ala OpenAI — Authorization: Bearer <API key>."""
    reply_text = _placeholder_reply(_extract_responses_input_text(payload.input))
    message_id = f"msg_{uuid.uuid4().hex}"

    return {
        "id": f"resp_{uuid.uuid4().hex}",
        "object": "response",
        "created_at": int(time.time()),
        "model": payload.model or "self-hosted-placeholder",
        "status": "completed",
        "output": [
            {
                "type": "message",
                "id": message_id,
                "status": "completed",
                "role": "assistant",
                "content": [{"type": "output_text", "text": reply_text, "annotations": []}],
            }
        ],
        "output_text": reply_text,
        "usage": {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0},
    }
