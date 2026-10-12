"""Shared FastAPI dependencies."""

from __future__ import annotations

from fastapi import HTTPException, Request, UploadFile
from PIL import Image

from app.services.container import Container
from app.services.images import ImageError, decode_image


def get_container(request: Request) -> Container:
    return request.app.state.container


def read_upload(upload: UploadFile, container: Container) -> Image.Image:
    """Read an uploaded file with a hard size cap and decode it safely."""
    s = container.settings
    data = upload.file.read(s.max_upload_bytes + 1)
    try:
        return decode_image(data, s.max_upload_bytes, s.max_image_pixels)
    except ImageError as exc:
        code = 413 if len(data) > s.max_upload_bytes else 422
        raise HTTPException(code, str(exc)) from exc


def split_csv(value: str | None) -> list[str]:
    return [v.strip() for v in (value or "").split(",") if v.strip()]
