from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.auth import cards, rfid

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    uid: int
    name: str = ""


@router.get("/cards")
def list_cards():
    """List all registered cards."""
    return {"cards": cards.list_all()}


@router.post("/cards")
def add_card(req: RegisterRequest):
    """Manually register a card by UID (e.g. for seeding the first card)."""
    if cards.is_registered(req.uid):
        raise HTTPException(400, "Card already registered")
    entry = cards.register(req.uid, req.name)
    return {"uid": req.uid, **entry}


@router.delete("/cards/{uid}")
def remove_card(uid: int):
    """Unregister a card."""
    if not cards.unregister(uid):
        raise HTTPException(404, "Card not found")
    return {"removed": uid}


@router.post("/register-mode")
def toggle_register_mode():
    """Enter register mode — the next scanned card gets registered."""
    rfid.enter_register_mode()
    return {"register_mode": True}


@router.post("/register-mode/cancel")
def cancel_register_mode():
    rfid.exit_register_mode()
    return {"register_mode": False}


@router.get("/status")
def auth_status():
    return {
        "registered_cards": cards.count(),
        "register_mode": rfid.register_mode,
    }
