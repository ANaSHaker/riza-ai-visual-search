"""Use cases: add product images to the index, remove products, rebuild."""

from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass

from PIL import Image

from app.core.config import Settings
from app.index.store import VectorRecord, VectorStore
from app.index.vector_index import VectorIndex
from app.models.embedder import Embedder
from app.services.images import fetch_image

log = logging.getLogger(__name__)


@dataclass
class IndexStats:
    images: int
    products: int
    vectors_in_memory: int


class IndexingService:
    def __init__(self, settings: Settings, embedder: Embedder, index: VectorIndex, store: VectorStore) -> None:
        self.settings = settings
        self.embedder = embedder
        self.index = index
        self.store = store

    def index_image(self, product_id: int, image_url: str, image: Image.Image, categories: Sequence[str] = ()) -> None:
        record = VectorRecord(product_id, image_url, self.embedder.embed(image), list(categories))
        self.store.upsert(record)
        # SQLite is updated in place; the flat in-memory index is append-only.
        # A re-indexed image therefore exists twice in memory until the next
        # rebuild, which is harmless because search keeps one hit per product.
        # Call /index/rebuild after a bulk re-index to compact it.
        self.index.add(record)

    def index_url(self, product_id: int, image_url: str, categories: Sequence[str] = ()) -> None:
        s = self.settings
        image = fetch_image(
            image_url,
            allowlist=s.image_host_allowlist,
            max_bytes=s.max_upload_bytes,
            max_pixels=s.max_image_pixels,
            timeout=s.fetch_timeout_s,
        )
        self.index_image(product_id, image_url, image, categories)

    def delete_product(self, product_id: int) -> int:
        removed = self.store.delete_product(product_id)
        if removed:
            self.rebuild()
        return removed

    def rebuild(self) -> int:
        n = self.index.rebuild(self.store.iter_all(self.index.dim))
        log.info("Vector index rebuilt: %d vectors (%s backend)", n, self.index.backend)
        return n

    def stats(self) -> IndexStats:
        images, products = self.store.stats()
        return IndexStats(images, products, self.index.size)
