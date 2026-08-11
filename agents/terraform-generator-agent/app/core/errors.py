class GeneratorError(Exception):
    """Base error for controlled generation failures."""


class NeedsInputError(GeneratorError):
    """Raised when generation needs information that cannot be inferred safely."""


class UnsupportedArchitectureError(GeneratorError):
    """Raised when the input contains resources outside the supported registry."""
