"""
RecallVision – Application Configuration
Reads settings from .env (or environment). Never exposes secrets to the frontend.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Google Gemini / Gemma
    gemini_api_key: str = ""

    # Server
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000

    # Video processing
    frames_per_second: int = 1
    max_upload_size_mb: int = 500

    # Derived paths
    @property
    def upload_dir(self) -> Path:
        p = BASE_DIR / "uploads"
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def frames_dir(self) -> Path:
        p = BASE_DIR / "frames"
        p.mkdir(parents=True, exist_ok=True)
        return p


settings = Settings()
