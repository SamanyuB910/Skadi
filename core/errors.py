"""Custom exception classes for Skadi system."""
from typing import Optional, Dict, Any


class SkadiException(Exception):
    """Base exception for all Skadi errors."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class KillSwitchEngagedException(SkadiException):
    """Raised when global kill switch is engaged."""
    pass


class GuardrailViolationException(SkadiException):
    """Raised when an action would violate safety guardrails."""
    pass


class RateLimitException(SkadiException):
    """Raised when write rate limit is exceeded."""
    pass


class IMSNotTrainedException(SkadiException):
    """Raised when IMS model hasn't been trained yet."""
    pass


class ModelNotReadyException(SkadiException):
    """Raised when required ML model is not available."""
    pass


class InvalidActionException(SkadiException):
    """Raised when action parameters are invalid."""
    pass


class TelemetryValidationException(SkadiException):
    """Raised when telemetry data fails validation."""
    pass


class ScenarioException(SkadiException):
    """Raised when demo scenario encounters an error."""
    pass
