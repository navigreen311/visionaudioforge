from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "VisionAudioForge"
    APP_ENV: str = "development"
    DEBUG: bool = True
    SECRET_KEY: str = "change-me"

    # Database
    POSTGRES_HOST: str = "db"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "visionaudio"
    POSTGRES_PASSWORD: str = "change-me-db-password"
    POSTGRES_DB: str = "visionaudioforge"

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    # Redis
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = ""

    @property
    def REDIS_URL(self) -> str:
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/0"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/0"

    # JWT
    JWT_SECRET_KEY: str = "change-me-jwt-secret"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_MINUTES: int = 60

    # Auth enforcement (WS-A / trust boundary)
    # AUTH_REQUIRED gates the app-level AuthenticationMiddleware. It defaults to
    # True so a request without a valid identity is rejected everywhere; opting
    # out must be a deliberate act (env var / dependency override), never a
    # side effect of forgetting a decorator on route #58.
    AUTH_REQUIRED: bool = True
    # When True the global exception handler echoes the exception text and
    # traceback to the caller. Defaults to False: 500 bodies leak stack frames,
    # SQL, and file paths. Independent of DEBUG on purpose.
    DEBUG_ERRORS: bool = False
    # Persist an audit_logs row per request. On by default — the README makes a
    # compliance claim about it. Test runs turn it off so they do not queue a
    # database write per assertion.
    AUDIT_ENABLED: bool = True

    # MinIO
    MINIO_ENDPOINT: str = "minio:9000"
    MINIO_ACCESS_KEY: str = "minioaccess"
    MINIO_SECRET_KEY: str = "miniosecret"
    MINIO_BUCKET: str = "visionaudioforge"

    # Celery
    CELERY_BROKER_URL: str = "redis://redis:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://redis:6379/1"

    # AI
    TORCH_DEVICE: str = "cpu"
    ANTHROPIC_API_KEY: str = ""

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
