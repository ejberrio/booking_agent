from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_root():
    res = client.get("/")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_health():
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json() == {"status": "healthy"}


def test_chat_demo_mode():
    res = client.post("/chat", json={"message": "hola"})
    assert res.status_code == 200
    assert "reply" in res.json()
