from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.db.session import SessionLocal

router = APIRouter()


@router.get("/health")
async def health():
    """Liveness + verificación de la base de datos.

    200 {"status":"healthy","db":"up"} si la DB responde;
    503 {"status":"degraded","db":"down"} si no (p. ej. Neon caído/suspendido).
    No expone detalles internos ni secretos.
    """
    try:
        async with SessionLocal() as session:
            await session.execute(text("SELECT 1"))
    except Exception:
        return JSONResponse(status_code=503, content={"status": "degraded", "db": "down"})
    return {"status": "healthy", "db": "up"}
