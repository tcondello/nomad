import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Fireworks Configuration
    fireworks_api_key: Optional[str] = None
    fireworks_model: str = "accounts/fireworks/models/llama-v3p3-70b-instruct"
    fireworks_temperature: float = 0.2

    # Obsidian Vault Configuration
    obsidian_vault_path: Optional[str] = None

    # Server Configuration
    nomad_host: str = "127.0.0.1"
    nomad_port: int = 8765
    log_level: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    def get_vault_path(self) -> Optional[Path]:
        if self.obsidian_vault_path:
            p = Path(self.obsidian_vault_path).expanduser().resolve()
            if p.is_dir():
                return p
        return None


settings = Settings()
