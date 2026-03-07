"""Custom exception classes for the GraphRAG service."""

from typing import Any, Dict, Optional

from fastapi import HTTPException


class BaseServiceException(Exception):
    """Base exception class for the application."""

    def __init__(self, message: str = "An error occurred") -> None:
        self.message = message
        super().__init__(self.message)


class ValidationException(BaseServiceException):
    """Exception raised for validation errors."""

    def __init__(self, message: str = "Validation error") -> None:
        super().__init__(message)


class RepositoryException(BaseServiceException):
    """Exception raised for repository/database errors."""

    def __init__(self, message: str = "Repository error") -> None:
        super().__init__(message)


class ServiceException(BaseServiceException):
    """Exception raised for service-level errors."""

    def __init__(self, message: str = "Service error") -> None:
        super().__init__(message)


class Neo4jConnectionException(RepositoryException):
    """Exception raised when Neo4j connection fails."""

    def __init__(self, message: str = "Neo4j connection error") -> None:
        super().__init__(message)


class LLMException(ServiceException):
    """Exception raised for LLM provider errors."""

    def __init__(self, message: str = "LLM provider error") -> None:
        super().__init__(message)


# Backwards compatibility alias
OpenAIException = LLMException


class BaseHTTPException(HTTPException):
    """Base HTTP exception for the microservice."""

    def __init__(
        self,
        status_code: int,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ):
        super().__init__(status_code=status_code, detail=message, headers=headers)
        self.message = message
        self.details = details or {}
