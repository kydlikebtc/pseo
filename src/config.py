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
    # When running inside Manus, OPENAI_API_KEY and OPENAI_BASE_URL are auto-injected.
    # LLM_MODEL accepts any model name string — no validation is applied.
    openai_api_key: str = Field(default="")
    llm_model: str = Field(default="gpt-4.1-mini")  # Any model name accepted

    # Google APIs
    google_service_account_file: str = Field(default="config/google_service_account.json")

    # Competitor Monitoring
    # SimilarWeb: auto-available inside Manus via built-in ApiClient (no key needed).
    #             Set SIMILARWEB_API_KEY only when running outside Manus.
    similarweb_api_key: str = Field(default="")

    # Semrush: free tier (10 req/day) is sufficient for weekly backlink scans.
    #          Sign up at https://www.semrush.com to get a free API key.
    semrush_api_key: str = Field(default="")

    # Notifications
    feishu_webhook_url: str = Field(default="")

    # Site
    site_url: str = Field(default="https://example.com")

    # pSEO Engine
    pseo_batch_size: int = Field(default=10)
    pseo_min_word_count: int = Field(default=800)


settings = Settings()
