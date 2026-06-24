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
    llm_provider: str = "anthropic"
    llm_model: str = "claude-opus-4-8"
    anthropic_api_key: str | None = None
    openai_api_key: str | None = None
    llm_max_usd_per_day: float = 5.0

    # Channel Manager (se decide en Fase 2)
    channel_manager: str | None = None
    cm_api_key: str | None = None
    cm_api_secret: str | None = None

    # Busqueda web (eventos / mercado)
    search_provider: str = "tavily"
    search_api_key: str | None = None

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
