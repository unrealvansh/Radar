# 📡 Radar

A student opportunity radar: internships, jobs and hackathons in one feed,
with deadline tracking and push reminders. Runs on a Mobistar C2 phone in Termux.

> The full PocketBrain personal OS (expenses, habits, attendance, exams, chat)
> is preserved at the git tag `pocketbrain-v1`.

## Features
- 📡 **Feed** from 70+ websites (see `server/services/sources.py`):
  hackathons & contests (Unstop, Devpost, Devfolio, MLH, HackerEarth, Codeforces, CodeChef, LeetCode, GDG, dev.events),
  jobs & internships (Unstop, remote boards, 23 company career pages — India roles only), tech news (22 feeds)
- 🧹 Duplicates removed (same link ignoring tracking params, or same title)
- 📅 Only upcoming events and fresh jobs/news (jobs ≤ 21 days, news ≤ 3 days); expired items auto-deleted
- 🎯 Student filter: no senior / sales / overseas roles; title must match your interest keywords
- 🔍 Search and filter by type
- 🔖 **Save** and 📅 **Track** — tracking sets a deadline (Devpost deadlines are detected automatically)
- 🔔 Push reminders via ntfy: 2 days before and on the deadline day, plus a morning digest
- 🎯 Interest keywords (Settings) decide which jobs are picked up on each scan
- 🔑 Access-token login on every API call

## App
Dark-first UI (matching light theme) in pale lavender + polished silver, no gradients.
Desktop gets a sidebar and a slide-in detail panel; phones get a bottom tab bar and a swipeable bottom sheet.
- **Dashboard** — New today / Closing this week / Tracked / Applied, Closing soon, Top picks, Just in, coverage
- **Feed** — sort by Latest / Closing soon / Top picks, filter by type and source, grid or list, infinite scroll
- **Calendar** — month view of tracked deadlines and upcoming events
- **Board** — Saved → Applied → Done (drag and drop on desktop, arrows everywhere)
- **Command palette** — `Ctrl K` or `/` to search everything and run commands

| Keys | Action |
|---|---|
| `Ctrl K`, `/` | Search & commands |
| `G` then `D` `F` `C` `B` `S` | Dashboard, Feed, Calendar, Board, Settings |
| `J` / `K` | Next / previous card |
| `Enter` | Open details |
| `S` / `T` / `O` | Save / Track / Open link |
| `R` | Scan now |
| `?` | All shortcuts |

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
