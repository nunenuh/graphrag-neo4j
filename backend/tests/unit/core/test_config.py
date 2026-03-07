"""Unit tests for core.config."""

import pytest

from graphrag_service.core.config import Settings, get_settings


class TestSettings:
    def test_defaults(self, settings):
        assert settings.APP_NAME == "GraphRAG Service"
        assert settings.APP_PORT == 8005
        assert settings.APP_HOST == "0.0.0.0"

    def test_api_key_from_env(self, settings):
        assert settings.APP_X_API_KEY == "test-api-key"

    def test_neo4j_from_env(self, settings):
        assert settings.NEO4J_URI == "bolt://localhost:7687"
        assert settings.NEO4J_USER == "neo4j"

    def test_allowed_origins_parses_csv(self, monkeypatch, settings):
        monkeypatch.setattr(settings, "ALLOWED_ORIGINS_STR", "http://a.com, http://b.com")
        assert settings.allowed_origins == ["http://a.com", "http://b.com"]

    def test_allowed_origins_empty(self, monkeypatch, settings):
        monkeypatch.setattr(settings, "ALLOWED_ORIGINS_STR", "")
        assert settings.allowed_origins == []

    def test_environment_alias(self, settings):
        assert settings.ENVIRONMENT == settings.APP_ENVIRONMENT

    def test_rag_defaults(self, settings):
        assert settings.TOP_K_SEED_NODES == 5
        assert settings.TRAVERSAL_DEPTH == 2

    def test_embedding_settings_present(self, settings):
        assert settings.EMBEDDING_DIM > 0
        assert settings.EMBEDDING_PROVIDER in ("openai", "google", "ollama", "qwen")
        assert len(settings.EMBEDDING_MODEL) > 0

    def test_llm_settings_present(self, settings):
        assert settings.LLM_PROVIDER in ("openai", "google", "ollama", "qwen")
        assert len(settings.LLM_MODEL) > 0


class TestGetSettings:
    def test_cached(self):
        get_settings.cache_clear()
        s1 = get_settings()
        s2 = get_settings()
        assert s1 is s2
        get_settings.cache_clear()
