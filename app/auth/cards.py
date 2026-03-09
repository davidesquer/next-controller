from datetime import datetime, timezone

from app.config import load_cards, save_cards

# In-memory cache, synced to cards.json on changes.
_cards: dict = {}


def init():
    """Load cards from disk into memory."""
    global _cards
    _cards = load_cards()
    print(f"Loaded {len(_cards)} registered card(s).")


def is_registered(uid: int) -> bool:
    return str(uid) in _cards


def register(uid: int, name: str = "") -> dict:
    """Register a new card UID. Returns the card entry."""
    key = str(uid)
    entry = {
        "name": name or f"Card {len(_cards) + 1}",
        "registered_at": datetime.now(timezone.utc).isoformat(),
    }
    _cards[key] = entry
    save_cards(_cards)
    print(f"Registered card {uid} as '{entry['name']}'")
    return entry


def unregister(uid: int) -> bool:
    key = str(uid)
    if key in _cards:
        del _cards[key]
        save_cards(_cards)
        print(f"Unregistered card {uid}")
        return True
    return False


def list_all() -> dict:
    return dict(_cards)


def count() -> int:
    return len(_cards)
