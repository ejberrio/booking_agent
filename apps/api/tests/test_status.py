from fastapi.testclient import TestClient

import app.api.routes.status as status_mod
from app.main import app

client = TestClient(app)


def _areturn(v):
    async def f():
        return v
    return f


def test_status_shape(monkeypatch):
    monkeypatch.setattr(status_mod, "_db_status", _areturn("up"))
    monkeypatch.setattr(status_mod, "_beds24_status", _areturn("connected"))
    monkeypatch.setattr(status_mod, "_open_issues", _areturn(3))
    channels = [
        {"kind": "booking", "is_active": True, "bookings": 12},
        {"kind": "airbnb", "is_active": True, "bookings": 3},
    ]
    monkeypatch.setattr(status_mod, "_channels_status", _areturn(channels))
    res = client.get("/status")
    assert res.status_code == 200
    d = res.json()
    assert d["version"] and d["db"] == "up" and d["beds24"] == "connected" and d["open_issues"] == 3
    assert d["channels"] == channels


def test_status_resilient_db_down(monkeypatch):
    monkeypatch.setattr(status_mod, "_db_status", _areturn("down"))
    monkeypatch.setattr(status_mod, "_beds24_status", _areturn("error"))
    monkeypatch.setattr(status_mod, "_open_issues", _areturn(-1))
    monkeypatch.setattr(status_mod, "_channels_status", _areturn([]))
    res = client.get("/status")
    assert res.status_code == 200  # responde igual, marcando degradado
    d = res.json()
    assert d["db"] == "down"
    assert d["channels"] == []  # resiliente: sin datos, sin 500
