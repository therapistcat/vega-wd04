"""
Rule engine — maps (disaster_type, floor_level, location_context) → action list.
Pure function, no I/O, no DB. Easily extendable.
"""
from __future__ import annotations

# ---------------------------------------------------------------------------
# Base action sets per disaster type
# ---------------------------------------------------------------------------
_BASE_RULES: dict[str, list[str]] = {
    "earthquake": [
        "drop_cover_hold",
        "stay_away_windows",
        "avoid_lift",
        "evacuate_after_shaking",
    ],
    "fire": [
        "stay_low",
        "cover_mouth",
        "use_stairs",
        "call_fire_brigade",
        "do_not_open_hot_doors",
    ],
    "flood": [
        "move_to_high_ground",
        "avoid_floodwater",
        "switch_off_electricity",
        "call_emergency",
    ],
    "medical": [
        "call_ambulance",
        "do_not_move_victim",
        "apply_pressure",
        "cpr_if_needed",
        "keep_conscious",
    ],
    "accident": [
        "call_ambulance",
        "do_not_move_victim",
        "apply_pressure",
        "manage_traffic",
        "keep_victim_warm",
    ],
    "generic": [
        "call_emergency",
        "stay_calm",
        "follow_authorities",
        "evacuate_if_told",
    ],
}

# ---------------------------------------------------------------------------
# Context-specific modifiers
# ---------------------------------------------------------------------------
def get_actions(
    disaster_type: str,
    floor_level: int | None = None,
    location_context: str | None = None,
) -> list[str]:
    """
    Return an ordered list of action slugs for the given emergency context.
    Always returns at least the generic fallback list.
    """
    dtype = (disaster_type or "generic").lower().strip()
    actions = list(_BASE_RULES.get(dtype, _BASE_RULES["generic"]))

    # Floor-level modifiers
    if dtype == "earthquake":
        if floor_level and floor_level > 2:
            # High floors: explicitly warn about stairs
            if "evacuate_after_shaking" not in actions:
                actions.append("evacuate_after_shaking")
        if floor_level and floor_level >= 1:
            if "move_to_open_ground" not in actions:
                actions.append("move_to_open_ground")

    if dtype == "fire":
        if floor_level and floor_level > 4:
            # Very high floors: do NOT try to evacuate during active fire
            actions = [a for a in actions if a != "use_stairs"]
            actions.insert(0, "stay_low")
            if "call_fire_brigade" not in actions:
                actions.append("call_fire_brigade")

    # Location modifiers
    loc = (location_context or "").lower()
    if dtype == "flood" and any(w in loc for w in ["basement", "ground floor", "bhumi"]):
        actions.insert(0, "move_to_high_ground")

    if dtype == "earthquake" and any(w in loc for w in ["school", "hospital", "mall", "building"]):
        if "move_to_open_ground" not in actions:
            actions.append("move_to_open_ground")

    # Deduplicate while preserving order
    seen: set[str] = set()
    result: list[str] = []
    for a in actions:
        if a not in seen:
            seen.add(a)
            result.append(a)

    return result
