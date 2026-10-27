# 📡 Radar

A student opportunity radar: internships, jobs and hackathons in one feed,
with deadline tracking and push reminders. Runs on a Mobistar C2 phone in Termux.

> The full PocketBrain personal OS (expenses, habits, attendance, exams, chat)
> is preserved at the git tag `pocketbrain-v1`.

## Features
- 📡 **Feed** — jobs & internships (Remotive, Jobicy), hackathons (Devpost, Google Developers), tech news
- 🔍 Search and filter by type
- 🔖 **Save** and 📅 **Track** — tracking sets a deadline (Devpost deadlines are detected automatically)
- 🔔 Push reminders via ntfy: 2 days before and on the deadline day, plus a morning digest
- 🎯 Interest keywords (Settings) decide which jobs are picked up on each scan
- 🔑 Access-token login on every API call

## Quick Start (on Termux)

```bash
# 1. One-time setup
bash scripts/setup.sh

# 2. Copy project files to ~/pocketbrain/

# 3. Start the server (prints the access token and ntfy topic)
bash scripts/start.sh

# 4. Open http://localhost:5000 and enter the access token
```

## Secrets
Created on first start, git-ignored:
- `data/access_token.txt` — login token (override with `RADAR_TOKEN`)
- `data/ntfy_topic.txt` — private ntfy topic to subscribe to (override with `NTFY_TOPIC`)

## Tech Stack
- **Backend:** Python Flask + SQLite (WAL) + APScheduler
- **Frontend:** single-file PWA, vanilla JS, no build step
- **Notifications:** ntfy.sh
