from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    app_name: str = "OrientedDetection CAM"
    app_host: str = "127.0.0.1"
    app_port: int = 8000
    model_path: Path = PROJECT_ROOT / "weights" / "best.pt"
    model_device: str = "cpu"
    model_image_size: int = 640
    model_confidence: float = 0.25
    model_iou: float = 0.45
    artifacts_dir: Path = PROJECT_ROOT / "artifacts"
    dataset_config: Path = PROJECT_ROOT / "datasets" / "dota_ship" / "dota_ship.yaml"
    frontend_origin: str = "http://localhost:5190"

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    def ensure_directories(self) -> None:
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        (self.artifacts_dir / "uploads").mkdir(exist_ok=True)
        (self.artifacts_dir / "inferences").mkdir(exist_ok=True)
        (self.artifacts_dir / "evaluations").mkdir(exist_ok=True)
        (self.artifacts_dir / "cams").mkdir(exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.ensure_directories()
    return settings
