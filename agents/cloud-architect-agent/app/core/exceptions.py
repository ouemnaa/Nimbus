class AppError(Exception):
    """Base class for application errors."""
    pass

class LLMProviderError(AppError):
    """Raised when an LLM provider fails."""
    pass

class ValidationError(AppError):
    """Raised when architecture validation fails."""
    pass

class ConfigurationError(AppError):
    """Raised when environment configuration is invalid."""
    pass
