import json

import httpx
import pytest

from app.catalog.sources import CatalogItem, WooCommerceSource, read_csv, read_json, woocommerce_product_to_item
from scripts.index_catalog import _batched, _pairs


def test_read_csv(tmp_path):
    p = tmp_path / "c.csv"
    p.write_text(
        "product_id,image_urls,categories\n1,https://x/a.jpg|https://x/b.jpg,Women|Dresses\n2,,Bags\n", encoding="utf-8"
    )
    items = list(read_csv(p))
    assert len(items) == 1  # rows without images are skipped
    assert items[0].image_urls == ["https://x/a.jpg", "https://x/b.jpg"]
    assert items[0].categories == ["Women", "Dresses"]


def test_read_json(tmp_path):
    p = tmp_path / "c.json"
    p.write_text(json.dumps([{"product_id": 3, "image_url": "https://x/c.jpg"}]), encoding="utf-8")
    (item,) = read_json(p)
    assert item.product_id == 3 and item.image_urls == ["https://x/c.jpg"] and item.categories == []


def test_woocommerce_mapping_limits_images():
    product = {"id": 7, "images": [{"src": f"https://x/{i}.jpg"} for i in range(9)], "categories": [{"name": "Shoes"}]}
    item = woocommerce_product_to_item(product, max_images=3)
    assert item.product_id == 7 and len(item.image_urls) == 3 and item.categories == ["Shoes"]
    assert woocommerce_product_to_item({"id": 8, "images": []}) is None


def test_woocommerce_source_paginates_with_basic_auth():
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        page = int(request.url.params["page"])
        data = [{"id": page, "images": [{"src": f"https://x/{page}.jpg"}], "categories": []}]
        return httpx.Response(200, json=data, headers={"X-WP-TotalPages": "2"})

    client = httpx.Client(transport=httpx.MockTransport(handler), auth=("ck_test", "cs_test"))
    items = list(WooCommerceSource("https://shop.example.com", "ck_test", "cs_test", client=client))
    assert [i.product_id for i in items] == [1, 2]
    assert all("consumer_key" not in str(r.url) for r in seen)  # creds never in the URL
    assert seen[0].headers["Authorization"].startswith("Basic ")


def test_woocommerce_source_requires_https():
    with pytest.raises(ValueError):
        WooCommerceSource("http://shop.example.com", "k", "s")


def test_pairs_and_batching():
    pairs = list(_pairs([CatalogItem(1, ["a", "b"], ["C"]), CatalogItem(2, ["c"])]))
    assert [p["image_url"] for p in pairs] == ["a", "b", "c"]
    assert [len(b) for b in _batched(pairs, 2)] == [2, 1]
