#!/bin/bash
cd "$(dirname "$0")/.." || exit 1
source venv/bin/activate
termux-wake-lock 2>/dev/null

pkill -f "python server/app.py" 2>/dev/null
sleep 1
mkdir -p logs data
nohup python server/app.py >> logs/app.log 2>&1 &

echo "Radar is running at http://localhost:5000"
IP=$(ifconfig wlan0 2>/dev/null | awk '/inet /{print $2}')
[ -n "$IP" ] && echo "On your network:  http://$IP:5000"
echo "Logs:             tail -f logs/app.log"

sleep 3
echo "Access token:     $(cat data/access_token.txt 2>/dev/null)"
echo "ntfy topic:       $(cat data/ntfy_topic.txt 2>/dev/null)"
