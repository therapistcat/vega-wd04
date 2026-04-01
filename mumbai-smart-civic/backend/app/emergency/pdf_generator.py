"""
ReportLab PDF generator — AI Emergency Visual Assistant (Illiterate-first design).

Layout:
  - Full-page design with large header
  - Comic poster image (disaster-specific PNG) — visually prominent
  - 3 step strips below poster with numbered label + personalized AI text
  - Clear emergency contacts footer
"""
from __future__ import annotations

import logging
import uuid
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas as rl_canvas

from app.emergency.assets import (
    DISASTER_COLORS,
    DISASTER_TITLES,
    URGENCY_COLORS,
    ACTION_LABELS,
)

LOGGER = logging.getLogger(__name__)

_BACKEND_DIR  = Path(__file__).resolve().parents[2]
GENERATED_DIR = _BACKEND_DIR / "app" / "static" / "generated"
POSTERS_DIR   = _BACKEND_DIR / "app" / "static" / "assets" / "posters"

GENERATED_DIR.mkdir(parents=True, exist_ok=True)

PAGE_W, PAGE_H = A4   # 595 x 842 pt

_DARK_ACCENT: dict[str, tuple[float, float, float]] = {
    "earthquake": (0.75, 0.28, 0.06),
    "fire":       (0.80, 0.10, 0.06),
    "flood":      (0.05, 0.38, 0.75),
    "medical":    (0.05, 0.58, 0.35),
    "accident":   (0.75, 0.45, 0.00),
    "generic":    (0.28, 0.28, 0.75),
}

_NUM_BG: dict[str, tuple[float, float, float]] = {
    "earthquake": (0.95, 0.88, 0.82),
    "fire":       (0.98, 0.88, 0.86),
    "flood":      (0.86, 0.92, 0.98),
    "medical":    (0.86, 0.98, 0.92),
    "accident":   (0.98, 0.94, 0.82),
    "generic":    (0.90, 0.90, 0.98),
}

STEP_ICONS: dict[str, str] = {
    # Earthquake
    "drop_cover_hold":        "DUCK",
    "avoid_lift":             "NO LIFT",
    "stay_away_windows":      "STEP BACK",
    "evacuate_after_shaking": "RUN OUT",
    "move_to_open_ground":    "GO OPEN",
    # Fire
    "stay_low":               "CRAWL",
    "cover_mouth":            "COVER",
    "use_stairs":             "STAIRS",
    "call_fire_brigade":      "CALL 101",
    "do_not_open_hot_doors":  "STOP",
    # Flood
    "move_to_high_ground":    "GO UP",
    "avoid_floodwater":       "AVOID",
    "call_emergency":         "CALL 112",
    "do_not_walk_flood":      "STOP",
    "switch_off_electricity": "POWER OFF",
    # Medical / Accident
    "call_ambulance":         "CALL 108",
    "do_not_move_victim":     "DON'T MOVE",
    "apply_pressure":         "PRESS",
    "cpr_if_needed":          "CPR",
    "keep_conscious":         "TALK",
    "manage_traffic":         "SIGNAL",
    "keep_victim_warm":       "KEEP WARM",
    # Generic
    "stay_calm":              "BREATHE",
    "follow_authorities":     "FOLLOW",
    "evacuate_if_told":       "EVACUATE",
}

STEP_COLORS = [
    (0.13, 0.60, 0.33),   # green   – Step 1
    (0.90, 0.55, 0.05),   # amber   – Step 2
    (0.82, 0.15, 0.15),   # red     – Step 3
]


def _draw_rounded_rect(
    c: rl_canvas.Canvas,
    x: float, y: float, w: float, h: float, r: float,
    fill: tuple, stroke: tuple | None = None, sw: float = 0,
) -> None:
    p = c.beginPath()
    p.roundRect(x, y, w, h, r)
    c.setFillColorRGB(*fill)
    if stroke:
        c.setStrokeColorRGB(*stroke)
        c.setLineWidth(sw)
        c.drawPath(p, fill=1, stroke=1)
    else:
        c.drawPath(p, fill=1, stroke=0)


def _wrap(text: str, max_ch: int = 52) -> list[str]:
    words, lines, cur = text.split(), [], ""
    for w in words:
        if len(cur) + len(w) + 1 <= max_ch:
            cur = f"{cur} {w}".lstrip()
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines or [""]


def generate_pdf(
    disaster_type: str,
    urgency_level: str,
    actions: list[str],
    location_context: str | None = None,
    floor_level: int | None = None,
    step_descriptions: list[str] | None = None,
) -> str:
    filename = f"emergency_{uuid.uuid4().hex[:12]}.pdf"
    filepath = GENERATED_DIR / filename

    c = rl_canvas.Canvas(str(filepath), pagesize=A4)
    c.setTitle(f"{disaster_type.title()} Emergency Visual Guide")
    c.setAuthor("Mumbai Smart Civic — AI Emergency Assistant")

    d_rgb   = DISASTER_COLORS.get(disaster_type, DISASTER_COLORS["generic"])
    u_rgb   = URGENCY_COLORS.get(urgency_level, URGENCY_COLORS["high"])
    dark    = _DARK_ACCENT.get(disaster_type, _DARK_ACCENT["generic"])
    title   = DISASTER_TITLES.get(disaster_type, "EMERGENCY")

    top_actions = (actions or [])[:3]
    while len(top_actions) < 3:
        top_actions.append("stay_calm")

    descs = list(step_descriptions or [])
    while len(descs) < 3:
        descs.append(ACTION_LABELS.get(top_actions[len(descs)], "Stay calm."))
    descs = descs[:3]

    # ===================================================================
    # HEADER  (height 100)
    # ===================================================================
    HDR_H = 100
    _draw_rounded_rect(c, 0, PAGE_H - HDR_H, PAGE_W, HDR_H, 0, fill=d_rgb)

    # SOS box
    _draw_rounded_rect(c, 22, PAGE_H - 82, 58, 58, 6, fill=(1, 1, 1))
    c.setFillColorRGB(*dark)
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(51, PAGE_H - 55, "SOS")

    # Title
    c.setFillColorRGB(1, 1, 1)
    c.setFont("Helvetica-Bold", 36)
    c.drawString(94, PAGE_H - 50, title)

    # Subtitle
    subtitle = "AI Emergency Visual Guide"
    if location_context:
        subtitle += f"  •  {location_context[:45]}"
    if floor_level:
        subtitle += f"  •  Floor {floor_level}"
    c.setFont("Helvetica", 12)
    c.setFillColorRGB(1, 1, 1)
    c.drawString(94, PAGE_H - 78, subtitle)

    # Urgency badge (top-right)
    badge_lbl = urgency_level.upper() + " ALERT"
    bw = 126
    bx = PAGE_W - bw - 22
    by = PAGE_H - 78
    _draw_rounded_rect(c, bx, by, bw, 28, 6, fill=u_rgb,
                       stroke=(1, 1, 1), sw=1.5)
    c.setFillColorRGB(1, 1, 1)
    c.setFont("Helvetica-Bold", 11)
    c.drawCentredString(bx + bw / 2, by + 9, badge_lbl)

    # ===================================================================
    # COMIC POSTER IMAGE  (disaster-specific visual)
    # ===================================================================
    poster_path = POSTERS_DIR / f"{disaster_type}.png"
    if not poster_path.exists():
        poster_path = POSTERS_DIR / "fire.png"   # fallback to fire (not earthquake)
        if not poster_path.exists():
            poster_path = None

    FOOTER_H   = 36
    STEP_H     = 72      # height of each step strip
    STEP_GAP   = 8
    STEPS_AREA = 3 * STEP_H + 2 * STEP_GAP + 18   # 3 strips + padding
    MARGIN     = 24

    poster_top = PAGE_H - HDR_H - 10
    poster_bot = FOOTER_H + STEPS_AREA + 14

    if poster_path and poster_path.exists():
        pw = PAGE_W - MARGIN * 2
        ph = poster_top - poster_bot
        try:
            c.drawImage(
                str(poster_path),
                x=MARGIN, y=poster_bot,
                width=pw, height=ph,
                preserveAspectRatio=True,
                anchor='c',
                mask='auto',
            )
        except Exception as exc:
            LOGGER.error("Poster draw failed: %s", exc)
            _draw_rounded_rect(c, MARGIN, poster_bot, pw, ph, 8,
                               fill=(0.93, 0.93, 0.93))
            c.setFillColorRGB(0.5, 0.5, 0.5)
            c.setFont("Helvetica-Bold", 14)
            c.drawCentredString(PAGE_W / 2, poster_bot + ph / 2, "Visual Unavailable")
    else:
        pw = PAGE_W - MARGIN * 2
        ph = poster_top - poster_bot
        _draw_rounded_rect(c, MARGIN, poster_bot, pw, ph, 8,
                           fill=(0.93, 0.93, 0.93))

    # ===================================================================
    # STEP STRIPS  (3 numbered cards below the poster)
    # ===================================================================
    nb    = _NUM_BG.get(disaster_type, _NUM_BG["generic"])
    sw    = PAGE_W - MARGIN * 2      # strip width
    num_w = 64                        # left number column
    txt_x = MARGIN + num_w + 12

    for i, (action, desc) in enumerate(zip(top_actions, descs)):
        sy = (FOOTER_H + 6) + (2 - i) * (STEP_H + STEP_GAP)

        # Strip background
        _draw_rounded_rect(c, MARGIN, sy, sw, STEP_H, 7,
                           fill=nb, stroke=dark, sw=1.2)

        # Number badge
        sc = STEP_COLORS[i]
        _draw_rounded_rect(c, MARGIN + 6, sy + 8, num_w - 12, STEP_H - 16, 6,
                           fill=sc)
        c.setFillColorRGB(1, 1, 1)
        c.setFont("Helvetica-Bold", 8)
        c.drawCentredString(MARGIN + 6 + (num_w - 12) / 2, sy + STEP_H - 22,
                            f"STEP {i + 1}")
        c.setFont("Helvetica-Bold", 26)
        c.drawCentredString(MARGIN + 6 + (num_w - 12) / 2, sy + 14, str(i + 1))

        # Short icon word (large, bold)
        icon_word = STEP_ICONS.get(action, action.replace("_", " ").upper()[:8])
        c.setFillColorRGB(*dark)
        c.setFont("Helvetica-Bold", 15)
        c.drawString(txt_x, sy + STEP_H - 20, icon_word)

        # Action label
        label = ACTION_LABELS.get(action, action.replace("_", " ").title())
        c.setFont("Helvetica-Bold", 11)
        c.setFillColorRGB(*dark)
        c.drawString(txt_x, sy + STEP_H - 36, label)

        # AI personalized description (wrapped, smaller)
        c.setFont("Helvetica", 9)
        c.setFillColorRGB(0.2, 0.2, 0.2)
        dl = _wrap(desc, max_ch=72)
        ty = sy + STEP_H - 50
        for line in dl[:2]:     # max 2 lines
            c.drawString(txt_x, ty, line)
            ty -= 12

    # ===================================================================
    # FOOTER
    # ===================================================================
    c.setFillColorRGB(0.12, 0.12, 0.12)
    c.rect(0, 0, PAGE_W, FOOTER_H - 2, fill=1, stroke=0)
    c.setFont("Helvetica-Bold", 8)
    c.setFillColorRGB(0.9, 0.9, 0.9)
    c.drawString(24, 12, "Mumbai Smart Civic — AI Emergency Assistant")
    c.drawRightString(PAGE_W - 24, 12,
                      "POLICE: 100  |  FIRE: 101  |  AMBULANCE: 108  |  HELPLINE: 112")

    c.save()
    LOGGER.info("Comic PDF generated (%s): %s", disaster_type, filepath)
    return f"/static/generated/{filename}"
