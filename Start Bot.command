#!/bin/bash
cd "$(dirname "$0")" || exit
echo "Starting Discord Bot..."
source .venv/bin/activate
python3 src/main.py
echo "Bot exited. Closing window in 10 seconds..."
sleep 10
