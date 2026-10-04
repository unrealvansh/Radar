# 🧠 PocketBrain

A self-hosted personal automation server running on a Mobistar C2 phone.

## What is this?

Your own JARVIS — an always-on server that:
- 💸 Tracks your expenses
- 🎯 Tracks your habits & streaks
- 📊 Calculates attendance & bunk predictions
- 🔔 Sends push notifications (coming soon)
- 🌐 Accessible from any device on your network

## Quick Start (on Termux)

```bash
# 1. One-time setup
bash scripts/setup.sh

# 2. Copy project files to ~/pocketbrain/

# 3. Start the server
bash scripts/start.sh

# 4. Open in browser
# http://localhost:5000
```

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python + Flask |
| Database | SQLite (WAL mode) |
| Frontend | Vanilla HTML/CSS/JS (PWA) |
| Scheduler | APScheduler (coming soon) |
| Notifications | ntfy (coming soon) |

## Project Structure

```
pocketbrain/
├── server/          # Python backend
│   ├── app.py       # Main Flask application
│   └── requirements.txt
├── frontend/        # PWA dashboard
│   ├── index.html   # Dashboard UI
│   └── manifest.json
├── data/            # SQLite database
├── storage/         # Personal cloud files
├── logs/            # Application logs
├── config/          # Settings (timetable, menu, etc.)
└── scripts/         # Setup & management scripts
```

## Access from Other Devices

Find your phone's IP:
```bash
ifconfig wlan0 | grep "inet "
```

Then open `http://<phone-IP>:5000` on any device on the same Wi-Fi.

## License

Personal project — built with 🧠
