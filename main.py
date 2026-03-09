import random
import threading
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI
from PIL import Image, ImageDraw, ImageFont
from StreamDeck.DeviceManager import DeviceManager
from StreamDeck.Devices.StreamDeckMini import StreamDeckMini
from StreamDeck.ImageHelpers import PILHelper
from StreamDeck.ProductIDs import USBProductIDs, USBVendorIDs

# ---------------------------------------------------------------------------
# Register Stream Deck Mini hardware revision (PID 0x00b3) not yet known
# to the upstream streamdeck library.
# ---------------------------------------------------------------------------
USBProductIDs.USB_PID_STREAMDECK_MINI_V2 = 0x00b3

_original_enumerate = DeviceManager.enumerate


def _patched_enumerate(self):
    """Enumerate devices, including the unregistered Mini PID 0x00b3."""
    devices = _original_enumerate(self)
    extra = self.transport.enumerate(
        vid=USBVendorIDs.USB_VID_ELGATO,
        pid=USBProductIDs.USB_PID_STREAMDECK_MINI_V2,
    )
    devices.extend(StreamDeckMini(d) for d in extra)
    return devices


DeviceManager.enumerate = _patched_enumerate

# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------
deck = None
current_page = 0  # 0 → numbers 1-5, 1 → numbers 6-10
locked = True
pin_progress = 0  # how many correct digits entered (0-6)
shuffled_keys = []  # key index → displayed digit
last_activity = 0.0  # monotonic timestamp of last key press while unlocked
LOCK_TIMEOUT = 10  # seconds of inactivity before re-locking


# ---------------------------------------------------------------------------
# Image helpers
# ---------------------------------------------------------------------------
def _font(size: int = 28) -> ImageFont.FreeTypeFont:
    """Try to load a system font; fall back to PIL default."""
    for path in (
        "/System/Library/Fonts/Helvetica.ttc",          # macOS
        "/System/Library/Fonts/SFNSMono.ttf",           # macOS alt
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",  # Linux
        "C:\\Windows\\Fonts\\arial.ttf",                 # Windows
    ):
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _make_number_image(deck_dev, number: int) -> bytes:
    """Render a number centered on a key-sized image."""
    img = PILHelper.create_key_image(deck_dev, background="black")
    draw = ImageDraw.Draw(img)
    draw.text(
        (img.width / 2, img.height / 2),
        text=str(number),
        font=_font(36),
        anchor="mm",
        fill="white",
    )
    return PILHelper.to_native_key_format(deck_dev, img)


def _make_folder_image(deck_dev, is_page_two: bool) -> bytes:
    """Draw a simple folder icon with a page indicator."""
    img = PILHelper.create_key_image(deck_dev, background="black")
    draw = ImageDraw.Draw(img)
    w, h = img.size

    # --- folder shape ---
    pad = int(w * 0.15)
    folder_top = int(h * 0.25)
    tab_w = int(w * 0.35)
    tab_h = int(h * 0.10)
    color = "#f0c040" if not is_page_two else "#40a0f0"

    # tab
    draw.rectangle(
        [pad, folder_top - tab_h, pad + tab_w, folder_top],
        fill=color,
    )
    # body
    draw.rectangle(
        [pad, folder_top, w - pad, int(h * 0.72)],
        fill=color,
    )

    # page label at the bottom
    label = "6-10" if is_page_two else "1-5"
    draw.text(
        (w / 2, h * 0.88),
        text=label,
        font=_font(14),
        anchor="mm",
        fill="white",
    )

    return PILHelper.to_native_key_format(deck_dev, img)


def _make_red_image(deck_dev) -> bytes:
    """Render a solid red key image."""
    img = PILHelper.create_key_image(deck_dev, background="red")
    return PILHelper.to_native_key_format(deck_dev, img)


def _shuffle_lock_screen():
    """Generate a new shuffled digit layout and render it on all keys."""
    global shuffled_keys, pin_progress
    pin_progress = 0
    shuffled_keys = random.sample(range(1, 7), 6)
    if deck is None or not deck.is_open():
        return
    with deck:
        for i in range(6):
            deck.set_key_image(i, _make_number_image(deck, shuffled_keys[i]))


def _flash_red():
    """Flash all keys red, then reshuffle the lock screen."""
    if deck is None or not deck.is_open():
        return
    red = _make_red_image(deck)
    with deck:
        for i in range(6):
            deck.set_key_image(i, red)
    time.sleep(0.4)
    _shuffle_lock_screen()


def _relock():
    """Re-lock the deck and show the shuffled lock screen."""
    global locked
    locked = True
    print("Inactivity timeout — re-locked.")
    _shuffle_lock_screen()


def _inactivity_watcher():
    """Background thread that re-locks the deck after LOCK_TIMEOUT seconds of inactivity."""
    while True:
        time.sleep(1)
        if not locked and last_activity and time.monotonic() - last_activity >= LOCK_TIMEOUT:
            _relock()


# ---------------------------------------------------------------------------
# Stream Deck setup
# ---------------------------------------------------------------------------
def update_keys():
    """Refresh all 6 keys based on current_page."""
    if deck is None or not deck.is_open():
        return

    offset = current_page * 5  # 0 or 5

    with deck:
        # Key 0 – folder toggle
        deck.set_key_image(0, _make_folder_image(deck, current_page == 1))
        # Keys 1-5 – numbers
        for i in range(1, 6):
            deck.set_key_image(i, _make_number_image(deck, i + offset))


def key_callback(deck_dev, key: int, pressed: bool):
    """Handle physical key presses."""
    global current_page, locked, pin_progress, last_activity

    if not pressed:
        return

    if locked:
        expected = pin_progress + 1
        actual = shuffled_keys[key]
        if actual == expected:
            pin_progress += 1
            print(f"PIN progress: {pin_progress}/6")
            if pin_progress == 6:
                locked = False
                last_activity = time.monotonic()
                print("Unlocked!")
                update_keys()
        else:
            print(f"Wrong key (expected {expected}, got {actual}) — resetting")
            _flash_red()
        return

    last_activity = time.monotonic()

    if key == 0:
        # Toggle page
        current_page = 1 - current_page
        update_keys()
        print(f"Switched to page {current_page} (numbers {1 + current_page * 5}-{5 + current_page * 5})")
    else:
        number = key + current_page * 5
        print(f"Button {key} pressed → number {number}")


def open_deck():
    """Find and initialise the first visual Stream Deck."""
    global deck

    devices = DeviceManager().enumerate()
    if not devices:
        print("No Stream Deck found.")
        return

    for dev in devices:
        if not dev.is_visual():
            continue

        dev.open()
        dev.reset()
        dev.set_brightness(80)

        deck = dev
        print(
            f"Opened {deck.deck_type()} — "
            f"{deck.key_count()} keys, layout {deck.key_layout()}"
        )

        deck.set_key_callback(key_callback)
        _shuffle_lock_screen()
        return

    print("No visual Stream Deck found (only non-visual devices detected).")


def close_deck():
    """Reset and close the deck."""
    global deck
    if deck and deck.is_open():
        with deck:
            deck.reset()
            deck.close()
        deck = None
        print("Stream Deck closed.")


# ---------------------------------------------------------------------------
# FastAPI
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup — open the Stream Deck on a background thread so it doesn't
    # block the event loop if enumeration is slow.
    threading.Thread(target=open_deck, daemon=True).start()
    threading.Thread(target=_inactivity_watcher, daemon=True).start()
    yield
    # Shutdown
    close_deck()


app = FastAPI(title="Elgato Stream Deck Controller", lifespan=lifespan)


@app.get("/")
def root():
    connected = deck is not None and deck.is_open()
    return {
        "status": "ok",
        "deck_connected": connected,
        "locked": locked,
        "current_page": current_page,
        "numbers_shown": list(range(1 + current_page * 5, 6 + current_page * 5)),
    }


@app.post("/toggle")
def toggle_page():
    """Toggle the page via HTTP (same as pressing the folder key)."""
    global current_page
    if deck is None or not deck.is_open():
        return {"error": "No Stream Deck connected"}
    if locked:
        return {"error": "Deck is locked"}
    current_page = 1 - current_page
    update_keys()
    return {
        "current_page": current_page,
        "numbers_shown": list(range(1 + current_page * 5, 6 + current_page * 5)),
    }


@app.get("/status")
def status():
    """Return current deck state."""
    connected = deck is not None and deck.is_open()
    return {
        "deck_connected": connected,
        "deck_type": deck.deck_type() if connected else None,
        "key_count": deck.key_count() if connected else None,
        "locked": locked,
        "current_page": current_page,
        "numbers_shown": list(range(1 + current_page * 5, 6 + current_page * 5)),
    }
