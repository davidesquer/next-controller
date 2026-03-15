from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.auth import rfid
from app.auth.router import router as auth_router
from app.deck import manager as deck_manager
from app.deck.router import router as deck_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    rfid.init(
        on_unlock=deck_manager.on_rfid_unlock,
        on_register=deck_manager.on_rfid_register,
        on_denied=deck_manager.on_rfid_denied,
    )
    deck_manager.start()
    yield
    # Shutdown
    deck_manager.close_deck()
    rfid.cleanup()


app = FastAPI(title="Next Controller", lifespan=lifespan)
app.include_router(auth_router)
app.include_router(deck_router)


@app.get("/")
def root():
    from app.deck import state

    d = state.deck
    connected = d is not None and d.is_open()
    return {
        "status": "ok",
        "deck_connected": connected,
        "locked": state.locked,
        "current_page": state.current_page,
    }
