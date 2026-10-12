"""Test fixtures. The real FashionCLIP / OWLv2 models are never loaded:
a colour-based fake embedder gives deterministic, meaningful similarities."""

from __future__ import annotations

from io import BytesIO

import numpy as np
import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.core.config import Settings
from app.index.store import VectorStore
from app.main import create_app
from app.models.detector import Detection
from app.models.embedder import l2_normalize
from app.models.vocabulary import VOCABULARY
from app.services.container import build_container

COLORS = {"red": (230, 20, 20), "green": (20, 200, 30), "blue": (20, 40, 220), "orange": (240, 120, 20)}
API_KEY = "test-key"


class FakeEmbedder:
    """Embeds an image as its normalised mean RGB colour (padded to ``dim``)."""

    dim = 8

    def embed(self, image: Image.Image) -> np.ndarray:
        rgb = np.asarray(image.convert("RGB"), dtype=np.float32).reshape(-1, 3).mean(axis=0) / 255.0
        v = np.zeros(self.dim, dtype=np.float32)
        v[:3] = rgb
        return l2_normalize(v)[0]


class FakeDetector:
    def __init__(self, detections: list[Detection] | None = None) -> None:
        self.detections = detections or []
        self.calls = 0

    def detect(self, image: Image.Image) -> list[Detection]:
        self.calls += 1
        return list(self.detections)


def solid(color: str, size: tuple[int, int] = (64, 64)) -> Image.Image:
    return Image.new("RGB", size, COLORS[color])


def png_bytes(img: Image.Image) -> bytes:
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def fake_fetch(url: str, **_: object) -> Image.Image:
    """Stand-in for the HTTP image download: colour is taken from the URL."""
    for name in COLORS:
        if name in url:
            return solid(name)
    from app.services.images import ImageError

    raise ImageError("Image download failed with HTTP 404")


@pytest.fixture
def settings(tmp_path) -> Settings:
    return Settings(
        data_dir=tmp_path,
        api_key=API_KEY,
        preload_detector=False,
        min_score_fashion=0.5,
        min_score_general=0.6,
    )


@pytest.fixture
def detector() -> FakeDetector:
    dress = next(v for v in VOCABULARY if v.label == "Dress")
    return FakeDetector([Detection(dress, (10.0, 10.0, 50.0, 60.0), 0.61)])


@pytest.fixture
def container(settings, detector, monkeypatch):
    monkeypatch.setattr("app.services.indexing_service.fetch_image", fake_fetch)
    c = build_container(settings, embedder=FakeEmbedder(), detector=detector, store=VectorStore(settings.db_path))
    yield c
    c.close()


@pytest.fixture
def client(settings, detector, monkeypatch):
    monkeypatch.setattr("app.services.indexing_service.fetch_image", fake_fetch)
    app = create_app(
        settings,
        container_factory=lambda s: build_container(s, embedder=FakeEmbedder(), detector=detector),
    )
    with TestClient(app, headers={"X-API-Key": API_KEY}) as c:
        yield c
