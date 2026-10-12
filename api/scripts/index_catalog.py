"""Index a product catalogue into the visual search service.

Examples
--------
  # From a CSV/JSON file, pushing to a running API
  python -m scripts.index_catalog csv  products.csv  --api http://127.0.0.1:8000

  # Straight from a WooCommerce store (read-only REST key from the environment)
  export WC_STORE_URL=https://shop.example.com WC_CONSUMER_KEY=ck_... WC_CONSUMER_SECRET=cs_...
  python -m scripts.index_catalog woocommerce --api http://127.0.0.1:8000

  # Without a server: embed locally and write straight into VS_DATA_DIR
  python -m scripts.index_catalog json products.json --direct
"""

from __future__ import annotations

import argparse
import itertools
import os
import sys
from collections.abc import Iterable, Iterator

import httpx

from app.catalog.sources import CatalogItem, WooCommerceSource, read_csv, read_json


def _pairs(items: Iterable[CatalogItem]) -> Iterator[dict]:
    for item in items:
        for url in item.image_urls:
            yield {"product_id": item.product_id, "image_url": url, "categories": item.categories}


def _batched(it: Iterable[dict], n: int) -> Iterator[list[dict]]:
    it = iter(it)
    while chunk := list(itertools.islice(it, n)):
        yield chunk


def push_to_api(items: Iterable[CatalogItem], api: str, api_key: str, batch_size: int) -> tuple[int, int]:
    ok = failed = 0
    headers = {"X-API-Key": api_key} if api_key else {}
    with httpx.Client(base_url=api, timeout=600, headers=headers) as client:
        for chunk in _batched(_pairs(items), batch_size):
            r = client.post("/v1/index/batch", json={"items": chunk})
            r.raise_for_status()
            body = r.json()
            ok, failed = ok + body["indexed"], failed + body["failed"]
            print(f"  indexed {ok}  failed {failed}  (index size {body['total_indexed']})", flush=True)
        client.post("/v1/index/rebuild").raise_for_status()
    return ok, failed


def index_directly(items: Iterable[CatalogItem]) -> tuple[int, int]:
    from app.core.config import get_settings
    from app.services.container import build_container
    from app.services.images import ImageError

    container = build_container(get_settings())
    ok = failed = 0
    try:
        for p in _pairs(items):
            try:
                container.indexing.index_url(p["product_id"], p["image_url"], p["categories"])
                ok += 1
            except ImageError as exc:
                failed += 1
                print(f"  skip product {p['product_id']}: {exc}", file=sys.stderr)
            if (ok + failed) % 50 == 0:
                print(f"  indexed {ok}  failed {failed}", flush=True)
    finally:
        container.close()
    return ok, failed


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("source", choices=["csv", "json", "woocommerce"])
    ap.add_argument("path", nargs="?", help="File path for csv/json sources")
    target = ap.add_mutually_exclusive_group(required=True)
    target.add_argument("--api", help="Base URL of a running visual search API")
    target.add_argument("--direct", action="store_true", help="Embed locally (loads the model in this process)")
    ap.add_argument("--batch-size", type=int, default=50)
    ap.add_argument("--max-images", type=int, default=5, help="Images per product (woocommerce)")
    args = ap.parse_args(argv)

    if args.source in {"csv", "json"}:
        if not args.path:
            ap.error(f"{args.source} source needs a file path")
        items: Iterable[CatalogItem] = read_csv(args.path) if args.source == "csv" else read_json(args.path)
    else:
        items = WooCommerceSource(
            os.environ["WC_STORE_URL"],
            os.environ["WC_CONSUMER_KEY"],
            os.environ["WC_CONSUMER_SECRET"],
            max_images=args.max_images,
        )

    if args.direct:
        ok, failed = index_directly(items)
    else:
        ok, failed = push_to_api(items, args.api, os.environ.get("VS_API_KEY", ""), args.batch_size)
    print(f"Done: {ok} images indexed, {failed} failed.")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
