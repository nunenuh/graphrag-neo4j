"""
Graph service — orchestrates library calls for parsing and data preparation.

Does NOT access the database. Uses library/ for reusable logic.
"""

import json
from pathlib import Path
from typing import Iterator

from loguru import logger

from graphrag_service.core.config import get_settings
from graphrag_service.library.llm import embed_batch
from graphrag_service.library.parsers import (
    iter_datasets,
    iter_methods,
    iter_papers,
    iter_tasks,
    load_json,
)



class GraphService:
    """Service for data parsing and preparation. Does NOT access the database."""

    @staticmethod
    def data_dir() -> Path:
        """Resolve the data directory path."""
        settings = get_settings()
        path = Path(settings.DATA_DIR)
        if path.is_absolute():
            return path
        # __file__ is modules/graph/services.py → go up 6 levels to project root
        return Path(__file__).parent.parent.parent.parent.parent.parent / settings.DATA_DIR

    def load_papers(
        self, offset: int = 0, limit: int = 0
    ) -> Iterator[dict]:
        """Load and parse papers using library functions."""
        settings = get_settings()
        data = load_json(self.data_dir() / "papers.json")
        return iter_papers(data, max_papers=settings.MAX_PAPERS, offset=offset, limit=limit)

    def load_methods(
        self, offset: int = 0, limit: int = 0
    ) -> Iterator[dict]:
        """Load and parse methods using library functions."""
        settings = get_settings()
        data = load_json(self.data_dir() / "methods.json")
        return iter_methods(data, max_items=settings.MAX_METHODS, offset=offset, limit=limit)

    def load_tasks(
        self, offset: int = 0, limit: int = 0
    ) -> Iterator[dict]:
        """Load and parse tasks using library functions."""
        settings = get_settings()
        data = load_json(self.data_dir() / "tasks.json")
        return iter_tasks(data, max_items=settings.MAX_TASKS, offset=offset, limit=limit)

    def load_datasets(
        self, offset: int = 0, limit: int = 0
    ) -> Iterator[dict]:
        """Load and parse datasets using library functions."""
        settings = get_settings()
        data = load_json(self.data_dir() / "datasets.json")
        return iter_datasets(data, max_items=settings.MAX_DATASETS, offset=offset, limit=limit)

    def load_evaluations(self) -> list:
        """Load evaluation data from JSON."""
        eval_path = self.data_dir() / "evaluations.json"
        with open(eval_path, encoding="utf-8") as f:
            return json.load(f)

    @staticmethod
    def prepare_embed_texts(nodes: list[dict]) -> list[str]:
        """Prepare text strings for embedding from node dicts."""
        return [
            f"{n.get('title', n.get('name', ''))} "
            f"{n.get('abstract', n.get('description', ''))}"
            for n in nodes
        ]

    @staticmethod
    def embed_nodes(texts: list[str]) -> list[list[float]]:
        """Embed a batch of texts using library/llm."""
        return embed_batch(texts)
