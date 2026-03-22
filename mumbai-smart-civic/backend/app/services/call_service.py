import re


LOCATION_PATTERN = re.compile(
    r"\b(?:at|near|in|on|around|beside|opposite)\s+([^.,;\n]+)",
    re.IGNORECASE,
)
LABELED_FIELD_PATTERNS = {
    "problem": re.compile(r"\b(?:problem|issue|complaint)\s*[:\-]\s*([^.;\n]+)", re.IGNORECASE),
    "location": re.compile(r"\b(?:location|area|landmark|place)\s*[:\-]\s*([^.;\n]+)", re.IGNORECASE),
    "details": re.compile(r"\b(?:details|description|note)\s*[:\-]\s*([^;\n]+)", re.IGNORECASE),
}


def _clean_text(value: str | None) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _extract_field(text: str, field: str) -> str | None:
    pattern = LABELED_FIELD_PATTERNS[field]
    match = pattern.search(text)
    if match:
        return _clean_text(match.group(1))
    return None


def _detect_category(text: str) -> str:
    lower_text = text.lower()
    if any(keyword in lower_text for keyword in ["garbage", "trash", "waste", "dump", "rubbish"]):
        return "garbage"
    if any(keyword in lower_text for keyword in ["road", "pothole", "street", "pavement"]):
        return "road"
    if any(keyword in lower_text for keyword in ["water", "leak", "pipe", "supply"]):
        return "water"
    if any(keyword in lower_text for keyword in ["electricity", "power", "light", "wire"]):
        return "electricity"
    if any(keyword in lower_text for keyword in ["sewage", "drain", "gutter", "overflow"]):
        return "sewage"
    return "general"


def _detect_ward(text: str) -> str:
    ward_match = re.search(r"\b([A-Z])\s*Ward\b", text, re.IGNORECASE)
    if ward_match:
        return ward_match.group(0).title()
    return "A Ward"


def _extract_location(text: str, ward: str) -> str:
    labeled_location = _extract_field(text, "location")
    if labeled_location:
        return labeled_location

    match = LOCATION_PATTERN.search(text)
    if match:
        return _clean_text(match.group(1))

    if ward:
        return ward
    return "Unknown Location"


def parse_call_to_complaint(summary: str, transcript: str | None = None) -> dict:
    """
    Parse a voice call summary/transcript into structured complaint data.

    The webhook now prefers Vapi's end-of-call summary and falls back to the
    transcript if needed.
    """
    clean_summary = _clean_text(summary)
    clean_transcript = _clean_text(transcript)
    source_text = clean_summary or clean_transcript

    if not source_text:
        return {
            "title": "Voice Complaint",
            "description": "Empty call summary received",
            "category": "general",
            "ward": "Unknown Ward",
            "landmark": None,
            "problem": "Unknown issue",
            "location": "Unknown Location",
            "details": "No summary or transcript available",
            "summary": "",
        }

    first_sentence = source_text.split(".")[0].strip() or source_text[:80]
    problem = _extract_field(source_text, "problem") or first_sentence[:120]
    ward = _detect_ward(f"{clean_summary} {clean_transcript}")
    location = _extract_location(f"{clean_summary} {clean_transcript}", ward)
    details = _extract_field(source_text, "details") or clean_transcript or source_text
    category = _detect_category(f"{clean_summary} {clean_transcript}")

    description_parts = [problem]
    if location and location.lower() not in {"unknown location", ward.lower()}:
        description_parts.append(f"Location: {location}")
    if details and details != problem:
        description_parts.append(f"Details: {details}")

    description = " | ".join(description_parts)

    return {
        "title": f"{problem[:80]} (Call)",
        "description": description,
        "category": category,
        "ward": ward,
        "landmark": location if location != ward else None,
        "problem": problem,
        "location": location,
        "details": details,
        "summary": clean_summary or source_text,
    }
