"""
Application configuration using Pydantic Settings v2
Supports environment variables and .env files
"""
from pathlib import Path
from typing import Optional, List
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable support"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # App Info
    app_name: str = "Crack Detection System"
    app_version: str = "2.0.0"
    api_prefix: str = "/api/v1"
    debug: bool = False

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    # CORS
    cors_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:5173"]
    )

    # Database
    database_url: str = "sqlite+aiosqlite:///./crack_detection.db"

    # File Storage
    upload_dir: Path = Path("./uploads")
    output_dir: Path = Path("./outputs")
    max_upload_size: int = 100 * 1024 * 1024  # 100MB

    # ML Models
    default_crack_model: str = "/media/dev/Data/aihub_building_defect/workspace/yolov8s_crack_seg4/weights/best.pt"
    default_det_model: str = "/media/dev/Data/aihub_building_defect/workspace/merged_unified6_a10012/weights/best.pt"

    # Default Inference Parameters
    default_imgsz: int = 1024
    default_crack_conf: float = 0.25
    default_det_conf: float = 0.35
    default_mm_per_pixel: float = 1.0
    default_min_box_px: int = 40
    default_min_mask_area_px: int = 250
    default_topk_base: int = 5
    default_topk_max: int = 7
    default_high_severity_th: float = 5000.0

    # Security (optional - for future auth)
    secret_key: str = "your-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7  # 7 days

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Create directories
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)


# Global settings instance
settings = Settings()
