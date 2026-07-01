import logging

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_request_logs_one_structured_line(caplog):
    with caplog.at_level(logging.INFO, logger="api.request"):
        client.get("/")
    lines = [r.getMessage() for r in caplog.records if r.name == "api.request"]
    assert any(("method=GET" in m and "path=/" in m and "status=200" in m and "ms=" in m) for m in lines)
    # no debe filtrar query ni secretos (la ruta / no tiene)
    assert all("?" not in m for m in lines)
