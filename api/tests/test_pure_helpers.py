import pytest
from PIL import Image

from app.index.vector_index import Hit
from app.models.detector import LazyDetector, best_per_label
from app.models.vocabulary import PROMPTS, VOCABULARY
from app.services.images import ImageError, crop_with_padding, decode_image, validate_image_url
from app.services.rerank import boost_by_category, category_matches, filter_by_category

from .conftest import png_bytes, solid


# --- detection post-processing ----------------------------------------------
def test_best_per_label_keeps_top_box_per_label_sorted():
    dets = best_per_label(
        boxes=[[0, 0, 10, 10], [1, 1, 9, 9], [5, 5, 20, 20]],
        scores=[0.3, 0.5, 0.4],
        label_ids=[0, 0, 13],
    )
    assert [d.label.prompt for d in dets] == [PROMPTS[0], PROMPTS[13]]
    assert dets[0].bbox == (1.0, 1.0, 9.0, 9.0)
    assert dets[0].score == 0.5


def test_vocabulary_is_consistent():
    assert len(set(PROMPTS)) == len(PROMPTS)
    assert {v.domain for v in VOCABULARY} == {"fashion", "general"}


def test_lazy_detector_builds_once():
    built = []

    class D:
        def detect(self, image):
            return []

    lazy = LazyDetector(lambda: built.append(1) or D())
    assert not lazy.loaded
    lazy.detect(solid("red"))
    lazy.detect(solid("red"))
    assert lazy.loaded and built == [1]


# --- images -------------------------------------------------------------------
def test_crop_adds_padding_and_clamps_to_image():
    img = Image.new("RGB", (100, 100))
    assert crop_with_padding(img, [10, 10, 60, 60], 0.10).size == (60, 60)  # 5px each side
    assert crop_with_padding(img, [0, 0, 100, 100], 0.10).size == (100, 100)


@pytest.mark.parametrize("bbox", [[10, 10, 5, 50], [1, 2, 3], [200, 200, 300, 300]])
def test_crop_rejects_bad_boxes(bbox):
    with pytest.raises(ImageError):
        crop_with_padding(Image.new("RGB", (100, 100)), bbox)


def test_decode_limits():
    data = png_bytes(solid("red", (50, 50)))
    assert decode_image(data, 10_000_000, 10_000).size == (50, 50)
    with pytest.raises(ImageError):
        decode_image(data, 10, 10_000)  # too many bytes
    with pytest.raises(ImageError):
        decode_image(data, 10_000_000, 100)  # too many pixels
    with pytest.raises(ImageError):
        decode_image(b"not an image", 10_000_000, 10_000)


@pytest.mark.parametrize(
    "url",
    [
        "ftp://example.com/a.jpg",
        "file:///etc/passwd",
        "http://127.0.0.1/a.jpg",
        "http://localhost/a.jpg",
        "http://10.0.0.5/x.png",
    ],
)
def test_url_validation_blocks_ssrf_targets(url):
    with pytest.raises(ImageError):
        validate_image_url(url, allowlist=set())


def test_url_allowlist():
    assert validate_image_url("https://media.example.com/a.jpg", {"media.example.com"})
    with pytest.raises(ImageError):
        validate_image_url("https://evil.example.net/a.jpg", {"media.example.com"})


# --- re-ranking -----------------------------------------------------------------
def _hit(pid, score, cats):
    return Hit(pid, score, f"u{pid}", tuple(cats))


def test_category_boost_is_stable_partition():
    hits = [
        _hit(1, 0.9, ["Bags"]),
        _hit(2, 0.8, ["Women", "Evening Dresses"]),
        _hit(3, 0.7, ["Dresses"]),
        _hit(4, 0.6, []),
    ]
    assert [h.product_id for h in boost_by_category(hits, ["dress"])] == [2, 3, 1, 4]
    assert [h.product_id for h in boost_by_category(hits, [])] == [1, 2, 3, 4]


def test_category_filter_and_matching_is_case_insensitive():
    hits = [_hit(1, 0.9, ["Bags"]), _hit(2, 0.8, ["DRESSES"])]
    assert [h.product_id for h in filter_by_category(hits, ["dresses"])] == [2]
    assert category_matches(["فساتين سهرة"], ["فساتين"])  # Arabic category names work too
