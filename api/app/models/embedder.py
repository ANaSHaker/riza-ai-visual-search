"""Image embedding models.

The service depends on the small :class:`Embedder` protocol, so the heavy
FashionCLIP implementation can be swapped for a fake in tests (or for another
CLIP checkpoint) without touching the search code.
"""

from __future__ import annotations

import logging
from typing import Protocol

import numpy as np
from PIL import Image

log = logging.getLogger(__name__)


def l2_normalize(vectors: np.ndarray) -> np.ndarray:
    """Return a float32 copy of ``vectors`` with unit L2 norm per row.

    With unit vectors, inner product == cosine similarity, which is what the
    ``IndexFlatIP`` FAISS index scores. The epsilon avoids division by zero for
    degenerate (all-zero) embeddings.
    """
    v = np.asarray(vectors, dtype=np.float32)
    if v.ndim == 1:
        v = v.reshape(1, -1)
    norms = np.linalg.norm(v, axis=1, keepdims=True)
    return v / (norms + 1e-8)


class Embedder(Protocol):
    dim: int

    def embed(self, image: Image.Image) -> np.ndarray:
        """Return a unit-norm float32 vector of shape ``(dim,)``."""
        ...


class FashionClipEmbedder:
    """FashionCLIP (CLIP ViT-B/32 fine-tuned on fashion catalogues), 512-d.

    One model serves both fashion and non-fashion products. Production first ran
    a second, general-purpose CLIP for beauty/toys/etc.; measuring showed the
    fashion model covered those categories well enough, and dropping the second
    model freed roughly 1.8 GB of RAM on a CPU-only server.
    """

    def __init__(self, model_name: str, device: str = "cpu") -> None:
        # Imported lazily so the rest of the package (and the tests) do not
        # need torch/transformers installed.
        import torch
        from transformers import CLIPModel, CLIPProcessor

        self._torch = torch
        self.device = device
        log.info("Loading embedding model %s", model_name)
        self.model = CLIPModel.from_pretrained(model_name).to(device).eval()
        self.processor = CLIPProcessor.from_pretrained(model_name)
        self.dim = int(self.model.config.projection_dim)

    def embed(self, image: Image.Image) -> np.ndarray:
        inputs = self.processor(images=image, return_tensors="pt").to(self.device)
        with self._torch.no_grad():
            features = self.model.get_image_features(**inputs)
        return l2_normalize(features.cpu().numpy())[0]
