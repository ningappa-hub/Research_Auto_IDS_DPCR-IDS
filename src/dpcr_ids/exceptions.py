"""Project-specific exceptions."""


class DPCRIDSError(Exception):
    """Base project error."""


class ConfigurationError(DPCRIDSError):
    """Raised when configuration is invalid or missing required fields."""


class DataValidationError(DPCRIDSError):
    """Raised when input data fails quality or contract checks."""


class DependencyUnavailableError(DPCRIDSError):
    """Raised when optional ML dependencies are not installed."""
