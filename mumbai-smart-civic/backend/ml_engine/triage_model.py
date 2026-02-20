from __future__ import annotations


KEYWORD_DEPARTMENT_MAP = {
    "garbage": "Solid Waste Management",
    "waste": "Solid Waste Management",
    "pothole": "Road Maintenance",
    "road": "Road Maintenance",
    "water": "Water Supply Department",
    "leak": "Water Supply Department",
    "drain": "Sewerage Operations",
    "sewage": "Sewerage Operations",
    "light": "Electrical Department",
    "electricity": "Electrical Department",
}


def predict_department(description: str, category: str) -> str:
    text = f"{category} {description}".lower()
    for keyword, department in KEYWORD_DEPARTMENT_MAP.items():
        if keyword in text:
            return department
    return "General Civic Response"