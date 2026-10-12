"""Use cases: detect garments, search by image, find similar products."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
from PIL import Image

from app.core.config import Settings
from app.index.store import VectorStore
from app.index.vector_index import Hit, VectorIndex
from app.models.detector import Detection, Detector
from app.models.embedder import Embedder, l2_normalize
from app.models.vocabulary import WHOLE_IMAGE, Domain
from app.services.images import crop_with_padding
from app.services.rerank import boost_by_category, filter_by_category


class ProductNotIndexed(LookupError):
    pass


@dataclass
class SearchResult:
    hits: list[Hit]
    min_score: float
    domain: Domain


class SearchService:
    def __init__(
        self,
        settings: Settings,
        embedder: Embedder,
        detector: Detector,
        index: VectorIndex,
        store: VectorStore,
    ) -> None:
        self.settings = settings
        self.embedder = embedder
        self.detector = detector
        self.index = index
        self.store = store

    # ------------------------------------------------------------------
    def detect(self, image: Image.Image) -> list[Detection]:
        """Detected items, or a single whole-image item when nothing is found.

        The fallback keeps the UX simple: the shopper always gets at least one
        chip to tap, and searching the whole photo is still useful.
        """
        found = self.detector.detect(image)
        if found:
            return found
        return [Detection(WHOLE_IMAGE, (0.0, 0.0, float(image.width), float(image.height)), 1.0)]

    def _threshold(self, domain: Domain, override: float | None) -> float:
        if override is not None and override >= 0:
            return override
        return self.settings.min_score_general if domain == "general" else self.settings.min_score_fashion

    def _clamp_k(self, top_k: int) -> int:
        return max(1, min(int(top_k), self.settings.max_top_k))

    def _rank(
        self,
        query: np.ndarray,
        top_k: int,
        threshold: float,
        category_hint: Sequence[str],
        categories: Sequence[str],
        exclude: Sequence[int] = (),
    ) -> list[Hit]:
        k = self._clamp_k(top_k)
        # Fetch a wider candidate pool when we will filter/re-rank afterwards.
        pool = k * 4 if (categories or category_hint) else k
        hits = self.index.search(query, pool, threshold, self.settings.oversample, exclude)
        hits = filter_by_category(hits, categories)
        hits = boost_by_category(hits, category_hint)
        return hits[:k]

    # ------------------------------------------------------------------
    def search_image(
        self,
        image: Image.Image,
        *,
        top_k: int = 12,
        bbox: Sequence[float] | None = None,
        domain: Domain = "fashion",
        min_score: float | None = None,
        category_hint: Sequence[str] = (),
        categories: Sequence[str] = (),
    ) -> SearchResult:
        if bbox:
            image = crop_with_padding(image, bbox, self.settings.crop_padding)
        query = self.embedder.embed(image)
        threshold = self._threshold(domain, min_score)
        hits = self._rank(query, top_k, threshold, category_hint, categories)
        return SearchResult(hits, threshold, domain)

    def similar_to_product(
        self,
        product_id: int,
        *,
        top_k: int = 12,
        min_score: float | None = None,
        category_hint: Sequence[str] = (),
        categories: Sequence[str] = (),
    ) -> SearchResult:
        """ "More like this": average the product's image vectors and search."""
        vectors = self.store.product_vectors(product_id, self.index.dim)
        if not vectors:
            raise ProductNotIndexed(product_id)
        query = l2_normalize(np.mean(l2_normalize(np.stack(vectors)), axis=0))[0]
        threshold = self._threshold("fashion", min_score)
        hits = self._rank(query, top_k, threshold, category_hint, categories, exclude=[product_id])
        return SearchResult(hits, threshold, "fashion")
