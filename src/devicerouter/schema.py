from typing import Dict, Any

def normalize_schema(doc: Dict[str, Any]) -> Dict[str, Any]:
    doc = dict(doc or {})
    doc.setdefault("devices", {})
    doc.setdefault("current-mount", {})
    if not isinstance(doc["devices"], dict) or not isinstance(doc["current-mount"], dict):
        raise ValueError("Invalid schema JSON: expected 'devices' and 'current-mount' dicts")
    # No heavy validation; just shape.
    return doc

