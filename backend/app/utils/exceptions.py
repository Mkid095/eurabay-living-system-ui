"""
Custom exception classes for EURABAY Living System.
"""


class TradingSystemException(Exception):
    """Base exception for all trading system errors."""

    def __init__(self, message: str, details: str = "") -> None:
        """
        Initialize trading system exception.

        Args:
            message: Error message
            details: Additional error details
        """
        self.message = message
        self.details = details
        super().__init__(self.message)


class MT5Error(TradingSystemException):
    """Exception raised for MT5-related errors."""

    def __init__(self, message: str, details: str = "") -> None:
        super().__init__(f"MT5 Error: {message}", details)


class DatabaseError(TradingSystemException):
    """Exception raised for database-related errors."""

    def __init__(self, message: str, details: str = "") -> None:
        super().__init__(f"Database Error: {message}", details)


class ModelError(TradingSystemException):
    """Exception raised for ML model-related errors."""

    def __init__(self, message: str, details: str = "") -> None:
        super().__init__(f"Model Error: {message}", details)


class RiskError(TradingSystemException):
    """Exception raised for risk management violations."""

    def __init__(self, message: str, details: str = "") -> None:
        super().__init__(f"Risk Error: {message}", details)


class ConfigurationError(TradingSystemException):
    """Exception raised for configuration-related errors."""

    def __init__(self, message: str, details: str = "") -> None:
        super().__init__(f"Configuration Error: {message}", details)


class ValidationError(TradingSystemException):
    """Exception raised for data validation errors."""

    def __init__(self, message: str, details: str = "") -> None:
        super().__init__(f"Validation Error: {message}", details)
