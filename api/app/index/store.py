"""SQLite persistence for image embeddings.

SQLite is the source of truth; the FAISS index is an in-memory acceleration
structure rebuilt from it at startup (a few thousand products rebuild in well
under a second). One row per (product, image URL), so re-indexing an image is
an idempotent upsert.
"""

from __future__ import annotations

import json
import sqlite3
import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

_SCHEMA = """
CREATE TABLE IF NOT EXISTS vectors (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id  INTEGER NOT NULL,
    image_url   TEXT    NOT NULL,
    categories  TEXT    NOT NULL DEFAULT '[]',
    vector      BLOB    NOT NULL,
    created_at  REAL    NOT NULL,
    UNIQUE(product_id, image_url)
);
CREATE INDEX IF NOT EXISTS ix_vectors_product ON vectors(product_id);
"""


@dataclass
class VectorRecord:
    product_id: int
    image_url: str
    vector: np.ndarray
    categories: list[str] = field(default_factory=list)


class VectorStore:
    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)
        if str(self.path) != ":memory:":
            self.path.parent.mkdir(parents=True, exist_ok=True)
        # A single connection guarded by SQLite's own locking; the service
        # writes rarely (indexing) and reads once at startup.
        self._conn = sqlite3.connect(str(self.path), check_same_thread=False)
        self._conn.executescript(_SCHEMA)

    @contextmanager
    def _tx(self) -> Iterator[sqlite3.Connection]:
        with self._conn:
            yield self._conn

    def upsert(self, record: VectorRecord) -> None:
        blob = np.asarray(record.vector, dtype=np.float32).tobytes()
        with self._tx() as c:
            c.execute(
                """INSERT INTO vectors (product_id, image_url, categories, vector, created_at)
                   VALUES (?, ?, ?, ?, ?)
                   ON CONFLICT(product_id, image_url) DO UPDATE SET
                     categories = excluded.categories,
                     vector     = excluded.vector,
                     created_at = excluded.created_at""",
                (
                    record.product_id,
                    record.image_url,
                    json.dumps(record.categories, ensure_ascii=False),
                    blob,
                    time.time(),
                ),
            )

    def delete_product(self, product_id: int) -> int:
        with self._tx() as c:
            return c.execute("DELETE FROM vectors WHERE product_id = ?", (product_id,)).rowcount

    def iter_all(self, dim: int) -> Iterator[VectorRecord]:
        rows = self._conn.execute("SELECT product_id, image_url, categories, vector FROM vectors ORDER BY id")
        for pid, url, cats, blob in rows:
            vec = np.frombuffer(blob, dtype=np.float32)
            if vec.shape[0] != dim:  # skip vectors from a different model
                continue
            yield VectorRecord(int(pid), url, vec.copy(), json.loads(cats or "[]"))

    def product_vectors(self, product_id: int, dim: int) -> list[np.ndarray]:
        rows = self._conn.execute("SELECT vector FROM vectors WHERE product_id = ?", (product_id,))
        return [v for (blob,) in rows if (v := np.frombuffer(blob, dtype=np.float32)).shape[0] == dim]

    def stats(self) -> tuple[int, int]:
        images, products = self._conn.execute("SELECT COUNT(*), COUNT(DISTINCT product_id) FROM vectors").fetchone()
        return int(images), int(products)

    def close(self) -> None:
        self._conn.close()
