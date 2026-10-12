"""Composition root: wires settings, models, storage and services together."""

from __future__ import annotations

from dataclasses import dataclass

from app.core.config import Settings
from app.index.store import VectorStore
from app.index.vector_index import VectorIndex
from app.models.detector import Detector, LazyDetector, Owlv2Detector
from app.models.embedder import Embedder, FashionClipEmbedder
from app.services.indexing_service import IndexingService
from app.services.search_service import SearchService


@dataclass
class Container:
    settings: Settings
    embedder: Embedder
    detector: LazyDetector
    store: VectorStore
    index: VectorIndex
    search: SearchService
    indexing: IndexingService

    def close(self) -> None:
        self.store.close()


def build_container(
    settings: Settings,
    *,
    embedder: Embedder | None = None,
    detector: Detector | None = None,
    store: VectorStore | None = None,
) -> Container:
    """Build the object graph. Tests inject lightweight fakes for the models."""
    embedder = embedder or FashionClipEmbedder(settings.embedding_model, settings.device)
    lazy = LazyDetector(
        (lambda: detector)
        if detector is not None
        else (lambda: Owlv2Detector(settings.detector_model, settings.detect_threshold, settings.device))
    )
    store = store or VectorStore(settings.db_path)
    index = VectorIndex(embedder.dim)
    indexing = IndexingService(settings, embedder, index, store)
    indexing.rebuild()
    search = SearchService(settings, embedder, lazy, index, store)
    return Container(settings, embedder, lazy, store, index, search, indexing)
