from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Path

from app.api.deps import get_container
from app.schemas.indexing import (
    IndexBatchRequest,
    IndexBatchResponse,
    IndexImageRequest,
    IndexItemResult,
    IndexStatsResponse,
)
from app.services.container import Container
from app.services.images import ImageError

log = logging.getLogger(__name__)
router = APIRouter(prefix="/v1/index", tags=["indexing"])


def _index_one(item: IndexImageRequest, c: Container) -> IndexItemResult:
    url = str(item.image_url)
    try:
        c.indexing.index_url(item.product_id, url, item.categories)
        return IndexItemResult(product_id=item.product_id, image_url=url, ok=True)
    except ImageError as exc:
        return IndexItemResult(product_id=item.product_id, image_url=url, ok=False, error=str(exc))
    except Exception:  # model/IO failure — log details server-side only
        log.exception("Indexing failed for product %s", item.product_id)
        return IndexItemResult(product_id=item.product_id, image_url=url, ok=False, error="internal error")


@router.post("", response_model=IndexItemResult, summary="Index one product image by URL")
def index_image(item: IndexImageRequest, c: Container = Depends(get_container)) -> IndexItemResult:
    result = _index_one(item, c)
    if not result.ok:
        raise HTTPException(422, result.error)
    return result


@router.post("/batch", response_model=IndexBatchResponse, summary="Index up to 200 images; per-item results")
def index_batch(body: IndexBatchRequest, c: Container = Depends(get_container)) -> IndexBatchResponse:
    results = [_index_one(item, c) for item in body.items]
    ok = sum(r.ok for r in results)
    return IndexBatchResponse(indexed=ok, failed=len(results) - ok, results=results, total_indexed=c.index.size)


@router.delete("/products/{product_id}", summary="Remove every vector of a product")
def delete_product(product_id: int = Path(gt=0), c: Container = Depends(get_container)) -> dict:
    return {"removed": c.indexing.delete_product(product_id)}


@router.post("/rebuild", summary="Rebuild the in-memory index from SQLite")
def rebuild(c: Container = Depends(get_container)) -> dict:
    return {"vectors": c.indexing.rebuild()}


@router.get("/stats", response_model=IndexStatsResponse)
def stats(c: Container = Depends(get_container)) -> IndexStatsResponse:
    s = c.indexing.stats()
    return IndexStatsResponse(
        images=s.images, products=s.products, vectors_in_memory=s.vectors_in_memory, backend=c.index.backend
    )
