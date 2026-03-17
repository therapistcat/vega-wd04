"""
ReportLab PDF generator for the AI Emergency Visual Assistant.
Produces a clean, professional PDF using high-quality AI instructional posters (PNG).
"""
from __future__ import annotations

import logging
import uuid
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from app.emergency.assets import (
    DISASTER_COLORS,
    DISASTER_TITLES,
    URGENCY_COLORS,
)

LOGGER = logging.getLogger(__name__)

# Output directories
_BACKEND_DIR = Path(__file__).resolve().parents[2]
GENERATED_DIR = _BACKEND_DIR / "app" / "static" / "generated"
POSTERS_DIR = _BACKEND_DIR / "app" / "static" / "assets" / "posters"

GENERATED_DIR.mkdir(parents=True, exist_ok=True)
POSTERS_DIR.mkdir(parents=True, exist_ok=True)

PAGE_W, PAGE_H = A4  # 595.27 x 841.89 points


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _draw_rounded_rect(
    c: canvas.Canvas,
    x: float,
    y: float,
    width: float,
    height: float,
    radius: float,
    fill_color: tuple[float, float, float],
    stroke_color: tuple[float, float, float] | None = None,
    stroke_width: float = 0,
) -> None:
    """Draw a rounded rectangle with fill."""
    p = c.beginPath()
    p.roundRect(x, y, width, height, radius)
    c.setFillColorRGB(*fill_color)
    if stroke_color:
        c.setStrokeColorRGB(*stroke_color)
        c.setLineWidth(stroke_width)
        c.drawPath(p, fill=1, stroke=1)
    else:
        c.drawPath(p, fill=1, stroke=0)


# ---------------------------------------------------------------------------
# Main generator
# ---------------------------------------------------------------------------

def generate_pdf(
    disaster_type: str,
    urgency_level: str,
    actions: list[str],
    location_context: str | None = None,
    floor_level: int | None = None,
) -> str:
    """
    Generate a visual emergency guide PDF utilizing the high-quality AI comic posters.
    Returns the relative URL path for serving via /static.
    """
    filename = f"emergency_{uuid.uuid4().hex[:12]}.pdf"
    filepath = GENERATED_DIR / filename

    c = canvas.Canvas(str(filepath), pagesize=A4)
    c.setTitle(f"{disaster_type.title()} Emergency Visual Guide")
    c.setAuthor("Mumbai Smart Civic — AI Emergency Assistant")

    # Color palette
    d_rgb = DISASTER_COLORS.get(disaster_type, DISASTER_COLORS["generic"])
    u_rgb = URGENCY_COLORS.get(urgency_level, URGENCY_COLORS["high"])
    disaster_title = DISASTER_TITLES.get(disaster_type, "EMERGENCY")

    # -----------------------------------------------------------------------
    # HEADER BAND
    # -----------------------------------------------------------------------
    header_h = 100
    _draw_rounded_rect(c, 0, PAGE_H - header_h, PAGE_W, header_h, 0, fill_color=d_rgb)

    c.setFillColorRGB(1, 1, 1)
    c.setFont("Helvetica-Bold", 40) # Large bold title
    c.drawString(30, PAGE_H - 45, disaster_title.upper())

    c.setFont("Helvetica", 14)
    c.setFillColorRGB(1, 1, 1, 0.9)
    subtitle = "Proper Step-by-Step AI Visual Guide"
    if location_context:
        subtitle += f"  •  {location_context[:50]}"
    if floor_level:
        subtitle += f"  •  Floor {floor_level}"
    c.drawString(30, PAGE_H - 75, subtitle)

    # Urgency badge
    badge_label = urgency_level.upper() + " ALERT"
    badge_w = 120
    badge_x = PAGE_W - badge_w - 30
    badge_y = PAGE_H - 70
    _draw_rounded_rect(c, badge_x, badge_y, badge_w, 30, 8,
                       fill_color=u_rgb,
                       stroke_color=(1, 1, 1), stroke_width=2)
    c.setFillColorRGB(1, 1, 1)
    c.setFont("Helvetica-Bold", 12)
    c.drawCentredString(badge_x + badge_w / 2, badge_y + 11, badge_label)

    # -----------------------------------------------------------------------
    # PROPER AI POSTER IMAGE
    # -----------------------------------------------------------------------
    # Use the PNG posters which contain the 3-step comic panels
    poster_path = POSTERS_DIR / f"{disaster_type}.png"
    if not poster_path.exists():
        poster_path = POSTERS_DIR / "generic.png"

    # Define centered area (below header, above footer)
    margin = 40
    avail_w = PAGE_W - (margin * 2)
    avail_h = PAGE_H - header_h - 100 # Leave space for footer
    
    if poster_path.exists():
        try:
            # Shift slightly down from header
            img_y = 60 
            c.drawImage(
                str(poster_path),
                x=margin,
                y=img_y,
                width=avail_w,
                height=avail_h,
                preserveAspectRatio=True,
                anchor='c',
                mask='auto'
            )
        except Exception as e:
            LOGGER.error(f"Failed to draw poster {poster_path}: {e}")
            c.setFillColorRGB(0.5, 0.5, 0.5)
            c.setFont("Helvetica-Bold", 18)
            c.drawCentredString(PAGE_W / 2, PAGE_H / 2, "Visual Instructions Unavailable")

    # -----------------------------------------------------------------------
    # FOOTER
    # -----------------------------------------------------------------------
    y_footer = 20
    c.setFillColorRGB(0.9, 0.9, 0.9)
    c.rect(0, 0, PAGE_W, y_footer + 15, fill=1, stroke=0)

    c.setFont("Helvetica-Bold", 9)
    c.setFillColorRGB(0.4, 0.4, 0.4)
    c.drawString(30, y_footer, "Mumbai Smart Civic — AI Visual Assistant")
    c.drawRightString(PAGE_W - 30, y_footer, "POLICE: 100 | FIRE: 101 | AMBULANCE: 108")

    c.save()
    LOGGER.info("Step-by-Step PNG PDF generated: %s", filepath)
    return f"/static/generated/{filename}"
