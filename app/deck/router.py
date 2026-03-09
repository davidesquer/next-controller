from fastapi import APIRouter, HTTPException

from app.deck import state
from app.deck.manager import update_keys

router = APIRouter(prefix="/deck", tags=["deck"])


@router.get("/status")
def deck_status():
    d = state.deck
    connected = d is not None and d.is_open()
    return {
        "deck_connected": connected,
        "deck_type": d.deck_type() if connected else None,
        "key_count": d.key_count() if connected else None,
        "locked": state.locked,
        "current_page": state.current_page,
        "numbers_shown": list(range(1 + state.current_page * 5, 6 + state.current_page * 5))
        if state.current_page < state.NUM_PAGES
        else [],
    }


@router.post("/toggle")
def toggle_page():
    d = state.deck
    if d is None or not d.is_open():
        raise HTTPException(503, "No Stream Deck connected")
    if state.locked:
        raise HTTPException(403, "Deck is locked")
    state.current_page = 1 - state.current_page if state.current_page < state.NUM_PAGES else 0
    state.touch()
    update_keys()
    return {
        "current_page": state.current_page,
    }
