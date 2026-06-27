from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

import app.api.routes.health as health_mod
from app.main import app

client = TestClient(app)


def test_root():
    res = client.get("/")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_health_ok(monkeypatch):
    # SessionLocal apuntando a SQLite en memoria -> SELECT 1 funciona.
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    maker = async_sessionmaker(engine, expire_on_commit=False)
    monkeypatch.setattr(health_mod, "SessionLocal", maker)

    res = client.get("/health")
    assert res.status_code == 200
    assert res.json() == {"status": "healthy", "db": "up"}


def test_health_degraded_when_db_down(monkeypatch):
    class _BoomSession:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

        async def execute(self, *a, **k):
            raise RuntimeError("db down")

    monkeypatch.setattr(health_mod, "SessionLocal", lambda: _BoomSession())

    res = client.get("/health")
    assert res.status_code == 503
    assert res.json() == {"status": "degraded", "db": "down"}
