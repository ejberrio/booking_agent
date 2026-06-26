from pydantic_settings import BaseSettings, SettingsConfigDict


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

    # Busqueda web (eventos / mercado)
    search_provider: str = "tavily"
    search_api_key: str | None = None
    search_base_url: str = "https://api.tavily.com"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
