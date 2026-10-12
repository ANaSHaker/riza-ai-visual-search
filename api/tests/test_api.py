import json

from fastapi.testclient import TestClient

from .conftest import png_bytes, solid


def _index(client, pid, color, cats=()):
    r = client.post(
        "/v1/index",
        json={"product_id": pid, "image_url": f"https://cdn.example.com/{color}.jpg", "categories": list(cats)},
    )
    assert r.status_code == 200, r.text


def _upload(color, size=(64, 64)):
    return {"image": ("q.png", png_bytes(solid(color, size)), "image/png")}


def test_health_is_public_and_has_no_catalogue_data(client):
    r = TestClient(client.app).get("/health")  # no API key
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok" and body["detector_loaded"] is False
    assert set(body) == {"status", "version", "embedding_model", "detector_model", "detector_loaded", "vectors"}


def test_protected_routes_require_api_key(client):
    anon = TestClient(client.app)
    assert anon.get("/v1/index/stats").status_code == 401
    assert anon.get("/v1/index/stats", headers={"X-API-Key": "wrong"}).status_code == 401
    assert client.get("/v1/index/stats").status_code == 200


def test_index_then_search_ranks_by_visual_similarity(client):
    _index(client, 1, "red", ["Women", "Dresses"])
    _index(client, 2, "orange", ["Bags"])
    _index(client, 3, "blue", ["Shoes"])

    r = client.post("/v1/search", files=_upload("red"), data={"top_k": "5"})
    assert r.status_code == 200
    body = r.json()
    ids = [h["product_id"] for h in body["results"]]
    assert ids[0] == 1 and 3 not in ids  # blue is below the 0.5 threshold
    assert body["total_indexed"] == 3 and body["domain"] == "fashion" and body["min_score_used"] == 0.5


def test_category_hint_reorders_results(client):
    _index(client, 1, "red", ["Bags"])
    _index(client, 2, "orange", ["Evening Dresses"])
    r = client.post("/v1/search", files=_upload("red"), data={"category_hint": "dress"})
    assert [h["product_id"] for h in r.json()["results"]] == [2, 1]


def test_general_domain_uses_stricter_threshold(client):
    r = client.post("/v1/search", files=_upload("red"), data={"domain": "general"})
    assert r.json()["min_score_used"] == 0.6


def test_search_with_bbox_crops_the_region(client):
    _index(client, 1, "red")
    _index(client, 2, "blue")
    # Left half blue, right half red: searching the right half must find red.
    img = solid("blue", (100, 50))
    img.paste(solid("red", (50, 50)), (50, 0))
    files = {"image": ("q.png", png_bytes(img), "image/png")}
    r = client.post("/v1/search", files=files, data={"bbox": json.dumps([55, 5, 95, 45])})
    assert r.json()["results"][0]["product_id"] == 1


def test_invalid_inputs(client):
    assert client.post("/v1/search", files={"image": ("x.png", b"nope", "image/png")}).status_code == 422
    assert client.post("/v1/search", files=_upload("red"), data={"bbox": "[1,2]"}).status_code == 422
    bad = client.post("/v1/index", json={"product_id": 9, "image_url": "https://cdn.example.com/missing.jpg"})
    assert bad.status_code == 422


def test_detect_returns_items_and_falls_back_to_whole_image(client, detector):
    r = client.post("/v1/detect", files=_upload("red", (80, 120)))
    body = r.json()
    assert body["image_size"] == [80, 120]
    assert body["items"][0]["label"] == "Dress" and body["items"][0]["domain"] == "fashion"

    detector.detections = []
    body = client.post("/v1/detect", files=_upload("red", (80, 120))).json()
    assert body["items"][0]["label"] == "Product"
    assert body["items"][0]["bbox"] == [0.0, 0.0, 80.0, 120.0]


def test_similar_products_excludes_itself(client):
    _index(client, 1, "red")
    _index(client, 2, "orange")
    _index(client, 3, "blue")
    r = client.get("/v1/products/1/similar")
    assert [h["product_id"] for h in r.json()["results"]] == [2]
    assert client.get("/v1/products/999/similar").status_code == 404


def test_batch_delete_and_rebuild(client):
    items = [
        {"product_id": 1, "image_url": "https://cdn.example.com/red-1.jpg"},
        {"product_id": 1, "image_url": "https://cdn.example.com/red-2.jpg"},
        {"product_id": 2, "image_url": "https://cdn.example.com/nothing.jpg"},
    ]
    body = client.post("/v1/index/batch", json={"items": items}).json()
    assert (body["indexed"], body["failed"]) == (2, 1)
    assert client.get("/v1/index/stats").json()["products"] == 1

    assert client.delete("/v1/index/products/1").json() == {"removed": 2}
    assert client.post("/v1/index/rebuild").json() == {"vectors": 0}


def test_vectors_survive_restart(settings, detector, monkeypatch):
    from app.main import create_app
    from app.services.container import build_container

    from .conftest import API_KEY, FakeEmbedder, fake_fetch

    monkeypatch.setattr("app.services.indexing_service.fetch_image", fake_fetch)

    def make():
        return create_app(
            settings, container_factory=lambda s: build_container(s, embedder=FakeEmbedder(), detector=detector)
        )

    with TestClient(make(), headers={"X-API-Key": API_KEY}) as c:
        _index(c, 1, "red")
    with TestClient(make(), headers={"X-API-Key": API_KEY}) as c:
        assert c.get("/health").json()["vectors"] == 1
