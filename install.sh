#!/usr/bin/env bash
set -e

VENV=".venv"

if [ ! -d "$VENV" ]; then
    python3 -m venv "$VENV"
fi

source "$VENV/bin/activate"

pip install -r requirements.txt

# mfrc522 depends on RPi.GPIO which conflicts with rpi-lgpio on Pi 5.
# Install without deps — its actual deps (spidev) are in requirements.txt.
pip install mfrc522 --no-deps
pip uninstall RPi.GPIO -y 2>/dev/null || true

echo "Done. Run with: python run.py"
