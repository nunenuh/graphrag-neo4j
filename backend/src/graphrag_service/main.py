"""
FastAPI application for GraphRAG Service.

Graph RAG over Papers With Code data using Neo4j as a unified
graph + vector store with OpenAI embeddings and LLM.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from loguru import logger

from .core.config import get_settings
from .core.dependencies import close_neo4j_client
from .core.logging import setup_logging
from .middleware.rate_limit import limiter
from .middleware.security_headers import SecurityHeadersMiddleware
from .router import api_router

_DOCS_ENVS = {"development", "local", "staging"}


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Application lifespan — startup and shutdown."""
    settings = get_settings()
    logger.bind(
        environment=settings.APP_ENVIRONMENT,
        debug=settings.APP_DEBUG,
        llm_provider=settings.LLM_PROVIDER,
        llm_model=settings.LLM_MODEL,
        embedding_provider=settings.EMBEDDING_PROVIDER,
        embedding_model=settings.EMBEDDING_MODEL,
        embedding_dim=settings.EMBEDDING_DIM,
        neo4j_uri=settings.NEO4J_URI,
        top_k=settings.TOP_K_SEED_NODES,
        traversal_depth=settings.TRAVERSAL_DEPTH,
    ).info("app.startup")
    yield
    logger.info("app.shutdown")
    close_neo4j_client()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()
    setup_logging()

    show_docs = settings.APP_ENVIRONMENT in _DOCS_ENVS

    app = FastAPI(
        title=settings.APP_NAME,
        description=settings.APP_DESCRIPTION,
        version=settings.APP_VERSION,
        docs_url="/docs" if show_docs else None,
        redoc_url="/redoc" if show_docs else None,
        debug=settings.APP_DEBUG,
        lifespan=lifespan,
    )

    # Security headers (outermost — runs on every response)
    app.add_middleware(SecurityHeadersMiddleware)

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type", "X-API-Key"],
    )

    # Rate limiting
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    app.include_router(api_router, prefix="/api")

    return app


app = create_app()


def main():
    """Main entry point for running the application."""
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "graphrag_service.main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=settings.APP_DEBUG,
    )


def dev():
    """Development entry point with auto-reload."""
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "graphrag_service.main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=True,
    )


if __name__ == "__main__":
    main()
