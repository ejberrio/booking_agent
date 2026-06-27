import ssl as _ssl
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from pydantic_settings import BaseSettings, SettingsConfigDict


def normalize_db_url(url: str) -> tuple[str, dict[str, Any]]:
    """Normaliza una cadena de conexión Postgres para asyncpg.

    - Fuerza el driver `postgresql+asyncpg`.
    - Elimina parámetros estilo libpq que asyncpg NO entiende (`sslmode`,
      `channel_binding`) y los traduce a `connect_args` con la semántica correcta:
        * `require`/`prefer` → cifrar SIN verificar el certificado (como libpq).
        * `verify-ca`/`verify-full` → cifrar Y verificar contra el CA del sistema.
        * `disable`/`allow`/ausente → sin SSL.

    Permite pegar la URL de Neon tal cual (con `?sslmode=require`).
    Devuelve (url_normalizada, connect_args).
    """
    parts = urlsplit(url)
    scheme = parts.scheme
    if scheme in ("postgres", "postgresql") or (
        scheme.startswith("postgresql+") and "asyncpg" not in scheme
    ):
        scheme = "postgresql+asyncpg"

    query = dict(parse_qsl(parts.query))
    sslmode = (query.pop("sslmode", None) or "").lower()
    query.pop("channel_binding", None)

    normalized = urlunsplit(
        (scheme, parts.netloc, parts.path, urlencode(query), parts.fragment)
    )
    connect_args: dict[str, Any] = {}
    if sslmode in ("require", "prefer"):
        ctx = _ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = _ssl.CERT_NONE
        connect_args["ssl"] = ctx
    elif sslmode in ("verify-ca", "verify-full"):
        connect_args["ssl"] = _ssl.create_default_context()
    return normalized, connect_args


class Settings(BaseSettings):
    """Configuracion de la aplicacion. Lee variables de entorno y, si existe, un .env."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: str = "development"

    # Base de datos
    database_url: str = "postgresql+asyncpg://booking:booking@localhost:5432/booking"

    # API
    cors_origins: str = "http://localhost:3000"
    secret_key: str = "cambia-esto"

    # LLM (multi-proveedor via LiteLLM)
    # Estrategia dos niveles: modelo barato para tareas de alto volumen
    # (leer/resumir eventos y mercado) y modelo capaz para acciones del
    # agente que escriben precios. Cambiable por config gracias a LiteLLM.
    llm_provider: str = "openai"
    llm_model: str = "gpt-4o-mini"  # tareas generales / desarrollo
    llm_model_actions: str = "gpt-4o"  # loop del agente que aplica cambios
    anthropic_api_key: str | None = None
    openai_api_key: str | None = None
    llm_max_usd_per_day: float = 5.0

    # Channel Manager (Beds24, API V1 con API Key de cuenta)
    channel_manager: str | None = None
    cm_api_key: str | None = None
    cm_api_secret: str | None = None
    beds24_api_key: str | None = None
    beds24_prop_key: str | None = None  # requerido por getRoomDates/getBookings/setRoomDates (>=16)
    beds24_prop_id: str | None = None
    beds24_room_id: str | None = None
    beds24_base_url: str = "https://api.beds24.com/json"
    # API V2 (token): obligatoria para ESCRIBIR precios (las escrituras de V1 están muertas).
    # "v1" = solo lectura; "v2" = lectura + escritura con refreshToken.
    beds24_api_version: str = "v1"
    beds24_v2_base_url: str = "https://api.beds24.com/v2"
    beds24_refresh_token: str | None = None  # se canjea por tokens de 24h en /authentication/token

    # Busqueda web (eventos / mercado)
    search_provider: str = "tavily"
    search_api_key: str | None = None
    search_base_url: str = "https://api.tavily.com"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def normalized_database_url(self) -> str:
        return normalize_db_url(self.database_url)[0]

    @property
    def db_connect_args(self) -> dict[str, Any]:
        return normalize_db_url(self.database_url)[1]


settings = Settings()
