"""Garment detection with OWLv2 (open-vocabulary object detection).

The detector is the most memory-hungry component (~2.5 GB RAM on CPU) and is
only needed for "detect items in this photo" requests, so it is wrapped in
:class:`LazyDetector`, which loads it once, on demand, behind a lock.
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Protocol

from PIL import Image

from app.models.vocabulary import PROMPTS, VOCABULARY, DetectionLabel

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Detection:
    label: DetectionLabel
    bbox: tuple[float, float, float, float]  # x1, y1, x2, y2 in pixels
    score: float


class Detector(Protocol):
    def detect(self, image: Image.Image) -> list[Detection]: ...


def best_per_label(
    boxes: Sequence[Sequence[float]],
    scores: Sequence[float],
    label_ids: Sequence[int],
    vocabulary: Sequence[DetectionLabel] = VOCABULARY,
) -> list[Detection]:
    """Keep the highest-scoring box for each label, sorted by score (desc).

    A photo of one outfit usually yields several overlapping boxes for the same
    prompt; showing the shopper one chip per garment type is far clearer.
    """
    best: dict[int, tuple[float, Sequence[float]]] = {}
    for box, score, idx in zip(boxes, scores, label_ids, strict=True):
        if idx not in best or score > best[idx][0]:
            best[idx] = (float(score), box)

    detections = [
        Detection(
            label=vocabulary[idx],
            bbox=tuple(round(float(c), 1) for c in box),  # type: ignore[arg-type]
            score=round(score, 3),
        )
        for idx, (score, box) in best.items()
    ]
    return sorted(detections, key=lambda d: -d.score)


class Owlv2Detector:
    def __init__(self, model_name: str, threshold: float, device: str = "cpu") -> None:
        import torch
        from transformers import Owlv2ForObjectDetection, Owlv2Processor

        self._torch = torch
        self.device = device
        self.threshold = threshold
        log.info("Loading detector %s", model_name)
        self.processor = Owlv2Processor.from_pretrained(model_name)
        self.model = Owlv2ForObjectDetection.from_pretrained(model_name).to(device).eval()

    def detect(self, image: Image.Image) -> list[Detection]:
        inputs = self.processor(text=[list(PROMPTS)], images=image, return_tensors="pt").to(self.device)
        with self._torch.no_grad():
            outputs = self.model(**inputs)
        # OWLv2 pads images to a square; post-process against the padded size
        # so boxes map back correctly onto the original pixels.
        side = max(image.width, image.height)
        result = self.processor.post_process_object_detection(
            outputs=outputs,
            threshold=self.threshold,
            target_sizes=self._torch.tensor([[side, side]]),
        )[0]
        return best_per_label(result["boxes"].tolist(), result["scores"].tolist(), result["labels"].tolist())


class LazyDetector:
    """Builds the wrapped detector on first use (thread-safe, double-checked)."""

    def __init__(self, factory: Callable[[], Detector]) -> None:
        self._factory = factory
        self._instance: Detector | None = None
        self._lock = threading.Lock()

    @property
    def loaded(self) -> bool:
        return self._instance is not None

    def get(self) -> Detector:
        if self._instance is None:
            with self._lock:
                if self._instance is None:
                    self._instance = self._factory()
        return self._instance

    def detect(self, image: Image.Image) -> list[Detection]:
        return self.get().detect(image)
