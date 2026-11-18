"""Application settings loaded from environment / .env file."""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = BACKEND_ROOT.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=[REPO_ROOT / ".env", BACKEND_ROOT / ".env"],
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ---- LLM --------------------------------------------------------------
    # Any endpoint speaking the OpenAI protocol. Changing model is configuration.
    llm_base_url: str = ""
    llm_api_key: str = ""
    llm_chat_model: str = "gemini-3.5-flash-lite"
    llm_fallback_model: str = ""
    llm_timeout_seconds: float = 25.0

    # ---- Data paths ---------------------------------------------------------
    data_dir: Path = REPO_ROOT / "data"
    build_db_path: Path = REPO_ROOT / "data" / "platform.build.duckdb"
    duckdb_path: Path = REPO_ROOT / "data" / "platform.duckdb"
    duckdb_memory_limit: str = "200MB"
    duckdb_threads: int = 1

    # ---- Abuse controls (anonymous endpoints) -------------------------------
    orb_rate_limit_per_ip: int = 20
    orb_rate_limit_global: int = 300
    orb_rate_limit_window_seconds: float = 300.0
    orb_max_message_chars: int = 2000
    orb_max_context_chars: int = 8000

    # The operator's token: resets the demo and lifts the rate limits for a live
    # walkthrough. Open demo: any visitor may use the work orders, acting as one
    # of the demo roles, under a per-address limit; the rules still refuse, and
    # the working copy returns to the build on every cold start.
    demo_write_token: str = ""
    public_writes: bool = True
    write_rate_limit_per_ip: int = 120
    write_rate_limit_global: int = 1500

    git_sha: str = ""
    cors_origins: str = "http://localhost:5271"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def llm_key(self) -> str:
        # Container Apps cannot hold an empty secret, so "unset" arrives as a space.
        return self.llm_api_key.strip()


settings = Settings()
