# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Next Controller is a FastAPI application that drives an Elgato Stream Deck Mini as a physical number-pad interface, secured by RFID card authentication (MFRC522 reader on Raspberry Pi GPIO). The deck shows numbers 1-10 across two pages; a third admin page allows registering new RFID cards via the deck itself.

## Running the App

```bash
# Activate the virtualenv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the server (port 8000)
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

The RFID reader requires running on a Raspberry Pi with SPI enabled. On non-Pi hardware, the app starts without RFID support (graceful fallback).

## Architecture

### `app/` Module Structure

- **`app/main.py`** — FastAPI app creation, lifespan (startup/shutdown), mounts routers.
- **`app/config.py`** — Constants (`LOCK_TIMEOUT`), `cards.json` path, load/save helpers.
- **`app/deck/state.py`** — Mutable global state: deck reference, lock status, current page, activity timer.
- **`app/deck/manager.py`** — Core logic: Stream Deck enumeration (with Mini V2 PID patch), key callbacks, page navigation, inactivity watcher, RFID callback handlers. Owns the background threads.
- **`app/deck/images.py`** — PIL-based image rendering for each key type (numbers, folder, lock, scan prompt, generic text).
- **`app/deck/router.py`** — `/deck/status` and `/deck/toggle` HTTP endpoints.
- **`app/auth/rfid.py`** — MFRC522 scan loop in a background thread, register mode toggle, GPIO cleanup.
- **`app/auth/cards.py`** — In-memory card registry backed by `cards.json`. CRUD operations on card UIDs.
- **`app/auth/router.py`** — `/auth/cards` CRUD endpoints and `/auth/register-mode` toggle.

### Key Design Details

- **Stream Deck Mini V2 patch**: The `streamdeck` library doesn't recognize PID `0x00b3`. `app/deck/manager.py` monkey-patches `DeviceManager.enumerate` to include it as a `StreamDeckMini`.
- **Threading model**: The deck runs callbacks on its own thread. The RFID scan loop and inactivity watcher each run on separate daemon threads. FastAPI's async event loop is kept free.
- **Lock/unlock flow**: The deck starts locked showing a lock icon + "SCAN" prompt. Scanning a registered RFID card unlocks it. After `LOCK_TIMEOUT` (10s) of inactivity, it re-locks automatically.
- **Page navigation**: Key 0 is always the navigation key. On number pages it cycles through page 0 → 1 → admin. On the admin page it goes back to page 0.
- **Card persistence**: `cards.json` at the project root stores registered card UIDs. Loaded into memory on startup, written back on every change.

## API Endpoints

- `GET /` — Basic status
- `GET /deck/status` — Deck connection and page state
- `POST /deck/toggle` — Toggle number page (requires unlocked)
- `GET /auth/cards` — List registered cards
- `POST /auth/cards` — Register card by UID (JSON body: `{uid, name}`)
- `DELETE /auth/cards/{uid}` — Remove a card
- `POST /auth/register-mode` — Enter register mode (next RFID scan registers)
- `POST /auth/register-mode/cancel` — Cancel register mode
- `GET /auth/status` — Card count and register mode flag
