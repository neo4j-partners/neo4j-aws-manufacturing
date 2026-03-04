"""Configuration: load Neo4j and OpenAI credentials from .env or CONFIG.txt."""

from __future__ import annotations

from pathlib import Path

from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_PKG_DIR = Path(__file__).resolve().parent
_ENV_FILE = _PKG_DIR.parent.parent / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_ENV_FILE,
        env_file_encoding="utf-8",
    )

    neo4j_uri: str
    neo4j_username: str = "neo4j"
    neo4j_password: SecretStr
    openai_api_key: SecretStr

    @model_validator(mode="after")
    def _check_uri_scheme(self) -> Settings:
        valid = ("neo4j://", "neo4j+s://", "neo4j+ssc://", "bolt://", "bolt+s://", "bolt+ssc://")
        if not self.neo4j_uri.startswith(valid):
            raise ValueError(f"NEO4J_URI must start with a valid scheme, got: {self.neo4j_uri}")
        return self
