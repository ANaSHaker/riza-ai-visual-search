"""Application settings, loaded from environment variables (prefix ``VS_``) or a ``.env`` file."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="VS_", env_file=".env", extra="ignore")

    # --- service -----------------------------------------------------------
    app_name: str = "Visual Search API"
    version: str = "2.0.0"
    log_level: str = "INFO"

    # Shared secret expected in the ``X-API-Key`` header. Empty = auth disabled
    # (only acceptable when the service listens on localhost behind the store).
    api_key: str = ""

    # --- models ------------------------------------------------------------
    # FashionCLIP: CLIP ViT-B/32 fine-tuned on fashion product images (512-d output).
    embedding_model: str = "patrickjohncyh/fashion-clip"
    # Open-vocabulary detector used to find individual garments in a photo.
    detector_model: str = "google/owlv2-base-patch16-finetuned"
    # Load the detector at startup in the background (True) or on first /detect (False).
    preload_detector: bool = True
    device: str = "cpu"

    # --- storage -----------------------------------------------------------
    data_dir: Path = Path("./data")

    # --- search tuning (values carried over from production) ----------------
    detect_threshold: float = 0.22
    min_score_fashion: float = 0.20
    min_score_general: float = 0.22
    # FAISS returns many images per product; fetch ``top_k * oversample``
    # neighbours, then collapse them to one hit per product.
    oversample: int = 6
    max_top_k: int = 100
    crop_padding: float = 0.10

    # --- input limits ------------------------------------------------------
    max_upload_mb: float = 10.0
    max_image_pixels: int = 40_000_000
    fetch_timeout_s: float = 30.0
    # Comma separated host allow-list for ``/index/url``. Empty = any public host.
    allowed_image_hosts: str = ""

    @field_validator("oversample")
    @classmethod
    def _oversample_positive(cls, v: int) -> int:
        if v < 1:
            raise ValueError("oversample must be >= 1")
        return v

    @property
    def db_path(self) -> Path:
        return self.data_dir / "vectors.db"

    @property
    def max_upload_bytes(self) -> int:
        return int(self.max_upload_mb * 1024 * 1024)

    @property
    def image_host_allowlist(self) -> set[str]:
        return {h.strip().lower() for h in self.allowed_image_hosts.split(",") if h.strip()}


@lru_cache
def get_settings() -> Settings:
    return Settings()


__all__ = ["Settings", "get_settings"]
