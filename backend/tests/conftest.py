import pytest
from fastapi.testclient import TestClient

from app.main import db, app


@pytest.fixture(autouse=True)
def reset_db():
    db.reset()
    yield
    db.reset()


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def user_creds():
    return {"email": "test@example.com", "username": "tester", "password": "secret123"}


@pytest.fixture
def auth(client, user_creds):
    client.post("/api/v1/auth/register", json=user_creds)
    token = client.post("/api/v1/auth/login", json={"email": user_creds["email"], "password": user_creds["password"]}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
