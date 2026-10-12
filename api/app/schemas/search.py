"""Request / response models for the search endpoints."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class DetectedItem(BaseModel):
    label: str = Field(examples=["Dress"])
    label_ar: str = Field(examples=["فستان"])
    icon: str = Field(examples=["👗"])
    prompt: str = Field(description="Detector prompt that matched", examples=["a woman wearing a dress"])
    domain: Literal["fashion", "general"]
    bbox: list[float] = Field(description="x1, y1, x2, y2 in pixels", examples=[[112.0, 40.5, 388.2, 610.0]])
    score: float = Field(examples=[0.512])


class DetectResponse(BaseModel):
    items: list[DetectedItem]
    image_size: tuple[int, int] = Field(description="width, height", examples=[[600, 800]])


class ProductHit(BaseModel):
    product_id: int = Field(examples=[1042])
    score: float = Field(description="Cosine similarity of the best-matching image", examples=[0.8731])
    image_url: str = Field(description="The indexed image that matched")
    categories: list[str] = Field(default_factory=list, examples=[["Women", "Dresses"]])


class SearchResponse(BaseModel):
    results: list[ProductHit]
    total_indexed: int = Field(description="Image vectors currently searchable")
    domain: Literal["fashion", "general"]
    min_score_used: float
