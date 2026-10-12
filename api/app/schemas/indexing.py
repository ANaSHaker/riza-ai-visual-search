"""Request / response models for the indexing endpoints."""

from __future__ import annotations

from pydantic import BaseModel, Field, HttpUrl


class IndexImageRequest(BaseModel):
    product_id: int = Field(gt=0, examples=[1042])
    image_url: HttpUrl = Field(examples=["https://shop.example.com/wp-content/uploads/dress-front.jpg"])
    categories: list[str] = Field(default_factory=list, max_length=50, examples=[["Women", "Dresses"]])


class IndexBatchRequest(BaseModel):
    items: list[IndexImageRequest] = Field(min_length=1, max_length=200)


class IndexItemResult(BaseModel):
    product_id: int
    image_url: str
    ok: bool
    error: str | None = None


class IndexBatchResponse(BaseModel):
    indexed: int
    failed: int
    results: list[IndexItemResult]
    total_indexed: int


class IndexStatsResponse(BaseModel):
    images: int = Field(description="Image vectors stored in SQLite")
    products: int = Field(description="Distinct products with at least one vector")
    vectors_in_memory: int = Field(description="Vectors loaded in the search index")
    backend: str = Field(examples=["faiss"])


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str
    embedding_model: str
    detector_model: str
    detector_loaded: bool
    vectors: int
