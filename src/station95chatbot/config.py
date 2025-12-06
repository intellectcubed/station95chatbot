"""Configuration management for the Station 95 chatbot."""

import os
from typing import Literal
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # GroupMe Configuration
    groupme_bot_id: str
    groupme_api_token: str
    groupme_group_id: str

    # AI/LLM Configuration
    ai_provider: Literal["openai", "anthropic"] = "openai"
    ai_mode: Literal["simple", "agentic"] = "simple"  # simple = single LLM call, agentic = multi-step workflow
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None

    # Calendar Service Configuration
    calendar_service_url: str = "https://dyumfg6b2e.execute-api.us-east-1.amazonaws.com/v1"

    # Bot Configuration
    webhook_port: int = 8080
    confidence_threshold: int = 70
    log_level: str = "INFO"

    # Roster Configuration
    roster_file_path: str = "data/roster.json"

    def validate_ai_config(self) -> None:
        """Validate that the correct API key is set for the chosen provider."""
        if self.ai_provider == "openai" and not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY must be set when using OpenAI provider")
        if self.ai_provider == "anthropic" and not self.anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY must be set when using Anthropic provider")


# Global settings instance
settings = Settings()
