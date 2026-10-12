"""FastAPI application factory.

Run locally:  uvicorn app.main:app --host 127.0.0.1 --port 8000
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI

from app.api.routes import health, indexing, search
from app.core.config import Settings, get_settings
from app.core.logging import configure_logging
from app.core.security import require_api_key
from app.services.container import Container, build_container

log = logging.getLogger(__name__)


def create_app(
    settings: Settings | None = None,
    container_factory: Callable[[Settings], Container] | None = None,
) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level)
    factory = container_factory or build_container

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        container = factory(settings)
        app.state.container = container
        log.info("Ready — %d vectors (%s backend)", container.index.size, container.index.backend)
        if settings.preload_detector:
            # Warm the detector without delaying startup; /search works meanwhile.
            threading.Thread(target=container.detector.get, name="detector-warmup", daemon=True).start()
        yield
        container.close()

    app = FastAPI(
        title=settings.app_name,
        version=settings.version,
        description="Visual & similar-product search for e-commerce catalogues (FashionCLIP + FAISS).",
        lifespan=lifespan,
    )
    # Settings dependency resolves to the instance this app was created with.
    app.dependency_overrides[get_settings] = lambda: settings

    protected = [Depends(require_api_key)]
    app.include_router(health.router)
    app.include_router(search.router, dependencies=protected)
    app.include_router(indexing.router, dependencies=protected)
    return app


app = create_app()
