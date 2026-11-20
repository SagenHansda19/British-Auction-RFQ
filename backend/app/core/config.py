from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# .env lives in the repo root
ENV_FILE = Path(__file__).resolve().parents[3] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_FILE, extra="ignore")

    database_url: str = "postgresql+psycopg://rfq:rfq@localhost:5432/rfq"
    test_database_url: str = "postgresql+psycopg://rfq:rfq@localhost:5432/rfq_test"
    redis_url: str = "redis://localhost:6379/0"
    cors_origins: list[str] = ["http://localhost:5173"]


settings = Settings()
