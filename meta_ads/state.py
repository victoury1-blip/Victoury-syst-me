import json
import os
from datetime import date

STATE_PATH = os.path.join(os.path.dirname(__file__), "..", "state", "budget_state.json")


def load_state():
    if not os.path.exists(STATE_PATH):
        return {}
    with open(STATE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_state(state):
    os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False, sort_keys=True)


def days_since(date_str):
    if not date_str:
        return None
    last = date.fromisoformat(date_str)
    return (date.today() - last).days
