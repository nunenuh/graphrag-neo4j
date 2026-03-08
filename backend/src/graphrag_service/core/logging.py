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


def _dev_sink(message) -> None:
    """Custom dev sink: compact, aligned, colored.

    Uses a sink function instead of a format function to avoid loguru's
    format_map processing, which chokes on messages containing literal
    curly braces (e.g. watchfiles change detection logs).
    """
    record = message.record
    module = _shorten_name(record["name"])
    event = record["message"]
    level = record["level"]
    time_str = record["time"].strftime("%H:%M:%S")

    # Extra key=value pairs from loguru's extra dict
    extra = record.get("extra", {})
    kv_parts = []
    for k, v in extra.items():
        if k.startswith("_"):
            continue
        if isinstance(v, float):
            kv_parts.append(f"\033[2m{k}\033[0m=\033[36m{v:.1f}\033[0m")
        elif isinstance(v, str) and len(v) > 80:
            kv_parts.append(f'\033[2m{k}\033[0m=\033[36m"{v[:77]}..."\033[0m')
        else:
            kv_parts.append(f"\033[2m{k}\033[0m=\033[36m{v}\033[0m")
    kv_str = " ".join(kv_parts)

    # Level colors
    level_colors = {
        "DEBUG": "\033[34m",    # blue
        "INFO": "\033[34;1m",   # bold blue
        "WARNING": "\033[33m",  # yellow
        "ERROR": "\033[31m",    # red
        "CRITICAL": "\033[31;1m",  # bold red
    }
    color = level_colors.get(level.name, "\033[0m")
    reset = "\033[0m"
    dim = "\033[2m"
    bold = "\033[1m"

    line = (
        f"{dim}{time_str}{reset} "
        f"{color}{level.name:<8}{reset} "
        f"{dim}{module:<22}{reset}"
        f"{color}|{reset} "
        f"{bold}{event:<32}{reset} "
        f"{kv_str}"
    )
    sys.stdout.write(line + "\n")

    # Print exception if present
    if record["exception"] is not None:
        import traceback
        tb = "".join(
            traceback.format_exception(
                record["exception"].type,
                record["exception"].value,
                record["exception"].traceback,
            )
        )
        sys.stdout.write(tb)


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
            _dev_sink,
            level=log_level,
            colorize=False,
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
