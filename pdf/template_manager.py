"""Template Management Module.

Registers, persists, and retrieves deterministic field coordinate configurations
for known PDF templates, bypassing OCR/AI search overhead.
"""

import json
import os
from typing import Dict, Any, Optional

TEMPLATE_FILE = "templates.json"


def load_templates() -> Dict[str, Any]:
    """Loads saved templates from disk."""
    if not os.path.exists(TEMPLATE_FILE):
        return {}
    try:
        with open(TEMPLATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_templates(templates: Dict[str, Any]) -> None:
    """Saves template dictionary to disk."""
    with open(TEMPLATE_FILE, "w", encoding="utf-8") as f:
        json.dump(templates, f, indent=2)


def register_template(template_id: str, fields: Dict[str, Any]) -> Dict[str, Any]:
    """Registers a new template configuration."""
    templates = load_templates()
    templates[template_id] = {
        "template_id": template_id,
        "fields": fields
    }
    save_templates(templates)
    return templates[template_id]


def get_template(template_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves a template by template_id."""
    templates = load_templates()
    return templates.get(template_id)
