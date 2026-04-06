"""
Central configuration management using pydantic-settings.
All settings are loaded from environment variables or .env file.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Database
    database_url: str = Field(default="sqlite:///./pseo.db")

    # LLM
    openai_api_key: str = Field(default="")
    llm_model: str = Field(default="gpt-5.4-mini")  # Any model name accepted, set via LLM_MODEL env var

    # Google APIs
    google_service_account_file: str = Field(default="config/google_service_account.json")

    # Ahrefs
    ahrefs_api_key: str = Field(default="")

    # Notifications
    feishu_webhook_url: str = Field(default="")

    # Site
    site_url: str = Field(default="https://example.com")

    # pSEO Engine
    pseo_batch_size: int = Field(default=10)
    pseo_min_word_count: int = Field(default=800)


settings = Settings()
