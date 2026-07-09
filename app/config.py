"""Application configuration."""

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings from environment variables."""

    database_url: str = Field(
        default="postgresql+psycopg://ghostloom:ghostloom@localhost:5432/ghostloom",
        validation_alias=AliasChoices("DATABASE_URL", "database_url"),
    )
    session_secret: str = Field(
        default="dev-only-change-me",
        validation_alias=AliasChoices("SESSION_SECRET", "session_secret"),
    )
    byok_encryption_key: str = Field(
        default="",
        validation_alias=AliasChoices("BYOK_ENCRYPTION_KEY", "byok_encryption_key"),
    )
    cors_origins: str = Field(
        default="http://localhost:3000",
        validation_alias=AliasChoices("CORS_ORIGINS", "cors_origins"),
    )
    llm_api_key: str = Field(
        default="",
        validation_alias=AliasChoices("OPENAI_API_KEY", "llm_api_key"),
    )
    session_ttl_days: int = 30

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
