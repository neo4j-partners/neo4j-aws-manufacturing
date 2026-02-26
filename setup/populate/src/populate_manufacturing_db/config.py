"""Configuration: load Neo4j and OpenAI credentials from .env and resolve data directory."""

from __future__ import annotations

from pathlib import Path
from pydantic import DirectoryPath, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolved once at import time — stable regardless of cwd.
_PKG_DIR = Path(__file__).resolve().parent
_ENV_FILE = _PKG_DIR.parent.parent / ".env"
_CONFIG_TXT = _PKG_DIR.parent.parent.parent.parent / "CONFIG.txt"
_DATA_DIR = _PKG_DIR.parent.parent.parent.parent / "TransformedData"


def _find_env_file() -> Path:
    """Return .env if it exists, otherwise fall back to repo-root CONFIG.txt."""
    if _ENV_FILE.is_file():
        return _ENV_FILE
    if _CONFIG_TXT.is_file():
        return _CONFIG_TXT
    return _ENV_FILE  # pydantic will just skip it if missing


class Settings(BaseSettings):
    """Neo4j connection and OpenAI settings loaded from .env."""

    model_config = SettingsConfigDict(
        env_file=_find_env_file(),
        env_file_encoding="utf-8",
    )

    neo4j_uri: str
    neo4j_username: str = "neo4j"
    neo4j_password: SecretStr

    data_dir: DirectoryPath = _DATA_DIR  # type: ignore[assignment]

    # OpenAI — used during the embedding phase of `load`.
    openai_api_key: SecretStr

    # Number of rows to show per section in the `samples` command.
    sample_size: int = 10

    @model_validator(mode="after")
    def _check_uri_scheme(self) -> Settings:
        valid = ("neo4j://", "neo4j+s://", "neo4j+ssc://", "bolt://", "bolt+s://", "bolt+ssc://")
        if not self.neo4j_uri.startswith(valid):
            raise ValueError(
                f"NEO4J_URI must start with a valid scheme (neo4j+s://, bolt+s://, etc.), "
                f"got: {self.neo4j_uri}"
            )
        return self
