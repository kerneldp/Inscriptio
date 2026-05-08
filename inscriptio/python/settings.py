from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Core
    environment: str = "dev"  # dev | prod
    api_title: str = "Inscriptio API"
    api_version: str = "1.0.0"

    # Security
    secret_key: str = "dev-only-change-me"
    jwt_algorithm: str = "HS256"
    token_expire_hours: int = 24

    # CORS
    cors_allow_origins: str = "http://localhost:5500,http://127.0.0.1:5500"

    # Database
    database_url: str = "sqlite:///./inscriptio.db"

    # Demo mode (optional)
    demo_mode: bool = True

    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_allow_origins.split(",") if o.strip()]


settings = Settings()

