"""Product catalogue readers: CSV, JSON and the WooCommerce REST API.

Every source yields :class:`CatalogItem` objects, so the indexer does not care
where products come from.
"""

from __future__ import annotations

import csv
import json
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path

import httpx

_LIST_SEP = "|"


@dataclass
class CatalogItem:
    product_id: int
    image_urls: list[str]
    categories: list[str] = field(default_factory=list)


def _split(value: str | None) -> list[str]:
    return [v.strip() for v in (value or "").split(_LIST_SEP) if v.strip()]


def read_csv(path: Path | str) -> Iterator[CatalogItem]:
    """CSV with columns ``product_id,image_urls,categories``.

    Multiple image URLs / categories are separated with ``|``.
    """
    with open(path, newline="", encoding="utf-8-sig") as fh:
        for row in csv.DictReader(fh):
            urls = _split(row.get("image_urls") or row.get("image_url"))
            if row.get("product_id") and urls:
                yield CatalogItem(int(row["product_id"]), urls, _split(row.get("categories")))


def read_json(path: Path | str) -> Iterator[CatalogItem]:
    """JSON array of ``{"product_id": 1, "image_urls": [...], "categories": [...]}``."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    for obj in data:
        urls = obj.get("image_urls") or ([obj["image_url"]] if obj.get("image_url") else [])
        if obj.get("product_id") and urls:
            yield CatalogItem(int(obj["product_id"]), list(urls), list(obj.get("categories", [])))


def woocommerce_product_to_item(product: dict, max_images: int = 5) -> CatalogItem | None:
    """Map a WooCommerce REST ``product`` object to a :class:`CatalogItem`."""
    urls = [img["src"] for img in product.get("images", []) if img.get("src")][:max_images]
    if not urls:
        return None
    cats = [c["name"] for c in product.get("categories", []) if c.get("name")]
    return CatalogItem(int(product["id"]), urls, cats)


class WooCommerceSource:
    """Iterates published products through ``/wp-json/wc/v3/products``.

    Credentials are a *read-only* WooCommerce REST key pair, sent with HTTP
    Basic auth over HTTPS (never put them in the query string, where they end
    up in access logs).
    """

    def __init__(
        self,
        store_url: str,
        consumer_key: str,
        consumer_secret: str,
        *,
        per_page: int = 100,
        max_images: int = 5,
        client: httpx.Client | None = None,
    ) -> None:
        if not store_url.startswith("https://"):
            raise ValueError("store_url must use https:// (credentials are sent with every request)")
        self.base = store_url.rstrip("/") + "/wp-json/wc/v3/products"
        self.per_page = per_page
        self.max_images = max_images
        self.client = client or httpx.Client(timeout=30, auth=(consumer_key, consumer_secret))

    def __iter__(self) -> Iterator[CatalogItem]:
        page = 1
        while True:
            r = self.client.get(self.base, params={"status": "publish", "per_page": self.per_page, "page": page})
            r.raise_for_status()
            products = r.json()
            for p in products:
                item = woocommerce_product_to_item(p, self.max_images)
                if item:
                    yield item
            total_pages = int(r.headers.get("X-WP-TotalPages", page))
            if not products or page >= total_pages:
                break
            page += 1
