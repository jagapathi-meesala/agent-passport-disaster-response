"""
Application Settings model.

Loads runtime environment configuration cleanly using Pydantic BaseModel and os.getenv without
hardcoding credentials, keys, endpoints, or default values.
"""

import os
from typing import Optional
from pydantic import BaseModel


def _parse_int(val: Optional[str]) -> Optional[int]:
    return int(val) if val is not None and val.strip() != "" else None


def _parse_float(val: Optional[str]) -> Optional[float]:
    return float(val) if val is not None and val.strip() != "" else None


class Settings(BaseModel):
    """Configuration loader for DisasterResponseAgent."""
    environment: Optional[str] = os.getenv("ENVIRONMENT")
    log_level: Optional[str] = os.getenv("LOG_LEVEL")

    api_host: Optional[str] = os.getenv("API_HOST")
    api_port: Optional[int] = _parse_int(os.getenv("API_PORT"))

    agent_passport_id: Optional[str] = os.getenv("AGENT_PASSPORT_ID")
    agent_issuer_public_key: Optional[str] = os.getenv("AGENT_ISSUER_PUBLIC_KEY")
    passport_file_path: Optional[str] = os.getenv("PASSPORT_FILE_PATH")

    model_provider: Optional[str] = os.getenv("MODEL_PROVIDER")
    model_endpoint_url: Optional[str] = os.getenv("MODEL_ENDPOINT_URL")
    model_api_key: Optional[str] = os.getenv("MODEL_API_KEY")

    weather_service_url: Optional[str] = os.getenv("WEATHER_SERVICE_URL")
    weather_api_key: Optional[str] = os.getenv("WEATHER_API_KEY")
    weather_timeout_seconds: Optional[float] = _parse_float(os.getenv("WEATHER_TIMEOUT_SECONDS"))

    resource_service_url: Optional[str] = os.getenv("RESOURCE_SERVICE_URL")
    resource_api_key: Optional[str] = os.getenv("RESOURCE_API_KEY")
    resource_timeout_seconds: Optional[float] = _parse_float(os.getenv("RESOURCE_TIMEOUT_SECONDS"))


def get_settings() -> Settings:
    """Instantiate and return configuration settings."""
    return Settings()

