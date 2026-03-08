"""
Logging configuration using Loguru.

Dev format (colored, aligned):
  08:03:18 INFO  rag.handler          | rag.request              question="How does..."
  08:03:20 INFO  graph.rag_pipeline   | rag_step.done            step=embed duration_ms=1025.8

Production format:
  JSON lines (structured, machine-readable)
"""

import logging
import sys

from loguru import logger

from .config import get_settings

# Third-party loggers to suppress
_NOISY_LOGGERS = (
    "uvicorn",
    "uvicorn.access",
    "uvicorn.error",
    "fastapi",
    "neo4j",
    "httpx",
    "httpcore",
    "openai",
    "langchain",
    "langchain_core",
    "langgraph",
    "neomodel",
    "watchfiles",
    "watchfiles.main",
)

# Module path shortening
_SKIP_PARTS = {"graphrag_service", "modules", "library", "apiv1", "core", "dbase"}


def _shorten_name(name: str) -> str:
    """graphrag_service.modules.rag.apiv1.handler -> rag.handler"""
    parts = name.split(".")
    return ".".join(p for p in parts if p not in _SKIP_PARTS) or name


def _dev_format(record: dict) -> str:
    """Custom dev format: compact, aligned, colored."""
    module = _shorten_name(record["name"])
    event = record["message"]

    # Extra key=value pairs from loguru's extra dict
    extra = record.get("extra", {})
    kv_parts = []
    for k, v in extra.items():
        if k.startswith("_"):
            continue
        if isinstance(v, float):
            kv_parts.append(f"<dim>{k}</dim>=<cyan>{v:.1f}</cyan>")
        elif isinstance(v, str) and len(v) > 80:
            kv_parts.append(f'<dim>{k}</dim>=<cyan>"{v[:77]}..."</cyan>')
        else:
            kv_parts.append(f"<dim>{k}</dim>=<cyan>{v}</cyan>")
    kv_str = " ".join(kv_parts)

    # Escape braces so loguru's format_map doesn't choke on messages
    # containing literal { } (e.g. watchfiles change detection logs)
    safe_module = module.replace("{", "{{").replace("}", "}}")
    safe_event = event.replace("{", "{{").replace("}", "}}")
    safe_kv = kv_str.replace("{", "{{").replace("}", "}}")

    return (
        "<dim>{time:HH:mm:ss}</dim> "
        "<level>{level: <8}</level> "
        f"<dim>{safe_module:<22}</dim>"
        "<level>|</level> "
        f"<bold>{safe_event:<32}</bold> "
        f"{safe_kv}"
        "\n{exception}"
    )


def _json_format(record: dict) -> str:
    """JSON format for production."""
    return (
        "{{"
        '"ts":"{time:YYYY-MM-DDTHH:mm:ss.SSS}",'
        '"level":"{level}",'
        '"module":"{name}",'
        '"event":"{message}",'
        '"extra":{extra}'
        "}}\n"
    )


class _InterceptHandler(logging.Handler):
    """Route stdlib logging to loguru."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno
        logger.opt(depth=6, exception=record.exc_info).log(
            level, record.getMessage()
        )


def setup_logging() -> None:
    """Configure loguru for the application."""
    settings = get_settings()

    log_level = "DEBUG" if settings.APP_ENVIRONMENT == "development" else "INFO"

    # Remove default loguru handler
    logger.remove()

    if settings.APP_ENVIRONMENT == "production":
        logger.add(
            sys.stdout,
            format=_json_format,
            level=log_level,
            serialize=True,
        )
    else:
        logger.add(
            sys.stdout,
            format=_dev_format,
            level=log_level,
            colorize=True,
        )

    # Intercept stdlib logging -> loguru
    logging.basicConfig(handlers=[_InterceptHandler()], level=logging.DEBUG, force=True)

    # Suppress noisy third-party loggers
    for name in _NOISY_LOGGERS:
        logging.getLogger(name).setLevel(logging.WARNING)


def get_logger(name: str):
    """Get a loguru logger bound with module name.

    Kept for backward compatibility — all files can gradually
    switch to `from loguru import logger` directly.
    """
    return logger.bind()
