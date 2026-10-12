"""Search endpoints.

Handlers are plain ``def`` (not ``async``): model inference is CPU-bound, so
FastAPI runs them in its worker thread pool instead of blocking the event loop.
"""

from __future__ import annotations

import json
from typing import Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, Path, Query, UploadFile, status

from app.api.deps import get_container, read_upload, split_csv
from app.schemas.search import DetectedItem, DetectResponse, ProductHit, SearchResponse
from app.services.container import Container
from app.services.images import ImageError
from app.services.search_service import ProductNotIndexed, SearchResult

router = APIRouter(prefix="/v1", tags=["search"])


def _to_response(result: SearchResult, c: Container) -> SearchResponse:
    return SearchResponse(
        results=[
            ProductHit(product_id=h.product_id, score=h.score, image_url=h.image_url, categories=list(h.categories))
            for h in result.hits
        ],
        total_indexed=c.index.size,
        domain=result.domain,
        min_score_used=result.min_score,
    )


def _parse_bbox(raw: str | None) -> list[float] | None:
    if not raw:
        return None
    try:
        bbox = json.loads(raw)
        if isinstance(bbox, list) and len(bbox) == 4:
            return [float(v) for v in bbox]
    except (ValueError, TypeError):
        pass
    raise HTTPException(422, "bbox must be a JSON array [x1, y1, x2, y2]")


@router.post("/detect", response_model=DetectResponse, summary="Detect shoppable items in a photo")
def detect(image: UploadFile = File(...), c: Container = Depends(get_container)) -> DetectResponse:
    img = read_upload(image, c)
    items = [
        DetectedItem(
            label=d.label.label,
            label_ar=d.label.label_ar,
            icon=d.label.icon,
            prompt=d.label.prompt,
            domain=d.label.domain,
            bbox=list(d.bbox),
            score=d.score,
        )
        for d in c.search.detect(img)
    ]
    return DetectResponse(items=items, image_size=(img.width, img.height))


@router.post("/search", response_model=SearchResponse, summary="Find products similar to an image (or a region of it)")
def search(
    image: UploadFile = File(...),
    bbox: str | None = Form(None, description="Optional JSON [x1,y1,x2,y2] from /v1/detect"),
    top_k: int = Form(12, ge=1),
    domain: Literal["fashion", "general"] = Form("fashion"),
    min_score: float | None = Form(None, ge=-1, le=1, description="Override the similarity threshold"),
    category_hint: str | None = Form(None, description="Comma separated; matching categories are ranked first"),
    categories: str | None = Form(None, description="Comma separated; hard filter"),
    c: Container = Depends(get_container),
) -> SearchResponse:
    img = read_upload(image, c)
    try:
        result = c.search.search_image(
            img,
            top_k=top_k,
            bbox=_parse_bbox(bbox),
            domain=domain,
            min_score=min_score,
            category_hint=split_csv(category_hint),
            categories=split_csv(categories),
        )
    except ImageError as exc:
        raise HTTPException(422, str(exc)) from exc
    return _to_response(result, c)


@router.post("/search/quick", response_model=SearchResponse, summary="Whole-image search, no detection step")
def quick_search(
    image: UploadFile = File(...),
    top_k: int = Form(12, ge=1),
    c: Container = Depends(get_container),
) -> SearchResponse:
    img = read_upload(image, c)
    return _to_response(c.search.search_image(img, top_k=top_k), c)


@router.get(
    "/products/{product_id}/similar",
    response_model=SearchResponse,
    summary="Products that look like an already-indexed product",
)
def similar(
    product_id: int = Path(gt=0),
    top_k: int = Query(8, ge=1),
    category_hint: str | None = Query(None),
    categories: str | None = Query(None),
    c: Container = Depends(get_container),
) -> SearchResponse:
    try:
        result = c.search.similar_to_product(
            product_id,
            top_k=top_k,
            category_hint=split_csv(category_hint),
            categories=split_csv(categories),
        )
    except ProductNotIndexed as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Product is not indexed") from exc
    return _to_response(result, c)
