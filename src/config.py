from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, Field, ValidationError


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class Settings(BaseModel):
    openai_api_key: str = Field(..., description="API key for OpenAI")
    openai_vision_model: str = Field(
        default="gpt-4o", description="Model used to parse scanned contract images"
    )
    openai_agent_model: str = Field(
        default="gpt-4o-mini",
        description="Model used by the text-only analysis agents",
    )
    langfuse_public_key: str | None = Field(default=None)
    langfuse_secret_key: str | None = Field(default=None)
    langfuse_base_url: str | None = Field(default=None)

    @property
    def langfuse_enabled(self) -> bool:
        return bool(self.langfuse_public_key and self.langfuse_secret_key)


def load_settings() -> Settings:
    load_dotenv(PROJECT_ROOT / ".env")

    try:
        return Settings(
            openai_api_key=os.environ["OPENAI_API_KEY"],
            openai_vision_model=os.getenv("OPENAI_VISION_MODEL", "gpt-4o"),
            openai_agent_model=os.getenv("OPENAI_AGENT_MODEL", "gpt-4o-mini"),
            langfuse_public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
            langfuse_secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
            langfuse_base_url=os.getenv("LANGFUSE_BASE_URL")
            or os.getenv("LANGFUSE_HOST"),
        )
    except KeyError as exc:
        missing_key = exc.args[0]
        raise RuntimeError(
            f"Missing required environment variable: {missing_key}. Check your .env file."
        ) from exc
    except ValidationError as exc:
        raise RuntimeError(f"Invalid environment configuration: {exc}") from exc