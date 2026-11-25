"""Centralized configuration loader using Pydantic Settings."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import List, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env file."""

    model_config = SettingsConfigDict(
        env_file=[str(PROJECT_ROOT / ".env"), ".env"],
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # 1. Application & Security
    APP_NAME: str = "Financial Markets Intelligence Platform"
    APP_ENV: str = "development"
    APP_DEBUG: bool = False
    API_V1_STR: str = "/api/v1"
    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_PORT: int = 8000
    FRONTEND_URL: str = "http://localhost:3000"

    SECRET_KEY: str = Field(
        default="fmip-dev-cryptographic-secret-key-change-in-production-64bytes-long",
        min_length=16,
    )
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    JWT_ALGORITHM: str = "HS256"

    INITIAL_ADMIN_EMAIL: str = "admin@sohcahtoaholdings.com"
    INITIAL_ADMIN_PASSWORD: str = "SohCahToa@Admin2026!"
    INITIAL_ADMIN_ROLE: str = "EXECUTIVE_ADMIN"

    RATE_LIMIT_PER_MINUTE: int = 120
    AGENT_TRIGGER_RATE_LIMIT_PER_HOUR: int = 20

    # 2. Database & Redis
    POSTGRES_USER: str = "fmip_user"
    POSTGRES_PASSWORD: str = "fmip_dev_password"
    POSTGRES_DB: str = "fmip_intelligence"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    DATABASE_URL: Optional[str] = None

    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = ""
    REDIS_URL: str = "redis://localhost:6379/0"

    # 3. AI & Multi-Agent Orchestration (Google Gemini API)
    GEMINI_API_KEY: str = ""
    GEMINI_PRIMARY_MODEL: str = "gemini-2.5-pro"
    GEMINI_FAST_MODEL: str = "gemini-2.5-flash"
    GEMINI_EMBEDDING_MODEL: str = "models/text-embedding-004"
    GEMINI_TEMPERATURE: float = 0.1
    GEMINI_MAX_OUTPUT_TOKENS: int = 8192

    # 4. Financial Data & Research Providers
    TAVILY_API_KEY: str = ""
    GOOGLE_SEARCH_API_KEY: str = ""
    GOOGLE_SEARCH_ENGINE_ID: str = ""
    FMP_API_KEY: str = ""
    ALPHA_VANTAGE_API_KEY: str = ""
    FRED_API_KEY: str = ""

    CBN_BASE_URL: str = "https://www.cbn.gov.ng"
    NGX_BASE_URL: str = "https://ngxgroup.com"
    FMDQ_BASE_URL: str = "https://fmdqgroup.com"
    DMO_BASE_URL: str = "https://www.dmo.gov.ng"
    NBS_BASE_URL: str = "https://nigerianstat.gov.ng"
    SEC_NIGERIA_BASE_URL: str = "https://sec.gov.ng"
    PENCOM_BASE_URL: str = "https://www.pencom.gov.ng"
    NAICOM_BASE_URL: str = "https://naicom.gov.ng"

    DATA_PROVIDER_TIMEOUT_SECONDS: int = 20
    DATA_PROVIDER_MAX_RETRIES: int = 3
    DATA_PROVIDER_USER_AGENT: str = (
        "FMIP-Institutional-Research-Engine/1.0 (+https://sohcahtoaholdings.com)"
    )

    # 5. Reporting, Google Drive Archiving & Gmail Delivery
    REPORT_STORAGE_DIR: str = str(PROJECT_ROOT / "storage" / "reports")
    DEFAULT_REPORT_DAY_OF_WEEK: str = "FRI"
    DEFAULT_REPORT_TIME_WAT: str = "16:30"
    DEFAULT_TIMEZONE: str = "Africa/Lagos"

    GOOGLE_DRIVE_ENABLED: bool = False
    GOOGLE_APPLICATION_CREDENTIALS: str = "./secrets/google_service_account.json"
    GOOGLE_DRIVE_REPORTS_FOLDER_ID: str = ""

    EMAIL_DELIVERY_ENABLED: bool = False
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USE_TLS: bool = True
    SMTP_USERNAME: str = ""
    SMTP_APP_PASSWORD: str = ""
    EMAIL_FROM_ADDRESS: str = "research-desk@sohcahtoaholdings.com"
    EMAIL_FROM_NAME: str = "SohCahToa Financial Markets Intelligence Desk"
    WEEKLY_REPORT_RECIPIENTS: str = "exco@sohcahtoaholdings.com,cio@sohcahtoaholdings.com"

    # 6. n8n Automation
    N8N_WEBHOOK_SHARED_SECRET: str = "fmip-n8n-shared-secret"

    @property
    def effective_database_url(self) -> str:
        """Resolve effective SQLAlchemy database URL."""
        if self.DATABASE_URL and "CHANGE_ME" not in self.DATABASE_URL:
            return self.DATABASE_URL
        pwd = (
            "fmip_dev_password"
            if "CHANGE_ME" in self.POSTGRES_PASSWORD
            else self.POSTGRES_PASSWORD
        )
        return (
            f"postgresql+psycopg://{self.POSTGRES_USER}:{pwd}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def recipient_list(self) -> List[str]:
        """Parse comma-separated report recipients into a clean list."""
        return [
            email.strip()
            for email in self.WEEKLY_REPORT_RECIPIENTS.split(",")
            if email.strip()
        ]


@lru_cache
def get_settings() -> Settings:
    """Return cached singleton Settings instance."""
    return Settings()


settings = get_settings()
