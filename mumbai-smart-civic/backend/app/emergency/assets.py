"""
Action asset map — inline SVG icons for each emergency action.
No external files needed; pure Python strings.
"""
from __future__ import annotations

# Each value is a minimal SVG (viewBox="0 0 64 64") suitable for
# rendering inside ReportLab via svglib or direct drawing calls.
# We store them as raw SVG strings; the PDF generator will rasterize.

ACTION_LABELS: dict[str, str] = {
    # Earthquake
    "drop_cover_hold":       "Drop, Cover & Hold On",
    "avoid_lift":            "Do NOT Use Lifts",
    "stay_away_windows":     "Stay Away from Windows",
    "evacuate_after_shaking":"Evacuate After Shaking Stops",
    "move_to_open_ground":   "Move to Open Ground",
    # Fire
    "stay_low":              "Stay Low — Crawl Under Smoke",
    "cover_mouth":           "Cover Mouth & Nose",
    "use_stairs":            "Use Stairs Only",
    "call_fire_brigade":     "Call Fire Brigade: 101",
    "do_not_open_hot_doors": "Do NOT Open Hot Doors",
    # Flood
    "move_to_high_ground":   "Move to High Ground",
    "avoid_floodwater":      "Do NOT Walk in Floodwater",
    "call_emergency":        "Call Emergency: 112",
    "do_not_walk_flood":     "Avoid Flooded Streets",
    "switch_off_electricity":"Switch Off Electricity",
    # Medical / Accident
    "call_ambulance":        "Call Ambulance: 108",
    "do_not_move_victim":    "Do NOT Move the Victim",
    "apply_pressure":        "Apply Pressure to Wound",
    "cpr_if_needed":         "Perform CPR If Trained",
    "keep_conscious":        "Keep Victim Conscious",
    "manage_traffic":        "Signal Others to Slow Down",
    "keep_victim_warm":      "Keep Victim Warm",
    # Generic
    "stay_calm":             "Stay Calm",
    "follow_authorities":    "Follow Authority Instructions",
    "evacuate_if_told":      "Evacuate If Instructed",
}

# Emoji-based icons (unicode, rendered as text in PDF)
ACTION_EMOJI: dict[str, str] = {
    "drop_cover_hold":       "🛡️",
    "avoid_lift":            "🚫",
    "stay_away_windows":     "⚠️",
    "evacuate_after_shaking":"🚶",
    "move_to_open_ground":   "🌿",
    "stay_low":              "⬇️",
    "cover_mouth":           "😷",
    "use_stairs":            "🪜",
    "call_fire_brigade":     "🚒",
    "do_not_open_hot_doors": "🔥",
    "move_to_high_ground":   "⛰️",
    "avoid_floodwater":      "🌊",
    "call_emergency":        "📞",
    "do_not_walk_flood":     "🚫",
    "switch_off_electricity":"⚡",
    "call_ambulance":        "🚑",
    "do_not_move_victim":    "🛑",
    "apply_pressure":        "🩹",
    "cpr_if_needed":         "❤️",
    "keep_conscious":        "👁️",
    "manage_traffic":        "✋",
    "keep_victim_warm":      "🧥",
    "stay_calm":             "🧘",
    "follow_authorities":    "👮",
    "evacuate_if_told":      "🚪",
}

DISASTER_COLORS: dict[str, tuple[float, float, float]] = {
    "earthquake": (0.85, 0.33, 0.10),   # deep orange
    "fire":       (0.90, 0.18, 0.18),   # red
    "flood":      (0.10, 0.45, 0.85),   # blue
    "medical":    (0.10, 0.72, 0.45),   # green
    "accident":   (0.95, 0.60, 0.10),   # amber
    "generic":    (0.40, 0.40, 0.90),   # indigo
}

DISASTER_TITLES: dict[str, str] = {
    "earthquake": "EARTHQUAKE",
    "fire":       "FIRE",
    "flood":      "FLOOD",
    "medical":    "MEDICAL EMERGENCY",
    "accident":   "ACCIDENT",
    "generic":    "EMERGENCY",
}

URGENCY_COLORS: dict[str, tuple[float, float, float]] = {
    "critical": (0.90, 0.10, 0.10),
    "high":     (0.95, 0.50, 0.10),
    "medium":   (0.95, 0.80, 0.10),
    "low":      (0.25, 0.75, 0.40),
}
