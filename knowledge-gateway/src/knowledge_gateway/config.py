from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "sqlite:///./knowledge_gateway.db"
    app_schema: str = "public"
    vault_root: Path = Path("./vault")
    default_timezone: str = "Asia/Calcutta"

    require_cloudflare_access: bool = False
    allow_cf_bypass_for_local: bool = True
    api_key_pepper: str = "replace-this"

    mcp_server_name: str = "knowledge-gateway"
    mcp_server_version: str = "0.1.0"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    settings = Settings()
    settings.vault_root.mkdir(parents=True, exist_ok=True)
    return settings
