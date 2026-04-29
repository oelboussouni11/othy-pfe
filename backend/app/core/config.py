from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=PROJECT_ROOT / ".env", extra="ignore")

    environment: str = "development"
    log_level: str = "INFO"

    db_url: str = "postgresql+psycopg://smartlaunchqa:smartlaunchqa@localhost:5432/smartlaunchqa"
    redis_url: str = "redis://localhost:6379/0"

    jwt_secret: str = "dev-only-change-this-secret-to-32-plus-random-bytes-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_ttl_min: int = 15
    jwt_refresh_token_ttl_days: int = 7

    backend_cors_origins: str = "http://localhost:3000"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.backend_cors_origins.split(",") if o.strip()]


settings = Settings()
