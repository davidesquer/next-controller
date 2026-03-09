import threading
import time

from app.auth import cards

# State
register_mode = False
_reader = None
_running = False
_on_unlock = None  # callback when a valid card is scanned
_on_register = None  # callback when a new card is registered


def init(on_unlock=None, on_register=None):
    """Initialise the RFID reader and start the scan loop."""
    global _reader, _on_unlock, _on_register
    _on_unlock = on_unlock
    _on_register = on_register

    try:
        from mfrc522 import SimpleMFRC522
        _reader = SimpleMFRC522()
        print("MFRC522 reader initialised.")
    except (ImportError, RuntimeError) as e:
        print(f"RFID reader not available ({e}). Running without RFID.")
        return

    cards.init()
    t = threading.Thread(target=_scan_loop, daemon=True)
    t.start()


def _scan_loop():
    """Continuously scan for RFID cards."""
    global register_mode, _running
    _running = True
    print("RFID scan loop started.")

    while _running:
        try:
            uid, _ = _reader.read()
        except Exception as e:
            print(f"RFID read error: {e}")
            time.sleep(1)
            continue

        if register_mode:
            if not cards.is_registered(uid):
                cards.register(uid)
                if _on_register:
                    _on_register(uid)
            else:
                print(f"Card {uid} is already registered.")
            register_mode = False
            print("Exited register mode.")
            continue

        if cards.is_registered(uid):
            print(f"Card {uid} authenticated.")
            if _on_unlock:
                _on_unlock(uid)
        else:
            print(f"Card {uid} not recognised.")


def enter_register_mode():
    """Enable register mode — the next scanned card will be registered."""
    global register_mode
    register_mode = True
    print("Register mode ON — scan a new card to register it.")


def exit_register_mode():
    global register_mode
    register_mode = False
    print("Register mode OFF.")


def cleanup():
    """Clean up GPIO on shutdown."""
    global _running
    _running = False
    try:
        import RPi.GPIO as GPIO
        GPIO.cleanup()
        print("GPIO cleaned up.")
    except (ImportError, RuntimeError):
        pass
