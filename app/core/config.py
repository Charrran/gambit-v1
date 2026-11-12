from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator

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
    # LLM routes, tried in order, once each ("provider:model", comma separated).
    # Per-turn text is the frequent, latency-critical call: fastest and cheapest model first.
    llm_turn_routes: str = "groq:qwen/qwen3.8-27b,gemini:gemini-3.1-flash-lite,groq:openai/gpt-oss-20b"
    # Headlines, aftermath and the epilogue are rare: spend Gemini's larger allowance first.
    llm_text_routes: str = "gemini:gemini-3.1-flash-lite,groq:openai/gpt-oss-20b,groq:qwen/qwen3.8-27b"
    # Narration variants kept per scene situation in the Neo4j cache before the LLM is no longer called.
    narration_variants: int = 2

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
