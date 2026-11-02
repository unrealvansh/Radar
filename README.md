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
Dark-first UI (matching light theme) shared with Explore: near-black base, white type, one blue for actions,
amber for urgent deadlines. Headings in B612 (the typeface designed for aircraft cockpit displays).
Desktop gets a sidebar and a slide-in detail panel; phones get a bottom tab bar and a swipeable bottom sheet.
- **Dashboard**: a radar scope that plots every deadline in the next 30 days (closer to the centre = closes sooner),
  a readout of new / due this week / tracked / applied, then Closing soon, Near you, Top picks and Just in
- **Feed**: sort by Latest / Closing soon / Top picks, filter by type and source, grid or list, infinite scroll
- **Calendar**: month view of tracked deadlines and upcoming events
- **Board**: Saved → Applied → Done (drag and drop on desktop, arrows everywhere)
- **Command palette**: `Ctrl K` or `/` to search everything and run commands
- **Near me**: set your city (or use GPS on the HTTPS link) and a radius; the feed can show opportunities
  near you (nearest first), near you + online, or online/remote only. Cities are detected from each
  listing using a built-in list of ~75 Indian cities (`server/services/locations.py`), no geocoding API.

| Keys | Action |
|---|---|
| `Ctrl K`, `/` | Search & commands |
| `G` then `D` `F` `C` `B` `S` | Dashboard, Feed, Calendar, Board, Settings |
| `J` / `K` | Next / previous card |
| `Enter` | Open details |
| `S` / `T` / `O` | Save / Track / Open link |
| `R` | Scan now |
| `?` | All shortcuts |

## Explore: Simple, Aura and Map views
A second page at `/explore/` (React + Motion + Leaflet, source in `web/`), reached from the
sidebar, the Feed toolbar or the command palette. It shares the login and API with the app.
- **Simple:** community-style cards (banner, round logo, stats, tags, Save / Saved menu) with
  scroll reveals, pointer tilt and infinite scroll.
- **Aura:** 16 cards on the inside of a 3D cylinder (plain CSS 3D, no WebGL). A loader deals the
  cards out while the real covers load, then the camera moves inside the ring. It drifts slowly
  on its own (Pause button); hovering a card brings it forward and blurs the rest. Drag, swipe,
  scroll or use the arrow keys to turn it. Escape, Tab or "Skip intro" ends the entrance;
  reduced-motion systems skip it (add `?motion` to the URL to force it for a demo).
- **Map:** a dark dot-matrix India on a tilted plane (canvas, no map tiles or API keys). Dots near
  opportunities glow blue, each city has a beacon with a count (amber = something closes within
  3 days), and picking a city flies the camera there. Drag to pan, scroll to zoom, Esc to go back.
- Keys `1` `2` `3` switch views. Cards use the images sources already provide (Unstop, Devpost,
  Devfolio); others get a drawn cover.

Build after changing `web/` (the output in `frontend/explore` is committed, so the phone needs no Node):
```bash
cd web && npm install && npm test && npm run build
```

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
