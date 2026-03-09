import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
CARDS_FILE = BASE_DIR / "cards.json"
LOCK_TIMEOUT = 10  # seconds of inactivity before re-locking


def load_cards() -> dict:
    """Load registered cards from disk."""
    if not CARDS_FILE.exists():
        return {}
    with open(CARDS_FILE) as f:
        return json.load(f)


def save_cards(cards: dict):
    """Persist registered cards to disk."""
    with open(CARDS_FILE, "w") as f:
        json.dump(cards, f, indent=2)
