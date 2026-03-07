"""Unit tests for core.auth."""

import pytest
from fastapi import HTTPException

from graphrag_service.core.auth import get_api_key


class TestGetApiKey:
    @pytest.mark.asyncio
    async def test_valid_key(self, settings):
        result = await get_api_key("test-api-key")
        assert result == "test-api-key"

    @pytest.mark.asyncio
    async def test_missing_key_raises_403(self, settings):
        with pytest.raises(HTTPException) as exc_info:
            await get_api_key(None)
        assert exc_info.value.status_code == 403
        assert "No API key" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_invalid_key_raises_403(self, settings):
        with pytest.raises(HTTPException) as exc_info:
            await get_api_key("wrong-key")
        assert exc_info.value.status_code == 403
        assert "Invalid API key" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_empty_string_raises_403(self, settings):
        with pytest.raises(HTTPException) as exc_info:
            await get_api_key("")
        assert exc_info.value.status_code == 403
