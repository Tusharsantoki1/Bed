"""Application settings, loaded from .env and validated with Pydantic."""

from __future__ import annotations

from functools import lru_cache
from urllib.parse import quote_plus

from pydantic import EmailStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """App settings, loaded from environment variables and/or a .env file."""

    # --- App ---
    PROJECT_NAME: str = "GST Billing API"
    DEBUG: bool = False
    API_PREFIX: str = "/api"

    # --- Database (PostgreSQL) ---
    DB_HOST: str = "127.0.0.1"
    DB_PORT: int = 5432
    DB_USER: str = "postgres"
    DB_PASSWORD: str = ""
    DB_NAME: str = "gst_billing"
    # Optional full-URL override (leave empty to use the parts above):
    DATABASE_URL: str = ""

    @property
    def SYNC_DATABASE_URL(self) -> str:
        """Get the full synchronous database URL, building it from parts if needed."""
        if self.DATABASE_URL:  # For services like Neon, the full URL is provided.
            # Ensure the driver is psycopg.
            if self.DATABASE_URL.startswith("postgres://"):
                return self.DATABASE_URL.replace("postgres://", "postgresql+psycopg://", 1)
            return self.DATABASE_URL

        # Build from parts for local development.
        password = quote_plus(self.DB_PASSWORD)
        return f"postgresql+psycopg://{self.DB_USER}:{password}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    # --- Security ---
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    ALGORITHM: str = "HS256"

    # --- CORS ---
    CORS_ORIGINS: str = ""

    @property
    def cors_origins_list(self) -> list[str]:
        """Get the CORS origins as a list of strings."""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    # --- First super admin (created by the seed script) ---
    SUPER_ADMIN_EMAIL: EmailStr
    SUPER_ADMIN_PASSWORD: str
    SUPER_ADMIN_NAME: str

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()