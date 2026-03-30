"""
Major Config Manager
====================
Persists which majors are enabled for training.
Other services import from here to know which majors are active.
"""
import json
import os
from datetime import datetime

CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'saved_models', 'major_config.json')

ALL_MAJORS = {
    0: "Agriculture",
    1: "Architecture",
    2: "Arts",
    3: "Business",
    4: "Education",
    5: "Finance",
    6: "Government",
    7: "Health",
    8: "Hospitality",
    9: "Human Services",
    10: "IT",
    11: "Law",
    12: "Manufacturing",
    13: "Sales",
    14: "Science",
    15: "Transport",
}


def get_enabled_majors() -> list[int]:
    """Return list of enabled major IDs from config file. Defaults to all 16."""
    try:
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, 'r') as f:
                data = json.load(f)
                enabled = data.get("enabled_majors", list(range(16)))
                # Validate: must be subset of 0-15
                return sorted([m for m in enabled if 0 <= m <= 15])
    except Exception:
        pass
    return list(range(16))


def save_enabled_majors(enabled_major_ids: list[int]) -> dict:
    """Save the list of enabled major IDs to config file."""
    enabled = sorted([m for m in enabled_major_ids if 0 <= m <= 15])
    data = {
        "enabled_majors": enabled,
        "updated_at": datetime.now().isoformat()
    }
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, 'w') as f:
        json.dump(data, f, indent=4)
    return data


def get_major_config_for_ui() -> list[dict]:
    """Return full list of all majors with enabled/disabled status for the UI."""
    enabled = set(get_enabled_majors())
    return [
        {
            "id": mid,
            "name": name,
            "enabled": mid in enabled,
        }
        for mid, name in ALL_MAJORS.items()
    ]
