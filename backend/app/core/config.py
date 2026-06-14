import os
from dataclasses import dataclass
from functools import lru_cache

DEFAULT_MAX_UPLOAD_BYTES = 104_857_600


@dataclass(frozen=True)
class Settings:
    app_name: str
    database_url: str
    max_upload_bytes: int
    default_retry_limit: int
    worker_poll_seconds: float


@lru_cache
def get_settings() -> Settings:
    return Settings(
        app_name=os.getenv("APP_NAME", "AI Response Threat Evaluator"),
        database_url=os.getenv(
            "DATABASE_URL",
            os.getenv("TEST_DATABASE_URL", "sqlite+pysqlite:///:memory:"),
        ),
        max_upload_bytes=int(os.getenv("MAX_UPLOAD_BYTES", str(DEFAULT_MAX_UPLOAD_BYTES))),
        default_retry_limit=int(os.getenv("DEFAULT_RETRY_LIMIT", "2")),
        worker_poll_seconds=float(os.getenv("WORKER_POLL_SECONDS", "5")),
    )
