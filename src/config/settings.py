"""
Configuration settings for the Regal POS Backend
Uses pydantic-settings for validation and type safety
"""
from pydantic_settings import BaseSettings
from typing import List, Optional
import os


class Settings(BaseSettings):
    # Application settings
    app_name: str = "Regal POS Backend"
    app_version: str = "1.0.0"
    debug: bool = False

    # Database settings
    database_url: str = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:password@localhost:5432/regal_pos_dev")
    database_pool_size: int = int(os.getenv("DATABASE_POOL_SIZE", "20"))
    database_max_overflow: int = int(os.getenv("DATABASE_MAX_OVERFLOW", "30"))

    # JWT settings - these should be stored securely in production
    access_token_secret_key: str = os.getenv("ACCESS_TOKEN_SECRET_KEY", "")
    refresh_token_secret_key: str = os.getenv("REFRESH_TOKEN_SECRET_KEY", "")
    algorithm: str = os.getenv("ALGORITHM", "HS256")
    access_token_expire_minutes: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15"))
    refresh_token_expire_days: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "30"))

    # Redis settings
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379")

    # CORS settings
    allowed_origins: List[str] = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(",")

    # Security settings
    csrf_enabled: bool = os.getenv("CSRF_ENABLED", "true").lower() == "true"
    secure_cookies: bool = os.getenv("SECURE_COOKIES", "true").lower() == "true"
    session_timeout_hours: int = int(os.getenv("SESSION_TIMEOUT_HOURS", "24"))

    # Rate limiting
    rate_limit_enabled: bool = os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true"
    auth_attempts_limit: int = int(os.getenv("AUTH_ATTEMPTS_LIMIT", "5"))
    auth_attempts_window: int = int(os.getenv("AUTH_ATTEMPTS_WINDOW", "300"))  # 5 minutes

    # API settings
    api_v1_prefix: str = "/api/v1"
    max_upload_size: int = int(os.getenv("MAX_UPLOAD_SIZE", "10485760"))  # 10MB
    default_pagination_limit: int = int(os.getenv("DEFAULT_PAGINATION_LIMIT", "50"))
    max_pagination_limit: int = int(os.getenv("MAX_PAGINATION_LIMIT", "200"))

    # Logging settings
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    log_format: str = os.getenv("LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    # Monitoring settings
    prometheus_enabled: bool = os.getenv("PROMETHEUS_ENABLED", "false").lower() == "true"
    sentry_dsn: Optional[str] = os.getenv("SENTRY_DSN", None)

    model_config = {
        "env_file": ".env",
        "case_sensitive": True,
        "extra": "allow"  # Allow extra fields for compatibility
    }


# Create global settings instance
settings = Settings()


def validate_secrets():
    """
    Validate that required secrets are properly set
    """
    errors = []

    if not settings.access_token_secret_key:
        errors.append("ACCESS_TOKEN_SECRET_KEY is not set")

    if not settings.refresh_token_secret_key:
        errors.append("REFRESH_TOKEN_SECRET_KEY is not set")

    if len(settings.access_token_secret_key) < 32:
        errors.append("ACCESS_TOKEN_SECRET_KEY should be at least 32 characters long")

    if len(settings.refresh_token_secret_key) < 32:
        errors.append("REFRESH_TOKEN_SECRET_KEY should be at least 32 characters long")

    if errors:
        raise ValueError("Configuration errors found:\n" + "\n".join(errors))


# Validate secrets on import
validate_secrets()