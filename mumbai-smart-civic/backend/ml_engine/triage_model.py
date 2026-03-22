from __future__ import annotations

from typing import Iterable


DEFAULT_DEPARTMENT = "General Civic Response"


_CATEGORY_DEPARTMENT = {
    "garbage": "Solid Waste Management",
    "waste": "Solid Waste Management",
    "trash": "Solid Waste Management",
    "pothole": "Road Maintenance",
    "road": "Road Maintenance",
    "street": "Road Maintenance",
    "water": "Water Supply Department",
    "leak": "Water Supply Department",
    "sewage": "Sewerage Operations",
    "drain": "Sewerage Operations",
    "electricity": "Electrical Department",
    "light": "Electrical Department",
}

_KEYWORD_RULES: list[tuple[set[str], str]] = [
    ({"garbage", "trash", "dump", "litter", "waste"}, "Solid Waste Management"),
    ({"pothole", "road", "crack", "asphalt"}, "Road Maintenance"),
    ({"water", "leak", "pipeline", "supply"}, "Water Supply Department"),
    ({"sewage", "drain", "overflow", "manhole"}, "Sewerage Operations"),
    ({"electricity", "wire", "streetlight", "power"}, "Electrical Department"),
]


def _tokenize(text: str) -> set[str]:
    return {token.strip(".,!?;:-_()[]{}\"'").lower() for token in text.split() if token.strip()}


def _best_rule(tokens: set[str]) -> str | None:
    best_score = 0
    best_department: str | None = None
    for keywords, department in _KEYWORD_RULES:
        score = len(tokens.intersection(keywords))
        if score > best_score:
            best_score = score
            best_department = department
    return best_department


def predict_department(description: str, category: str) -> str:
    category_norm = (category or "").strip().lower()
    if category_norm in _CATEGORY_DEPARTMENT:
        return _CATEGORY_DEPARTMENT[category_norm]

    tokens = _tokenize(description or "")
    by_description = _best_rule(tokens)
    if by_description:
        return by_description

    return DEFAULT_DEPARTMENT

