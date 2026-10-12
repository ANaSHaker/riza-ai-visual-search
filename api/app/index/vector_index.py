"""Exact cosine-similarity index over product image embeddings.

Uses FAISS ``IndexFlatIP`` (exact inner-product search) on L2-normalised
vectors, i.e. cosine similarity. For a catalogue of a few thousand products ×
several images each, brute-force search is single-digit milliseconds on CPU
and needs no training, so approximate indexes (IVF/HNSW) would add complexity
without a measurable benefit. If FAISS is not installed, an equivalent NumPy
backend is used (handy for tests and tiny catalogues).
"""

from __future__ import annotations

import threading
from collections.abc import Iterable
from dataclasses import dataclass, field

import numpy as np

from app.index.store import VectorRecord
from app.models.embedder import l2_normalize

try:  # pragma: no cover - exercised implicitly depending on the environment
    import faiss  # type: ignore

    HAS_FAISS = True
except ImportError:  # pragma: no cover
    faiss = None
    HAS_FAISS = False


@dataclass(frozen=True)
class Entry:
    product_id: int
    image_url: str
    categories: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class Hit:
    product_id: int
    score: float
    image_url: str
    categories: tuple[str, ...]


class _NumpyFlatIP:
    """Minimal drop-in for ``faiss.IndexFlatIP`` (exact, brute force)."""

    def __init__(self, dim: int) -> None:
        self.d = dim
        self._data = np.empty((0, dim), dtype=np.float32)

    @property
    def ntotal(self) -> int:
        return self._data.shape[0]

    def add(self, x: np.ndarray) -> None:
        self._data = np.vstack([self._data, x.astype(np.float32)])

    def search(self, q: np.ndarray, k: int) -> tuple[np.ndarray, np.ndarray]:
        sims = q @ self._data.T
        idx = np.argsort(-sims, axis=1)[:, :k]
        return np.take_along_axis(sims, idx, axis=1), idx


def _new_flat_index(dim: int, backend: str):
    if backend == "faiss":
        if not HAS_FAISS:
            raise RuntimeError("faiss is not installed")
        return faiss.IndexFlatIP(dim)
    return _NumpyFlatIP(dim)


class VectorIndex:
    def __init__(self, dim: int, backend: str | None = None) -> None:
        self.dim = dim
        self.backend = backend or ("faiss" if HAS_FAISS else "numpy")
        self._lock = threading.RLock()
        self._index = _new_flat_index(dim, self.backend)
        self._entries: list[Entry] = []

    # -- mutation ----------------------------------------------------------
    def rebuild(self, records: Iterable[VectorRecord]) -> int:
        index = _new_flat_index(self.dim, self.backend)
        entries: list[Entry] = []
        batch: list[np.ndarray] = []
        for r in records:
            batch.append(np.asarray(r.vector, dtype=np.float32).reshape(-1))
            entries.append(Entry(r.product_id, r.image_url, tuple(r.categories)))
        if batch:
            index.add(l2_normalize(np.stack(batch)))
        with self._lock:
            self._index, self._entries = index, entries
        return len(entries)

    def add(self, record: VectorRecord) -> None:
        vec = l2_normalize(record.vector)
        with self._lock:
            self._index.add(vec)
            self._entries.append(Entry(record.product_id, record.image_url, tuple(record.categories)))

    # -- queries -----------------------------------------------------------
    @property
    def size(self) -> int:
        return self._index.ntotal

    def search(
        self,
        query: np.ndarray,
        top_k: int,
        min_score: float = -1.0,
        oversample: int = 6,
        exclude: Iterable[int] = (),
    ) -> list[Hit]:
        """Return up to ``top_k`` *products* most similar to ``query``.

        Products have several images, so the raw neighbour list is dominated by
        a handful of products. We ask FAISS for ``top_k * oversample`` image
        neighbours, keep the best-scoring image per product, drop anything under
        ``min_score`` and return the top ``top_k`` products.
        """
        excluded = set(exclude)
        with self._lock:
            n = self._index.ntotal
            if n == 0 or top_k <= 0:
                return []
            k = min(top_k * oversample + len(excluded), n)
            scores, ids = self._index.search(l2_normalize(query), k)
            entries = self._entries

        best: dict[int, Hit] = {}
        for score, i in zip(scores[0], ids[0], strict=True):
            if i < 0 or i >= len(entries):
                continue
            s = float(score)
            if s < min_score:
                continue
            e = entries[i]
            if e.product_id in excluded:
                continue
            if e.product_id not in best or s > best[e.product_id].score:
                best[e.product_id] = Hit(e.product_id, round(s, 4), e.image_url, e.categories)
        return sorted(best.values(), key=lambda h: -h.score)[:top_k]
