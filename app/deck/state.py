import time

# Deck hardware reference
deck = None

# UI state
current_page = 0   # 0 → numbers 1-5, 1 → numbers 6-10, 2 → admin page
locked = True
last_activity = 0.0

NUM_PAGES = 2       # number pages (page 0 and 1)
ADMIN_PAGE = 2       # page index for admin controls


def touch():
    """Record activity timestamp (resets inactivity timer)."""
    global last_activity
    last_activity = time.monotonic()


def unlock():
    global locked
    locked = False
    touch()


def lock():
    global locked, current_page
    locked = True
    current_page = 0
