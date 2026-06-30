"""Application configuration loaded from environment variables / .env file."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL


class Settings(BaseSettings):
    # App
    PROJECT_NAME: str = "GST Billing API"
    DEBUG: bool = True
    API_PREFIX: str = "/api"

    # Database — give the parts separately; the password is encoded safely,
    # so special characters like @ ! # are fine without manual escaping.
    DB_HOST: str = "127.0.0.1"
    DB_PORT: int = 3306
    DB_USER: str = "root"
    DB_PASSWORD: str = "Divij@2026!"
    DB_NAME: str = "gst_billing"
    # Optional: set a full URL to override the parts above.
    DATABASE_URL: str = ""

    # Security
    SECRET_KEY: str = "change-me"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # CORS — comma separated list of origins, or "*"
    CORS_ORIGINS: str = "*"

    # First super admin (used by the seed script)
    SUPER_ADMIN_EMAIL: str = "superadmin@example.com"
    SUPER_ADMIN_PASSWORD: str = "ChangeThisStrongPassword123!"
    SUPER_ADMIN_NAME: str = "Platform Owner"

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    @property
    def database_url(self) -> str:
        """Full SQLAlchemy URL. Uses DATABASE_URL if set, else builds it from
        the DB_* parts with the password safely URL-encoded."""
        if self.DATABASE_URL.strip():
            return self.DATABASE_URL.strip()
        return URL.create(
            "mysql+pymysql",
            username=self.DB_USER,
            password=self.DB_PASSWORD,
            host=self.DB_HOST,
            port=self.DB_PORT,
            database=self.DB_NAME,
        ).render_as_string(hide_password=False)

    @property
    def cors_origins_list(self) -> list[str]:
        if self.CORS_ORIGINS.strip() == "*":
            return ["*"]
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
