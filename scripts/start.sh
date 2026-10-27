#!/bin/bash
# ============================================================
# Radar — Start Server
# Usage: bash scripts/start.sh
# ============================================================

cd ~/pocketbrain
source venv/bin/activate

# Acquire wake lock so the phone doesn't sleep
termux-wake-lock 2>/dev/null

echo "📡 Starting Radar..."

# Kill any existing instance
pkill -f "python server/app.py" 2>/dev/null
sleep 1

# Start in background
nohup python server/app.py >> logs/app.log 2>&1 &
SERVER_PID=$!

echo "✅ Server started! (PID: $SERVER_PID)"
echo "📱 Dashboard: http://localhost:5000"
echo "📋 Logs: tail -f logs/app.log"

# Show IP for other devices
IP=$(ifconfig wlan0 2>/dev/null | grep 'inet ' | awk '{print $2}')
if [ -n "$IP" ]; then
    echo "🌐 Other devices: http://$IP:5000"
fi

# Access token + private ntfy topic (created on first start)
sleep 3
echo "🔑 Access token: $(cat data/access_token.txt 2>/dev/null)"
echo "🔔 ntfy topic:   $(cat data/ntfy_topic.txt 2>/dev/null)"
