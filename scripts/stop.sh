#!/bin/bash
# ============================================================
# Radar — Stop Server
# Usage: bash scripts/stop.sh
# ============================================================

echo "🛑 Stopping Radar..."
pkill -f "python server/app.py" 2>/dev/null

if [ $? -eq 0 ]; then
    echo "✅ Server stopped."
else
    echo "ℹ️  Server was not running."
fi
