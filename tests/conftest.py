import os
import tempfile

import pytest

_db_fd, _db_path = tempfile.mkstemp(suffix=".db")
os.close(_db_fd)

os.environ["ADMIN_SECRET"] = "test-admin-secret"
os.environ["JWT_SECRET"] = "test-jwt-secret"
os.environ["JWT_ALGORITHM"] = "HS256"
os.environ["JWT_EXPIRY_SECONDS"] = "3600"
os.environ["DEFAULT_DAILY_QUOTA"] = "1000"
os.environ["DATABASE_URL"] = f"sqlite:///{_db_path}"

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.models import init_db  # noqa: E402

init_db()


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="session")
def admin_headers():
    return {"X-Admin-Secret": os.environ["ADMIN_SECRET"]}


def pytest_sessionfinish(session, exitstatus):
    try:
        os.remove(_db_path)
    except OSError:
        pass
