# API-and-Token

Backend self-hosted untuk menerbitkan dan mengelola **API key** serta **access token (JWT)** milik sendiri — tanpa bergantung pada provider auth pihak ketiga berbayar (Auth0, Firebase Auth, AWS Cognito, dll). Cocok dipakai sebagai lapisan otentikasi/otorisasi di depan model AI atau layanan lain yang Anda "provide" sendiri ke klien.

## Fitur

1. **Generate & kelola API key** — key acak kriptografis (`secrets.token_urlsafe`), hanya hash SHA-256-nya yang disimpan di database. Plaintext key hanya ditampilkan sekali saat dibuat/di-rotate.
2. **Access token berbasis JWT** — klien menukar API key dengan JWT access token berumur pendek (`POST /auth/token`), lalu memakai token itu untuk memanggil endpoint yang dilindungi.
3. **Rate limiting & kuota per API key** — setiap key punya kuota request/hari (default via env, bisa dioverride per key). Kuota di-reset otomatis saat tanggal berganti. Jika kuota habis, server membalas `429 Too Many Requests`.

## Struktur proyek

```
app/
  main.py     -> entrypoint FastAPI, endpoint /auth/token dan /v1/predict
  admin.py    -> router admin untuk create/list/revoke/rotate API key
  auth.py     -> hashing key, verifikasi, generate & decode JWT, dependency proteksi
  models.py   -> model SQLAlchemy (ApiKey, UsageCounter) + koneksi DB
  schemas.py  -> skema request/response Pydantic
  config.py   -> baca konfigurasi dari environment variable
tests/
  test_api.py -> tes end-to-end pakai pytest + FastAPI TestClient
```

## Instalasi & menjalankan secara lokal

Butuh Python 3.11+.

```bash
git clone https://github.com/DevMyCry/API-and-Token.git
cd API-and-Token

python3 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt

cp .env.example .env
# lalu edit .env: ganti ADMIN_SECRET dan JWT_SECRET dengan nilai rahasia Anda sendiri

uvicorn app.main:app --reload
```

Server jalan di `http://127.0.0.1:8000`. Database SQLite (`data.db`) akan dibuat otomatis di direktori kerja saat server pertama kali start.

## Konfigurasi (environment variable)

Lihat `.env.example`:

| Variable | Default | Keterangan |
|---|---|---|
| `ADMIN_SECRET` | `change-me-admin-secret` | Secret untuk mengakses endpoint admin. **Wajib diganti.** |
| `JWT_SECRET` | `change-me-jwt-secret` | Secret untuk menandatangani JWT. **Wajib diganti.** |
| `JWT_ALGORITHM` | `HS256` | Algoritma JWT. |
| `JWT_EXPIRY_SECONDS` | `3600` | Umur access token (detik). |
| `DEFAULT_DAILY_QUOTA` | `1000` | Kuota request/hari default untuk API key baru. |
| `DATABASE_URL` | `sqlite:///./data.db` | Connection string database (SQLAlchemy). |

## Endpoint

### Admin — kelola API key

Semua endpoint admin butuh header `X-Admin-Secret: <ADMIN_SECRET>`.

#### Buat API key baru

```bash
curl -X POST http://127.0.0.1:8000/admin/keys \
  -H "X-Admin-Secret: <ADMIN_SECRET>" \
  -H "Content-Type: application/json" \
  -d '{"label": "klien-a", "daily_quota": 1000}'
```

Response (plaintext key **hanya muncul di sini, sekali saja** — simpan baik-baik):

```json
{
  "id": "055eb70247934def979c83a1c8d998d4",
  "label": "klien-a",
  "api_key": "vs8L-toxHqB1OUJF0g3Y-lfmgkllK5oDz6a9X8-B-ws",
  "daily_quota": 1000,
  "created_at": "2026-09-14T04:56:48.944379"
}
```

`daily_quota` opsional; jika tidak dikirim, memakai `DEFAULT_DAILY_QUOTA`.

#### List API key

```bash
curl http://127.0.0.1:8000/admin/keys \
  -H "X-Admin-Secret: <ADMIN_SECRET>"
```

Tidak pernah menampilkan plaintext key, hanya metadata (`id`, `label`, `daily_quota`, `is_revoked`, `created_at`).

#### Revoke API key

```bash
curl -X POST http://127.0.0.1:8000/admin/keys/<key_id>/revoke \
  -H "X-Admin-Secret: <ADMIN_SECRET>"
```

Key yang sudah di-revoke tidak bisa lagi dipakai untuk menukar token maupun memanggil endpoint terproteksi.

#### Rotate API key

Menerbitkan plaintext key baru untuk `id` yang sama (key lama otomatis tidak berlaku lagi karena hash-nya diganti):

```bash
curl -X POST http://127.0.0.1:8000/admin/keys/<key_id>/rotate \
  -H "X-Admin-Secret: <ADMIN_SECRET>"
```

### Auth — tukar API key dengan access token

```bash
curl -X POST http://127.0.0.1:8000/auth/token \
  -H "Content-Type: application/json" \
  -d '{"api_key": "<PLAINTEXT_API_KEY>"}'
```

Response:

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

Endpoint ini juga memakan kuota harian API key. Jika kuota habis, responsnya `429`.

### Endpoint terproteksi (contoh)

`POST /v1/predict` adalah placeholder tempat memanggil model AI Anda sendiri. Wajib membawa `Authorization: Bearer <access_token>`.

```bash
curl -X POST http://127.0.0.1:8000/v1/predict \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"input": "halo dunia"}'
```

Response:

```json
{"result": "echo: halo dunia"}
```

Setiap pemanggilan endpoint ini juga memakan kuota harian API key pemilik token; kalau habis, responsnya `429`.

### Health check

```bash
curl http://127.0.0.1:8000/health
```

## Menjalankan tes

```bash
source .venv/bin/activate
pip install -r requirements.txt
pytest -v
```

Tes mencakup: generate key & tukar token (sukses), API key salah ditolak, API key yang sudah di-revoke ditolak, dan kuota habis mengembalikan `429`.

## Deploy self-hosted dengan Docker

```bash
docker build -t api-and-token .

docker run -d \
  --name api-and-token \
  -p 8000:8000 \
  -e ADMIN_SECRET="ganti-dengan-secret-anda" \
  -e JWT_SECRET="ganti-dengan-secret-anda" \
  -e JWT_EXPIRY_SECONDS=3600 \
  -e DEFAULT_DAILY_QUOTA=1000 \
  -v $(pwd)/data:/app/data \
  -e DATABASE_URL="sqlite:////app/data/data.db" \
  api-and-token
```

Mount volume (`-v`) supaya database SQLite tidak hilang saat container di-restart. Semua komponen (FastAPI, SQLite, JWT) berjalan sepenuhnya di server Anda sendiri — tidak ada biaya langganan ke provider auth pihak ketiga.

## Catatan keamanan

- **Jangan pernah commit file `.env`** atau API key/secret asli ke git. Repo ini sudah mengabaikan `.env` dan `*.db` lewat `.gitignore`.
- Plaintext API key hanya ditampilkan **satu kali** saat dibuat/di-rotate — sistem hanya menyimpan hash SHA-256-nya. Jika hilang, buat/rotate key baru; jangan berharap bisa "melihat lagi" key lama.
- Kalau ada API key yang bocor (misalnya ter-commit atau bocor lewat log klien), segera **revoke** lewat endpoint admin, lalu terbitkan key baru untuk klien tersebut.
- Ganti `ADMIN_SECRET` dan `JWT_SECRET` dengan nilai acak yang kuat sebelum deploy ke production — jangan pakai nilai default di `.env.example`.
- Jangan log body request yang berisi API key plaintext atau JWT di sistem logging Anda.
