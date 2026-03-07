"""Unit tests for shared.exceptions."""

import pytest

from graphrag_service.shared.exceptions import (
    BaseServiceException,
    LLMException,
    Neo4jConnectionException,
    RepositoryException,
    ServiceException,
    ValidationException,
)


class TestExceptionHierarchy:
    def test_base_service_exception(self):
        exc = BaseServiceException("test")
        assert str(exc) == "test"
        assert exc.message == "test"

    def test_default_messages(self):
        assert ValidationException().message == "Validation error"
        assert RepositoryException().message == "Repository error"
        assert ServiceException().message == "Service error"
        assert Neo4jConnectionException().message == "Neo4j connection error"
        assert LLMException().message == "LLM provider error"

    def test_inheritance(self):
        assert issubclass(RepositoryException, BaseServiceException)
        assert issubclass(ServiceException, BaseServiceException)
        assert issubclass(Neo4jConnectionException, RepositoryException)
        assert issubclass(LLMException, ServiceException)
        assert issubclass(ValidationException, BaseServiceException)

    def test_custom_message(self):
        exc = RepositoryException("custom error")
        assert exc.message == "custom error"
        assert str(exc) == "custom error"

    def test_openai_alias(self):
        from graphrag_service.shared.exceptions import OpenAIException
        assert OpenAIException is LLMException
