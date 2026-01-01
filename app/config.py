"""Configuration management for A2A Guestbook application."""

import os
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    """Application configuration loaded from environment variables."""

    # AWS Configuration (Required)
    aws_region: str
    dynamodb_table_name: str

    # API Keys (injected from K8s Secret via ESO)
    api_keys: str  # JSON array of API keys, e.g., '["key1","key2"]'

    # Application Configuration (Optional with defaults)
    rate_limit_per_minute: int = 10
    log_level: str = "INFO"
    port: int = 8000

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    def validate_config(self) -> None:
        """Validate configuration values."""
        # Validate log level
        valid_log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if self.log_level.upper() not in valid_log_levels:
            raise ValueError(
                f"Invalid LOG_LEVEL: {self.log_level}. "
                f"Must be one of: {', '.join(valid_log_levels)}"
            )

        # Validate rate limit
        if self.rate_limit_per_minute <= 0:
            raise ValueError(
                f"RATE_LIMIT_PER_MINUTE must be positive, got: {self.rate_limit_per_minute}"
            )

        # Validate port
        if not (1 <= self.port <= 65535):
            raise ValueError(
                f"PORT must be between 1 and 65535, got: {self.port}"
            )



# Global configuration instance
config = Config()

# Validate configuration on module import
config.validate_config()
