import threading
import time

from StreamDeck.DeviceManager import DeviceManager
from StreamDeck.Devices.StreamDeckMini import StreamDeckMini
from StreamDeck.ProductIDs import USBProductIDs, USBVendorIDs

from app.auth import rfid
from app.config import LOCK_TIMEOUT
from app.deck import images, state

# ---------------------------------------------------------------------------
# Patch: register Stream Deck Mini V2 (PID 0x00b3)
# ---------------------------------------------------------------------------
USBProductIDs.USB_PID_STREAMDECK_MINI_V2 = 0x00B3
_original_enumerate = DeviceManager.enumerate


def _patched_enumerate(self):
    devices = _original_enumerate(self)
    extra = self.transport.enumerate(
        vid=USBVendorIDs.USB_VID_ELGATO,
        pid=USBProductIDs.USB_PID_STREAMDECK_MINI_V2,
    )
    devices.extend(StreamDeckMini(d) for d in extra)
    return devices


DeviceManager.enumerate = _patched_enumerate


# ---------------------------------------------------------------------------
# Key rendering
# ---------------------------------------------------------------------------
def update_keys():
    """Refresh all 6 keys based on current state."""
    d = state.deck
    if d is None or not d.is_open():
        return

    if state.locked:
        _show_lock_screen()
        return

    page = state.current_page

    with d:
        if page == state.ADMIN_PAGE:
            _show_admin_page()
        else:
            # Normal number pages
            offset = page * 5
            d.set_key_image(0, images.make_folder(d, page == 1))
            for i in range(1, 6):
                d.set_key_image(i, images.make_number(d, i + offset))


def _show_lock_screen():
    d = state.deck
    with d:
        # Key 0: lock icon, keys 1-4: blank, key 5 (last): "SCAN" prompt
        for i in range(6):
            if i == 0:
                d.set_key_image(i, images.make_lock(d))
            elif i == 5:
                d.set_key_image(i, images.make_scan_prompt(d))
            else:
                d.set_key_image(i, images.make_text(d, "", color="black"))


def _show_admin_page():
    d = state.deck
    # Key 0: back arrow, Key 1: register card, keys 2-5: empty
    d.set_key_image(0, images.make_text(d, "BACK", color="#40a0f0"))
    if rfid.register_mode:
        d.set_key_image(1, images.make_text(d, "REG..", color="black", bg="yellow"))
    else:
        d.set_key_image(1, images.make_text(d, "REG\nCARD", color="#00cc66"))
    for i in range(2, 6):
        d.set_key_image(i, images.make_text(d, "", color="black"))


# ---------------------------------------------------------------------------
# Key callbacks
# ---------------------------------------------------------------------------
def key_callback(deck_dev, key: int, pressed: bool):
    if not pressed:
        return

    if state.locked:
        # Ignore button presses while locked — auth is via RFID only
        return

    state.touch()
    page = state.current_page

    if page == state.ADMIN_PAGE:
        _handle_admin_key(key)
    else:
        _handle_number_key(key, page)


def _handle_number_key(key: int, page: int):
    if key == 0:
        # Cycle: page 0 → 1 → admin → 0
        if page < state.NUM_PAGES - 1:
            state.current_page = page + 1
        else:
            state.current_page = state.ADMIN_PAGE
        update_keys()
        print(f"Switched to page {state.current_page}")
    else:
        number = key + page * 5
        print(f"Button {key} pressed -> number {number}")


def _handle_admin_key(key: int):
    if key == 0:
        # Back to page 0
        state.current_page = 0
        update_keys()
        print("Back to page 0")
    elif key == 1:
        # Toggle register mode
        if rfid.register_mode:
            rfid.exit_register_mode()
        else:
            rfid.enter_register_mode()
        update_keys()


# ---------------------------------------------------------------------------
# RFID callbacks
# ---------------------------------------------------------------------------
def on_rfid_unlock(uid: int):
    """Called by RFID module when a registered card is scanned."""
    print(f"RFID unlock by card {uid}")
    state.unlock()
    update_keys()


def on_rfid_register(uid: int):
    """Called by RFID module after a new card is registered."""
    print(f"New card {uid} registered via RFID scan.")
    update_keys()


def on_rfid_denied(uid: int):
    """Called by RFID module when an unregistered card is scanned."""
    print(f"RFID denied — card {uid} not registered.")
    _show_denied_screen()
    time.sleep(2)
    state.lock()
    update_keys()


def _show_denied_screen():
    d = state.deck
    if d is None or not d.is_open():
        return
    with d:
        d.set_key_image(0, images.make_text(d, "ACCESS", color="white", bg="red"))
        d.set_key_image(1, images.make_text(d, "DENIED", color="white", bg="red"))
        for i in range(2, 6):
            d.set_key_image(i, images.make_text(d, "", color="white", bg="red"))


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------
def _inactivity_watcher():
    while True:
        time.sleep(1)
        if (
            not state.locked
            and state.last_activity
            and time.monotonic() - state.last_activity >= LOCK_TIMEOUT
        ):
            print("Inactivity timeout — re-locked.")
            state.lock()
            update_keys()


def open_deck():
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

        state.deck = dev
        print(
            f"Opened {dev.deck_type()} — "
            f"{dev.key_count()} keys, layout {dev.key_layout()}"
        )

        dev.set_key_callback(key_callback)
        update_keys()
        return

    print("No visual Stream Deck found.")


def close_deck():
    d = state.deck
    if d and d.is_open():
        with d:
            d.reset()
            d.close()
        state.deck = None
        print("Stream Deck closed.")


def start():
    """Start deck + inactivity watcher in background threads."""
    threading.Thread(target=open_deck, daemon=True).start()
    threading.Thread(target=_inactivity_watcher, daemon=True).start()
