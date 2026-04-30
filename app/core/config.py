import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator
from typing import Optional

# Path calculation to the project root
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DOTENV_PATH = BASE_DIR / ".env"

class Settings(BaseSettings):
    """
    Application settings for Gambit Engine.
    Features robust environment variable fallback and validation.
    """
    neo4j_uri: str
    neo4j_username: str
    neo4j_password: str
    redis_url: str
    groq_api_key: str
    gemini_api_key: str

    # Pydantic-settings configuration
    model_config = SettingsConfigDict(
        env_file=DOTENV_PATH if DOTENV_PATH.exists() else None,
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False  # Allows matching NEO4J_URI to neo4j_uri
    )

    @field_validator("redis_url", mode="before")
    @classmethod
    def handle_empty_redis_url(cls, v):
        """
        Forces Pydantic to ignore empty strings from the OS environment
        and fallback to the value in the .env file.
        """
        if v == "" or v is None:
            return None
        return v

    def validate_redis_url(self):
        """Sanity check to prevent using the placeholder or empty URLs."""
        if not self.redis_url or "your_upstash_redis_url_here" in self.redis_url:
            raise ValueError(
                "CRITICAL: Placeholder or empty REDIS_URL detected. "
                "Ensure your .env file contains a valid rediss:// URL."
            )

# Create and validate the settings singleton
settings = Settings()
settings.validate_redis_url()
