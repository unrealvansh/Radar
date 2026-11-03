# Radar

A student opportunity radar: internships, jobs and hackathons in one feed,
with deadline tracking and push reminders. Runs on a Mobistar C2 phone in Termux.

> The full PocketBrain personal OS (expenses, habits, attendance, exams, chat)
> is preserved at the git tag `pocketbrain-v1`.

## Features
- **Feed** from 70+ websites (see `server/services/sources.py`):
  hackathons & contests (Unstop, Devpost, Devfolio, MLH, HackerEarth, Codeforces, CodeChef, LeetCode, GDG, dev.events),
  jobs & internships (Unstop, remote boards, 23 company career pages: India roles only), tech news (22 feeds)
- Duplicates removed (same link ignoring tracking params, or same title)
- Only upcoming events and fresh jobs/news (jobs ≤ 21 days, news ≤ 3 days); expired items auto-deleted
- Student filter: no senior / sales / overseas roles; title must match your interest keywords
- Search and filter by type
- **Save** and **Track**: tracking sets a deadline (Devpost deadlines are detected automatically)
- Push reminders via ntfy: 2 days before and on the deadline day, plus a morning digest
- Interest keywords (Settings) decide which jobs are picked up on each scan
- Access-token login on every API call

## App
One React app (source in `web/`, built into `frontend/app`, served at `/`). Dark UI: near-black base,
white type, one blue for actions, amber for urgent deadlines; headings in B612. Sidebar on desktop,
bottom tab bar on phones.
- **Home**: the hero is a 3D ring of 16 opportunity cards (plain CSS 3D, no WebGL). On first visit a loader
  deals the cards out while the real covers load, then the camera moves inside the ring. It drifts slowly
  (Pause button); hovering a card pauses it, turns the card to face you and pulls it close. Below the ring:
  greeting, stats, Closing soon, Near you, Picks for you, Just in.
- **Feed**: cards with banner, logo, stats, tags and a Save / Saved menu; filter by type, For you,
  Closing soon, Near me, Online; search; infinite scroll.
- **Map**: a dark dot-matrix India on a tilted plane with glowing state borders
  (boundaries from [Datameet](https://github.com/datameet/maps), CC BY 4.0). Each city has a beacon labelled with its soonest
  event (amber = something closes within 3 days); pick one and the camera flies there.
- **Calendar**: month view of tracked deadlines and upcoming events.
- **Board**: Saved, Applied, Done (drag and drop on desktop, arrows everywhere).
- **Settings**: name, location (GPS on HTTPS, or pick a city) and radius, interests, ntfy topic, lock.
- Reduced-motion systems skip the intro (add `?motion` to the URL to force it for a demo).

Build after changing `web/` (the output is committed, so the phone needs no Node):
```bash
cd web && npm install && npm test && npm run build
```

| Keys | Action |
|---|---|
| `Ctrl K`, `/` | Search & commands |
| `G` then `H` `F` `M` `C` `B` `S` | Home, Feed, Map, Calendar, Board, Settings |
| `Esc` | Close details / leave a city on the map |

## Legal
`/terms.html` and `/privacy.html` (linked from the login screen, sidebar and Settings).

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
- `data/access_token.txt`: login token (override with `RADAR_TOKEN`)
- `data/ntfy_topic.txt`: private ntfy topic to subscribe to (override with `NTFY_TOPIC`)

## Tech Stack
- **Backend:** Python Flask + SQLite (WAL) + APScheduler
- **Frontend:** single-file PWA, vanilla JS, no build step
- **Notifications:** ntfy.sh
