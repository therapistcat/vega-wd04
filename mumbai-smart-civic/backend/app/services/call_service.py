def parse_call_to_complaint(transcript: str) -> dict:
    """
    Parses a call transcript into structured complaint data.
    In a real-world scenario, this would use an LLM or more advanced NLP.
    For now, we use a robust heuristic-based approach.
    """
    if not transcript:
        return {
            "title": "Voice Complaint",
            "description": "Empty transcript received",
            "category": "general",
            "ward": "Unknown Ward"
        }

    # Basic cleaning
    clean_transcript = transcript.strip()
    
    # Title extraction (First sentence or first 80 chars)
    title = clean_transcript.split('.')[0][:80]
    if len(title) < 10 and len(clean_transcript) > 10:
         title = clean_transcript[:80]
    
    # Simple keyword-based category detection
    category = "general"
    lower_transcript = clean_transcript.lower()
    if any(k in lower_transcript for k in ["garbage", "trash", "waste", "dump"]):
        category = "garbage"
    elif any(k in lower_transcript for k in ["road", "pothole", "street", "pavement"]):
        category = "road"
    elif any(k in lower_transcript for k in ["water", "leak", "pipe", "supply"]):
        category = "water"
    elif any(k in lower_transcript for k in ["electricity", "power", "light", "wire"]):
        category = "electricity"
    elif any(k in lower_transcript for k in ["sewage", "drain", "gutter"]):
        category = "sewage"

    # Simple ward detection (looking for patterns like 'A Ward', 'B Ward', etc.)
    import re
    ward_match = re.search(r'([A-Z])\s*Ward', clean_transcript, re.IGNORECASE)
    ward = ward_match.group(0).title() if ward_match else "A Ward" # Default to 'A Ward' for Mumbai

    return {
        "title": title + " (Call)",
        "description": clean_transcript,
        "category": category,
        "ward": ward
    }
