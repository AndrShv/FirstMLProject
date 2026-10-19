from pathlib import Path
from typing import Optional, Any

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENV_PATH = BASE_DIR / "proprts.env"


class Settings(BaseSettings):
    DEBUG: bool = False
    PROJECT_NAME: str = "ML Service Example"
    PORT: int = 8001
    LOG_LEVEL: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=("proprts.env", str(ENV_PATH)),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # --- PostgreSQL ---
    POSTGRES_USER: str = "root"
    POSTGRES_PASSWORD: str = ""
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "ml_service"
    DATABASE_URL: Optional[str] = None

    @property
    def database_url(self) -> str:
        if self.DATABASE_URL:
            url = self.DATABASE_URL
            if url.startswith("postgresql://"):
                url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
            if "?ssl=disable" not in url and "localhost" in url:
                url += "?ssl=disable"
            return url
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
            f"?ssl=disable"
        )

    # --- RabbitMQ ---
    CLOUDAMQP_URL: Optional[str] = None
    RABBITMQ_URL: Optional[str] = None
    RABBIT_HOST: str = "localhost"
    RABBIT_PORT: int = 5672
    RABBIT_USERNAME: str = ""
    RABBIT_PASSWORD: str = ""
    MAIN_QUEUE_NAME: str = "ml.queue.main.queue"

    @property
    def rabbitmq_url(self) -> str:
        if self.CLOUDAMQP_URL:
            return self.CLOUDAMQP_URL
        if self.RABBITMQ_URL:
            return self.RABBITMQ_URL

        auth = ""
        if self.RABBIT_USERNAME or self.RABBIT_PASSWORD:
            auth = f"{self.RABBIT_USERNAME}:{self.RABBIT_PASSWORD}@"

        return f"amqp://{auth}{self.RABBIT_HOST}:{self.RABBIT_PORT}/"

    # --- Redis ---
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: Optional[str] = None

    @property
    def redis_url(self) -> str:
        if self.REDIS_PASSWORD:
            return f"rediss://default:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/0"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/0"

    @property
    def celery_result_backend(self) -> str:
        scheme = "rediss" if self.REDIS_PASSWORD and self.REDIS_HOST not in {"localhost", "127.0.0.1", "redis"} else "redis"
        if self.REDIS_PASSWORD:
            return f"{scheme}://default:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/1"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/1"


    # --- Gemini Key
    GEMINI_API_KEY: str


settings = Settings()
