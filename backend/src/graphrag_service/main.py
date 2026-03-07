"""
FastAPI application for GraphRAG Service.

Graph RAG over Papers With Code data using Neo4j as a unified
graph + vector store with OpenAI embeddings and LLM.
"""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .core.config import get_settings
from .core.dependencies import close_neo4j_client
from .core.logging import setup_logging
from .router import api_router

logger = logging.getLogger(__name__)


def get_docs_path():
    """Get docs path based on environment."""
    settings = get_settings()
    if settings.APP_ENVIRONMENT in ["development", "local", "staging"]:
        return "/docs"
    return None


def get_redoc_path():
    """Get redoc path based on environment."""
    settings = get_settings()
    if settings.APP_ENVIRONMENT in ["development", "local", "staging"]:
        return "/redoc"
    return None


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()
    setup_logging()

    app = FastAPI(
        title=settings.APP_NAME,
        description=settings.APP_DESCRIPTION,
        version=settings.APP_VERSION,
        docs_url=get_docs_path(),
        redoc_url=get_redoc_path(),
        debug=settings.APP_DEBUG,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router, prefix="/api")

    return app


app = create_app()


@app.on_event("startup")
async def startup_event():
    """Handle application startup."""
    logger.info("Application starting up...")
    logger.info("Application startup complete")


@app.on_event("shutdown")
async def shutdown_event():
    """Handle application shutdown."""
    logger.info("Application shutting down...")
    close_neo4j_client()
    logger.info("Application shutdown complete")


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
