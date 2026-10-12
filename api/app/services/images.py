"""Image decoding, cropping and safe remote fetching."""

from __future__ import annotations

import ipaddress
import socket
from collections.abc import Sequence
from io import BytesIO
from urllib.parse import urlparse

import httpx
from PIL import Image, UnidentifiedImageError


class ImageError(ValueError):
    """Raised for unreadable, oversized or disallowed images."""


def decode_image(data: bytes, max_bytes: int, max_pixels: int) -> Image.Image:
    if not data:
        raise ImageError("Empty image")
    if len(data) > max_bytes:
        raise ImageError(f"Image larger than {max_bytes // (1024 * 1024)} MB")
    try:
        img = Image.open(BytesIO(data))
        # Check dimensions *before* decoding pixels (decompression-bomb guard).
        if img.width * img.height > max_pixels:
            raise ImageError("Image dimensions too large")
        img.load()
    except (UnidentifiedImageError, OSError) as exc:
        raise ImageError("Unsupported or corrupt image") from exc
    return img.convert("RGB")


def crop_with_padding(img: Image.Image, bbox: Sequence[float], padding: float = 0.10) -> Image.Image:
    """Crop ``bbox`` (x1, y1, x2, y2) expanded by ``padding`` of its size on each side.

    A little context around a detected garment (collar, hem, how it drapes)
    noticeably improves CLIP matches compared with a tight crop.
    """
    if len(bbox) != 4:
        raise ImageError("bbox must have 4 values: x1, y1, x2, y2")
    x1, y1, x2, y2 = (float(v) for v in bbox)
    if x2 <= x1 or y2 <= y1:
        raise ImageError("bbox has no area")
    pw, ph = (x2 - x1) * padding, (y2 - y1) * padding
    w, h = img.size
    box = (
        max(0, int(x1 - pw)),
        max(0, int(y1 - ph)),
        min(w, int(x2 + pw)),
        min(h, int(y2 + ph)),
    )
    if box[2] <= box[0] or box[3] <= box[1]:
        raise ImageError("bbox is outside the image")
    return img.crop(box)


def _is_public_host(host: str) -> bool:
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror:
        return False
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
            return False
    return True


def validate_image_url(url: str, allowlist: set[str]) -> str:
    """Reject URLs that could be abused for SSRF (internal hosts, odd schemes)."""
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ImageError("Only absolute http(s) URLs are allowed")
    host = parsed.hostname.lower()
    if allowlist:
        if host not in allowlist:
            raise ImageError("Image host is not in the allow-list")
    elif not _is_public_host(host):
        raise ImageError("Image host resolves to a non-public address")
    return url


def fetch_image(
    url: str,
    *,
    allowlist: set[str],
    max_bytes: int,
    max_pixels: int,
    timeout: float,
    client: httpx.Client | None = None,
) -> Image.Image:
    validate_image_url(url, allowlist)
    own = client is None
    client = client or httpx.Client(timeout=timeout, follow_redirects=False)
    try:
        with client.stream("GET", url, headers={"User-Agent": "visual-search-indexer/2"}) as r:
            if r.status_code != 200:
                raise ImageError(f"Image download failed with HTTP {r.status_code}")
            buf = bytearray()
            for chunk in r.iter_bytes():
                buf.extend(chunk)
                if len(buf) > max_bytes:
                    raise ImageError("Remote image too large")
    except httpx.HTTPError as exc:
        raise ImageError(f"Image download failed: {exc.__class__.__name__}") from exc
    finally:
        if own:
            client.close()
    return decode_image(bytes(buf), max_bytes, max_pixels)
