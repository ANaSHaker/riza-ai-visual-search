"""Category-aware re-ranking.

Pure visual similarity sometimes ranks a beige *bag* above a beige *dress*
when the shopper selected the dress. In production the fix was simple and
effective: after the similarity search, move products whose category matches
the selected item to the front, keeping score order inside each group.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import TypeVar

from app.index.vector_index import Hit

H = TypeVar("H", bound=Hit)


def _normalise(s: str) -> str:
    return " ".join(s.casefold().split())


def category_matches(categories: Iterable[str], hints: Sequence[str]) -> bool:
    """True when any hint appears (case-insensitively) inside any category name."""
    norm_hints = [_normalise(h) for h in hints if h and h.strip()]
    if not norm_hints:
        return False
    for cat in categories:
        c = _normalise(cat)
        if any(h in c for h in norm_hints):
            return True
    return False


def boost_by_category(hits: Sequence[H], hints: Sequence[str]) -> list[H]:
    """Stable partition: matching-category hits first, each group by score."""
    if not any(h and h.strip() for h in hints):
        return list(hits)
    matched = [h for h in hits if category_matches(h.categories, hints)]
    others = [h for h in hits if not category_matches(h.categories, hints)]
    return matched + others


def filter_by_category(hits: Sequence[H], categories: Sequence[str]) -> list[H]:
    """Hard filter: keep only hits in one of ``categories``."""
    if not categories:
        return list(hits)
    return [h for h in hits if category_matches(h.categories, categories)]
