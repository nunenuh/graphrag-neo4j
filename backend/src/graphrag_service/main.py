"""
FastAPI application for GraphRAG Service.

Graph RAG over Papers With Code data using Neo4j as a unified
graph + vector store with OpenAI embeddings and LLM.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .core.config import get_settings
from .core.dependencies import close_neo4j_client
from .core.logging import get_logger, setup_logging
from .router import api_router

logger = get_logger(__name__)

_DOCS_ENVS = {"development", "local", "staging"}


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Application lifespan — startup and shutdown."""
    logger.info("Application starting up...")
    yield
    logger.info("Application shutting down...")
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

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type", "X-API-Key"],
    )

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
