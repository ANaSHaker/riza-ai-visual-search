import numpy as np
import pytest

from app.index.store import VectorRecord, VectorStore
from app.index.vector_index import HAS_FAISS, VectorIndex
from app.models.embedder import l2_normalize

BACKENDS = ["numpy"] + (["faiss"] if HAS_FAISS else [])


def vec(*xs: float) -> np.ndarray:
    v = np.zeros(4, dtype=np.float32)
    v[: len(xs)] = xs
    return v


def test_l2_normalize_unit_norm_and_zero_safe():
    out = l2_normalize(np.array([[3.0, 4.0], [0.0, 0.0]]))
    assert out.dtype == np.float32
    assert np.allclose(np.linalg.norm(out[0]), 1.0)
    assert np.all(np.isfinite(out[1]))


@pytest.mark.parametrize("backend", BACKENDS)
def test_search_returns_one_hit_per_product_with_best_score(backend):
    idx = VectorIndex(4, backend=backend)
    idx.rebuild(
        [
            VectorRecord(1, "a1", vec(1, 0)),
            VectorRecord(1, "a2", vec(1, 0.2)),  # same product, slightly worse
            VectorRecord(2, "b1", vec(0.7, 0.7)),
            VectorRecord(3, "c1", vec(0, 1)),
        ]
    )
    hits = idx.search(vec(1, 0), top_k=3)
    assert [h.product_id for h in hits] == [1, 2, 3]
    assert hits[0].image_url == "a1"
    assert hits[0].score == pytest.approx(1.0, abs=1e-4)


@pytest.mark.parametrize("backend", BACKENDS)
def test_min_score_and_exclude(backend):
    idx = VectorIndex(4, backend=backend)
    idx.rebuild([VectorRecord(1, "a", vec(1, 0)), VectorRecord(2, "b", vec(0, 1)), VectorRecord(3, "c", vec(1, 0.1))])
    hits = idx.search(vec(1, 0), top_k=10, min_score=0.5, exclude=[1])
    assert [h.product_id for h in hits] == [3]


@pytest.mark.parametrize("backend", BACKENDS)
def test_scores_are_cosine_even_for_unnormalised_inputs(backend):
    idx = VectorIndex(4, backend=backend)
    idx.add(VectorRecord(7, "x", vec(10, 0)))
    (hit,) = idx.search(vec(0.001, 0), top_k=1)
    assert hit.score == pytest.approx(1.0, abs=1e-4)


def test_empty_index_returns_nothing():
    assert VectorIndex(4, backend="numpy").search(vec(1), top_k=5) == []


def test_store_roundtrip_upsert_and_dimension_guard(tmp_path):
    store = VectorStore(tmp_path / "v.db")
    store.upsert(VectorRecord(5, "u", vec(1, 2), ["Women", "Dresses"]))
    store.upsert(VectorRecord(5, "u", vec(3, 4), ["Women"]))  # same key -> update
    store.upsert(VectorRecord(6, "w", np.ones(8, dtype=np.float32)))  # other model's dim
    rows = list(store.iter_all(4))
    assert len(rows) == 1
    assert rows[0].categories == ["Women"]
    assert np.allclose(rows[0].vector, vec(3, 4))
    assert store.stats() == (2, 2)
    assert store.delete_product(5) == 1
    store.close()
