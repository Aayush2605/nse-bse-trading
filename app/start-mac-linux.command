#!/bin/sh
# Double-click (Mac) or run (Linux) to start NSE BSE Trader. Close the window to stop it.
cd "$(dirname "$0")" && exec python3 server.py "$@"
