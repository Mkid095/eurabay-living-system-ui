"""
Configuration management for EURABAY Living System.
Loads settings from environment variables and .env file.
"""

import os
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator, Field
from functools import lru_cache


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    """

    # Application settings
    APP_NAME: str = "EURABAY Living System"
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # Server settings
    HOST: str = "127.0.0.1"
    PORT: int = 8000

    # Request limits
    MAX_REQUEST_SIZE: int = 10 * 1024 * 1024  # 10MB
    CONNECTION_TIMEOUT: int = 30  # 30 seconds
    READ_TIMEOUT: int = 60  # 60 seconds

    # CORS settings for Next.js frontend
    # Store as string, parse as list
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:3001,http://127.0.0.1:3000,http://127.0.0.1:3001"

    # Trading symbols (volatility indices)
    # Store as string, parse as list
    TRADING_SYMBOLS: str = "V10,V25,V50,V75,V100"

    # MT5 connection settings
    MT5_PATH: str = ""
    MT5_ACCOUNT: int = 0
    MT5_PASSWORD: str = ""
    MT5_SERVER: str = ""

    # Risk management settings
    MAX_RISK_PER_TRADE: float = 0.02  # 2%
    MAX_DAILY_LOSS: float = 0.05  # 5%
    MAX_CONCURRENT_POSITIONS: int = 3
    MIN_RISK_REWARD_RATIO: float = 1.5

    # Trading settings
    TRADING_ENABLED: bool = False
    PAPER_TRADING: bool = True

    # Database settings
    DATABASE_PATH: str = "backend/data/trading.db"

    # Data storage settings
    DATA_DIR: str = "backend/data"
    LOG_DIR: str = "backend/logs"

    # Model settings
    MODEL_DIR: str = "backend/data/models"
    RETRAIN_INTERVAL_DAYS: int = 7

    # WebSocket settings
    WS_HEARTBEAT_INTERVAL: int = 30

    def validate_configuration(self) -> None:
        """
        Validate configuration settings at startup.
        Raises ValueError if configuration is invalid.
        """
        errors = []

        # Validate port range
        if not (1 <= self.PORT <= 65535):
            errors.append(f"Invalid PORT: {self.PORT}. Must be between 1 and 65535.")

        # Validate timeouts
        if self.CONNECTION_TIMEOUT <= 0:
            errors.append(f"CONNECTION_TIMEOUT must be positive, got {self.CONNECTION_TIMEOUT}")
        if self.READ_TIMEOUT <= 0:
            errors.append(f"READ_TIMEOUT must be positive, got {self.READ_TIMEOUT}")

        # Validate risk settings
        if not (0 < self.MAX_RISK_PER_TRADE <= 1):
            errors.append(f"MAX_RISK_PER_TRADE must be between 0 and 1, got {self.MAX_RISK_PER_TRADE}")
        if not (0 < self.MAX_DAILY_LOSS <= 1):
            errors.append(f"MAX_DAILY_LOSS must be between 0 and 1, got {self.MAX_DAILY_LOSS}")
        if self.MAX_CONCURRENT_POSITIONS < 1:
            errors.append(f"MAX_CONCURRENT_POSITIONS must be at least 1, got {self.MAX_CONCURRENT_POSITIONS}")
        if self.MIN_RISK_REWARD_RATIO < 1:
            errors.append(f"MIN_RISK_REWARD_RATIO must be at least 1, got {self.MIN_RISK_REWARD_RATIO}")

        # Validate trading symbols
        symbols = self.parsed_trading_symbols
        if not symbols:
            errors.append("TRADING_SYMBOLS cannot be empty")

        # Validate directories exist or can be created
        for dir_path, dir_name in [
            (self.DATA_DIR, "DATA_DIR"),
            (self.LOG_DIR, "LOG_DIR"),
            (self.MODEL_DIR, "MODEL_DIR"),
        ]:
            try:
                os.makedirs(dir_path, exist_ok=True)
            except Exception as e:
                errors.append(f"Cannot create {dir_name} at {dir_path}: {e}")

        # Raise if any errors
        if errors:
            raise ValueError(f"Configuration validation failed:\n" + "\n".join(f"  - {err}" for err in errors))

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

    @property
    def parsed_allowed_origins(self) -> List[str]:
        """Parse ALLOWED_ORIGINS string into a list."""
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",")]

    @property
    def parsed_trading_symbols(self) -> List[str]:
        """Parse TRADING_SYMBOLS string into a list."""
        return [symbol.strip() for symbol in self.TRADING_SYMBOLS.split(",")]


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.
    """
    return Settings()


# Export settings instance
settings = get_settings()
