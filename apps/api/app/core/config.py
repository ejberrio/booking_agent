import ssl as _ssl
from typing import TYPE_CHECKING, Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from pydantic_settings import BaseSettings, SettingsConfigDict

if TYPE_CHECKING:  # solo para anotaciones; el import real es local (evita ciclo)
    from app.models.enums import ChannelKind


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
    # Feature 026: "legacy" = transición: con sesión (Bearer) se usa esa cuenta; sin ella,
    # la cuenta nº 1 (la web antigua). "sessions" = toda petición exige sesión válida.
    auth_mode: str = "legacy"
    # Dirección pública de la web (enlaces de los correos). Staging pone la suya.
    public_base_url: str = "https://staylever.com"
    # Feature 026 — ambiente de pruebas: "simulated" = el Channel Manager se simula con la
    # base local (NUNCA habla con Beds24/Booking/Airbnb) y no se envían avisos al celular.
    # Producción: "real" (por defecto).
    channel_mode: str = "real"

    @property
    def sandbox(self) -> bool:
        return self.channel_mode == "simulated"

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
    # Modelos de razonamiento (gpt-5.x / gpt-6 Luna/Sol): esfuerzo de razonamiento. En Chat
    # Completions, las herramientas (agente) solo funcionan con "none". Vacío = no se envía
    # (modelos clásicos como gpt-4o, que no lo aceptan).
    llm_reasoning_effort: str | None = None

    # Uso y límites de IA por cuenta (feature 027). Precios en USD: por millón de tokens
    # [entrada, salida] por modelo, y por búsqueda web. `AI_PRICES` (JSON) los reemplaza.
    ai_prices: dict = {
        "gpt-6-luna": [0.10, 0.50],
        "gpt-4o-mini": [0.15, 0.60],
        "gpt-4o": [2.50, 10.0],
        "search": 0.008,
    }
    ai_chat_limit_month: int = 300  # mensajes al asistente por cuenta y mes
    ai_search_limit_day: int = 5  # búsquedas web del escaneo por cuenta y día
    # Feature 034: fuentes de eventos a apagar (coma): tuboleta, ticketmaster, plazamayor, all.
    event_sources_disabled: str = ""
    ai_timezone: str = "America/Bogota"  # para el día y el mes de los contadores

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
    # Oferta designada (slot 1–16) donde se cuelgan las promociones (feature 011).
    # El "slot" se crea una vez en el panel de Beds24 (enable=always); aquí solo su número.
    beds24_promo_offer_id: int | None = None
    # Canales conectados en el Channel Manager (feature 012). CSV de ChannelKind.
    # Beds24 no expone el estado de conexión por canal de forma consultable, así que
    # el operador lo declara aquí; quitar un canal = marcarlo inactivo (sus reservas
    # históricas se conservan).
    channels_active: str = "booking,airbnb"

    # Busqueda web (eventos / mercado)
    search_provider: str = "tavily"
    search_api_key: str | None = None
    search_base_url: str = "https://api.tavily.com"

    # Sugerencias: no repetir lo que el host ya decidió (aplicó o rechazó). Solo se
    # vuelve a proponer una noche decidida si el nuevo precio difiere del decidido más
    # de este % (o cambia de sentido). Y no se sugiere nada si el precio actual ya está
    # a menos de la tolerancia del sugerido.
    suggestion_repeat_threshold_pct: float = 15.0
    suggestion_same_price_tolerance_pct: float = 1.0

    # Observabilidad
    sentry_dsn: str | None = None  # si está, se activa Sentry; sin él es no-op
    log_level: str = "INFO"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    def active_channel_kinds(self) -> list["ChannelKind"]:
        """Kinds de canal declarados como conectados (tolerante a espacios y valores inválidos)."""
        from app.models.enums import ChannelKind  # import local: evita ciclo config<->models

        out: list[ChannelKind] = []
        for token in self.channels_active.split(","):
            token = token.strip().lower()
            if not token:
                continue
            try:
                kind = ChannelKind(token)
            except ValueError:
                continue
            if kind not in out:
                out.append(kind)
        return out

    @property
    def normalized_database_url(self) -> str:
        return normalize_db_url(self.database_url)[0]

    @property
    def db_connect_args(self) -> dict[str, Any]:
        return normalize_db_url(self.database_url)[1]


settings = Settings()
