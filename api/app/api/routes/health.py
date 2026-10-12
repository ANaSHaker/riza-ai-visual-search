from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_container
from app.schemas.indexing import HealthResponse
from app.services.container import Container

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health(c: Container = Depends(get_container)) -> HealthResponse:
    """Liveness/readiness probe. Intentionally exposes no catalogue data."""
    return HealthResponse(
        version=c.settings.version,
        embedding_model=c.settings.embedding_model,
        detector_model=c.settings.detector_model,
        detector_loaded=c.detector.loaded,
        vectors=c.index.size,
    )
