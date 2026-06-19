import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="JARVIS_", env_file=ROOT / ".env", extra="ignore")

    host: str = "127.0.0.1"
    port: int = 8787
    data_dir: Path = ROOT / "data"
    workspace_dir: Path = ROOT
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "llama3.2:3b"
    ollama_vision_model: str = "moondream"
    agent_name: str = "William Agent"
    openclaw_gateway_url: str = "http://127.0.0.1:18789"
    macos_helper_url: str = "http://127.0.0.1:8788"
    netatmo_client_id: str = ""
    netatmo_client_secret: str = ""
    public_webhook_url: str = ""
    cursor_model: str = "composer-2.5"
    cursor_api_key: str = ""
    timezone: str = "Europe/Amsterdam"
    briefing_hour: int = 8

    def resolved_cursor_api_key(self) -> str:
        return self.cursor_api_key or os.environ.get("CURSOR_API_KEY", "")


settings = Settings()
settings.data_dir.mkdir(parents=True, exist_ok=True)
