"""Configuration: load Neo4j and Bedrock credentials from .env."""

from __future__ import annotations

from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_PKG_DIR = Path(__file__).resolve().parent
# src/graphrag_validator -> src -> solutions_bedrock
_ENV_FILE = _PKG_DIR.parent.parent / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    neo4j_uri: str
    neo4j_username: str = "neo4j"
    neo4j_password: str
    model_id: str = "global.anthropic.claude-sonnet-4-5-20250929-v1:0"
    embedding_model_id: str = "amazon.titan-embed-text-v2:0"
    region: str = "us-west-2"

    @model_validator(mode="after")
    def _check_uri_scheme(self) -> Settings:
        valid = ("neo4j://", "neo4j+s://", "neo4j+ssc://", "bolt://", "bolt+s://", "bolt+ssc://")
        if not self.neo4j_uri.startswith(valid):
            raise ValueError(f"NEO4J_URI must start with a valid scheme, got: {self.neo4j_uri}")
        return self
