from __future__ import annotations

import math
import re
from difflib import SequenceMatcher


_WORD_RE = re.compile(r"[a-z0-9]+")
_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "has",
    "i",
    "in",
    "is",
    "it",
    "my",
    "of",
    "on",
    "or",
    "that",
    "the",
    "there",
    "this",
    "to",
    "was",
    "we",
    "with",
}


def normalize_text(value: str | None) -> str:
    if not value:
        return ""
    return " ".join(_WORD_RE.findall(value.lower()))


def tokenize(value: str | None) -> set[str]:
    normalized = normalize_text(value)
    if not normalized:
        return set()
    return {
        token
        for token in normalized.split(" ")
        if token and token not in _STOPWORDS and len(token) > 1
    }


def jaccard_similarity(text_a: str | None, text_b: str | None) -> float:
    tokens_a = tokenize(text_a)
    tokens_b = tokenize(text_b)
    if not tokens_a or not tokens_b:
        return 0.0
    overlap = len(tokens_a.intersection(tokens_b))
    union = len(tokens_a.union(tokens_b))
    if union == 0:
        return 0.0
    return float(overlap) / float(union)


def sequence_similarity(text_a: str | None, text_b: str | None) -> float:
    a = normalize_text(text_a)
    b = normalize_text(text_b)
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def description_similarity(text_a: str | None, text_b: str | None) -> float:
    seq_score = sequence_similarity(text_a, text_b)
    jac_score = jaccard_similarity(text_a, text_b)
    # Sequence captures phrasing, Jaccard captures keyword overlap.
    return (0.6 * seq_score) + (0.4 * jac_score)


def _distance_score(distance_m: float | None, radius_m: float) -> float:
    if distance_m is None:
        return 0.0
    if radius_m <= 0:
        return 0.0
    ratio = min(max(distance_m, 0.0) / radius_m, 1.0)
    return 1.0 - ratio


def duplicate_score(
    *,
    new_description: str,
    old_description: str,
    new_category: str | None,
    old_category: str | None,
    new_department: str | None,
    old_department: str | None,
    distance_m: float | None,
    radius_m: float,
) -> float:
    text_score = description_similarity(new_description, old_description)
    category_match = 1.0 if normalize_text(new_category) == normalize_text(old_category) else 0.0
    department_match = (
        1.0 if normalize_text(new_department) == normalize_text(old_department) else 0.0
    )
    geo_score = _distance_score(distance_m, radius_m)

    score = (
        (0.65 * text_score)
        + (0.15 * category_match)
        + (0.10 * department_match)
        + (0.10 * geo_score)
    )
    return round(min(max(score, 0.0), 1.0), 4)


def is_duplicate(score: float, threshold: float) -> bool:
    if math.isnan(score):
        return False
    return score >= threshold
