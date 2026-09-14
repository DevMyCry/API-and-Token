def create_key(client, admin_headers, label="test-client", daily_quota=None):
    payload = {"label": label}
    if daily_quota is not None:
        payload["daily_quota"] = daily_quota
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
    created = create_key(client, admin_headers, label="klien-kuota-kecil", daily_quota=1)

    first = client.post("/auth/token", json={"api_key": created["api_key"]})
    assert first.status_code == 200

    second = client.post("/auth/token", json={"api_key": created["api_key"]})
    assert second.status_code == 429
