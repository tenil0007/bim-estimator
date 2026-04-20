"""
Application Configuration Module
---------------------------------
Centralized configuration management using Pydantic Settings.
Loads from environment variables and .env files.
"""

import os
from pathlib import Path
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    app_name: str = "BIM Cost & Time Estimator"
    app_version: str = "1.0.0"
    debug: bool = True

    # Server
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000
    backend_cors_origins: str = "http://localhost:5173,http://localhost:3000"

    # Database
    database_url: str = "sqlite:///./data/bim_estimator.db"

    # File Storage
    upload_dir: str = "./data/uploads"
    max_upload_size_mb: int = 500

    # ML Models
    model_dir: str = "./ml/saved_models"
    cost_model_type: str = "xgboost"  # "xgboost" or "random_forest"
    time_model_type: str = "xgboost"

    # Material reference rates (FX blend baseline; see material_market_rates)
    material_rate_reference_usd_inr: float = 83.0

    # Logging
    log_level: str = "INFO"
    log_format: str = "json"

    @property
    def cors_origins(self) -> list[str]:
        if self.backend_cors_origins.strip() == "*":
            return ["*"]
        return [origin.strip() for origin in self.backend_cors_origins.split(",")]

    @property
    def base_dir(self) -> Path:
        return Path(__file__).resolve().parent.parent

    @property
    def data_dir(self) -> Path:
        return self.base_dir / "data"

    @property
    def upload_path(self) -> Path:
        path = self.base_dir / self.upload_dir
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def model_path(self) -> Path:
        path = self.base_dir / self.model_dir
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def extracted_data_path(self) -> Path:
        path = self.data_dir / "extracted"
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def processed_data_path(self) -> Path:
        path = self.data_dir / "processed"
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def reports_path(self) -> Path:
        path = self.data_dir / "reports"
        path.mkdir(parents=True, exist_ok=True)
        return path

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Cached settings instance - singleton pattern."""
    return Settings()
