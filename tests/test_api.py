def create_key(client, admin_headers, label="test-client", quota_limit=None, quota_period_seconds=None):
    payload = {"label": label}
    if quota_limit is not None:
        payload["quota_limit"] = quota_limit
    if quota_period_seconds is not None:
        payload["quota_period_seconds"] = quota_period_seconds
    response = client.post("/admin/keys", json=payload, headers=admin_headers)
    assert response.status_code == 201
    return response.json()


def test_generate_key_and_exchange_token_success(client, admin_headers):
    created = create_key(client, admin_headers, label="klien-a")
    assert created["api_key"]
    assert created["label"] == "klien-a"

    token_response = client.post("/auth/token", json={"api_key": created["api_key"]})
    assert token_response.status_code == 200
    body = token_response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]

    predict_response = client.post(
        "/v1/predict",
        json={"input": "halo"},
        headers={"Authorization": f"Bearer {body['access_token']}"},
    )
    assert predict_response.status_code == 200
    assert predict_response.json()["result"] == "echo: halo"


def test_wrong_api_key_rejected(client, admin_headers):
    response = client.post("/auth/token", json={"api_key": "kunci-yang-tidak-pernah-ada"})
    assert response.status_code == 401


def test_revoked_key_rejected(client, admin_headers):
    created = create_key(client, admin_headers, label="klien-b")

    revoke_response = client.post(f"/admin/keys/{created['id']}/revoke", headers=admin_headers)
    assert revoke_response.status_code == 200
    assert revoke_response.json()["is_revoked"] is True

    token_response = client.post("/auth/token", json={"api_key": created["api_key"]})
    assert token_response.status_code == 401


def test_quota_exceeded_returns_429(client, admin_headers):
    created = create_key(client, admin_headers, label="klien-kuota-kecil", quota_limit=1)

    first = client.post("/auth/token", json={"api_key": created["api_key"]})
    assert first.status_code == 200

    second = client.post("/auth/token", json={"api_key": created["api_key"]})
    assert second.status_code == 429


def test_custom_quota_period_is_stored(client, admin_headers):
    created = create_key(
        client, admin_headers, label="klien-2-jam", quota_limit=10_000_000, quota_period_seconds=7200
    )
    assert created["quota_limit"] == 10_000_000
    assert created["quota_period_seconds"] == 7200


def test_messages_endpoint_accepts_api_key_directly(client, admin_headers):
    created = create_key(client, admin_headers, label="klien-messages")

    response = client.post(
        "/v1/messages",
        json={"model": "self-hosted", "messages": [{"role": "user", "content": "halo"}]},
        headers={"x-api-key": created["api_key"]},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["role"] == "assistant"
    assert body["content"][0]["type"] == "text"
    assert "halo" in body["content"][0]["text"]


def test_messages_endpoint_rejects_wrong_api_key(client, admin_headers):
    response = client.post(
        "/v1/messages",
        json={"messages": [{"role": "user", "content": "halo"}]},
        headers={"x-api-key": "kunci-yang-tidak-pernah-ada"},
    )
    assert response.status_code == 401


def test_chat_completions_accepts_bearer_api_key(client, admin_headers):
    created = create_key(client, admin_headers, label="klien-chat-completions")

    response = client.post(
        "/chat/completions",
        json={"model": "self-hosted", "messages": [{"role": "user", "content": "halo chat"}]},
        headers={"Authorization": f"Bearer {created['api_key']}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["object"] == "chat.completion"
    assert "halo chat" in body["choices"][0]["message"]["content"]


def test_chat_completions_rejects_wrong_api_key(client, admin_headers):
    response = client.post(
        "/chat/completions",
        json={"messages": [{"role": "user", "content": "halo"}]},
        headers={"Authorization": "Bearer kunci-yang-tidak-pernah-ada"},
    )
    assert response.status_code == 401


def test_responses_endpoint_accepts_bearer_api_key(client, admin_headers):
    created = create_key(client, admin_headers, label="klien-responses")

    response = client.post(
        "/responses",
        json={"model": "self-hosted", "input": "halo responses"},
        headers={"Authorization": f"Bearer {created['api_key']}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["object"] == "response"
    assert "halo responses" in body["output_text"]


def test_responses_endpoint_rejects_wrong_api_key(client, admin_headers):
    response = client.post(
        "/responses",
        json={"input": "halo"},
        headers={"Authorization": "Bearer kunci-yang-tidak-pernah-ada"},
    )
    assert response.status_code == 401
