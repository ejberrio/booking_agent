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


# Nota: /chat ahora es el agente real (requiere DB y orquestador); su comportamiento
# se prueba en tests/test_agent_orchestrator.py con FakeLLM + ChannelManager falso.
