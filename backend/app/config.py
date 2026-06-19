"""Application configuration and config-data loading.

Runtime settings come from environment variables (see ``.env.example``).
Domain configuration (source sets, retailers, market profile, normalization
dictionaries, scoring weights) is loaded from versioned YAML files in
``app/config_data`` so administrators can tune behaviour without code changes.
"""
from __future__ import annotations

import functools
from pathlib import Path
from typing import Any

import yaml
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent
CONFIG_DATA_DIR = BASE_DIR / "config_data"
FIXTURES_DIR = BASE_DIR / "fixtures"


class Settings(BaseSettings):
    """Runtime settings sourced from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    APP_ENV: str = "development"
    PORT: int = 8000
    # Defaults to a local SQLite file so the demo and tests run with zero setup.
    # Point this at PostgreSQL / Supabase for production.
    DATABASE_URL: str = "sqlite:///./hijacking.db"

    SUPABASE_URL: str | None = None
    SUPABASE_SERVICE_ROLE_KEY: str | None = None
    STORAGE_BUCKET: str = "snapshots"
    # Local directory used for raw HTML snapshots when Supabase Storage is not
    # configured.
    STORAGE_DIR: str = "./storage"

    ALLOWED_ORIGINS: str = "*"

    SCAN_TIMEOUT_SECONDS: float = 15.0
    SCAN_MAX_RESPONSE_BYTES: int = 5_000_000
    SCAN_PER_DOMAIN_RATE_PER_MINUTE: int = 20
    PLAYWRIGHT_ENABLED: bool = False
    USER_AGENT: str = "HijackingBot/0.1 (+retail-opportunity-research)"

    LOG_LEVEL: str = "INFO"
    # Optional shared secret. When set, mutating endpoints require X-API-Key.
    API_KEY: str | None = None

    # Discovery mode used when the frontend starts a run (its input has no mode).
    # The Lovable frontend only knows "demo" / "live"; we default backend runs to
    # the seeded "demo" pipeline so the live HTTP integration returns rich data
    # without real source URLs. Set to "replay" or "live" to change this.
    BACKEND_DISCOVERY_MODE: str = "demo"

    @property
    def allowed_origins_list(self) -> list[str]:
        if self.ALLOWED_ORIGINS.strip() == "*":
            return ["*"]
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",") if o.strip()]


@functools.lru_cache
def get_settings() -> Settings:
    return Settings()


def _load_yaml(name: str) -> dict[str, Any]:
    path = CONFIG_DATA_DIR / name
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


@functools.lru_cache
def load_source_sets() -> dict[str, Any]:
    return _load_yaml("source_sets.yaml").get("source_sets", {})


@functools.lru_cache
def load_retailers() -> dict[str, Any]:
    data = _load_yaml("retailers.yaml").get("retailers", [])
    return {r["key"]: r for r in data}


@functools.lru_cache
def load_market_profile() -> dict[str, Any]:
    return _load_yaml("market_profile_ch.yaml")


@functools.lru_cache
def load_normalization() -> dict[str, Any]:
    return _load_yaml("normalization.yaml")


@functools.lru_cache
def load_scoring() -> dict[str, Any]:
    return _load_yaml("scoring.yaml")


def clear_config_cache() -> None:
    """Used by tests / hot-reload to drop cached YAML config."""
    for fn in (
        load_source_sets,
        load_retailers,
        load_market_profile,
        load_normalization,
        load_scoring,
        get_settings,
    ):
        fn.cache_clear()
