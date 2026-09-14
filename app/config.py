from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    ADMIN_SECRET: str = "change-me-admin-secret"
    JWT_SECRET: str = "change-me-jwt-secret"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRY_SECONDS: int = 3600
    DEFAULT_QUOTA_LIMIT: int = 1000
    DEFAULT_QUOTA_PERIOD_SECONDS: int = 86400
    DATABASE_URL: str = "sqlite:///./data.db"


settings = Settings()
