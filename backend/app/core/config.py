from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Pipeline Doctor"
    environment: str = "development"
    api_token: str = "change-me"
    github_webhook_secret: str = ""
    github_token: str = ""
    github_api_url: str = "https://api.github.com"
    database_url: str = "sqlite:///./pipeline_doctor.db"
    ai_provider: str = "local"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1"
    cors_origins: str = "http://localhost:5173"
    max_log_chars: int = 60000


@lru_cache
def get_settings() -> Settings:
    return Settings()
