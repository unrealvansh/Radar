# Radar

Internships, jobs, hackathons and tech news from 70+ sites in one feed, filtered to what you
care about, with deadline reminders. Radar is self-hosted and small enough to run on an old
Android phone with Termux.

## Features

- **One feed from 77 sources**: Unstop, Devfolio, Devpost, MLH, HackerEarth, Luma (6 cities), Codeforces,
  CodeChef, LeetCode, GDG, dev.events, remote job boards, 23 company career pages and 22 news feeds
- **Filtered for students**: no senior, sales or overseas roles; jobs must match your interest keywords
- **No duplicates and nothing stale**: the same listing from two sites shows once; past events
  and old posts are cleared every night
- **Near me**: pick your city and a radius to see nearby events first
- **Save, track and apply**: a Saved → Applied → Done board, a deadline calendar, and push
  reminders two days before and on the day (via [ntfy](https://ntfy.sh))
- **Notifications**: every new find and reminder appears under the bell in the app
- **Home**: a 3D ring of opportunities (plain CSS 3D) with a loading intro
- **Map**: India as a dot matrix with state borders and a beacon per city
- Five scans a day (7:30, 11:00, 15:00, 19:00, 22:00 IST), none at night

## Stack

| Part | Tech |
|---|---|
| Server | Python, Flask, SQLite, APScheduler |
| App | React, Motion, Vite (built into `frontend/app`, served by Flask) |
| Notifications | ntfy |

```
server/            Flask app, scanners and scheduler
  services/        sources, location detection, storage, notifications
web/               React app source
frontend/          built app, manifest, terms and privacy pages
scripts/           setup, start and stop for Termux
data/              database and secrets (git-ignored)
```

## Run it on a computer

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r server/requirements.txt
python server/app.py
```

Open http://localhost:5000 and enter the access token printed in the console.

To work on the app with live reload, run `npm install` and `npm run dev` in `web/`
(the dev server proxies `/api` to port 5000). After changing it, rebuild:

```bash
cd web
npm test
npm run build
```

The build output in `frontend/app` is committed, so the server never needs Node.

## Run it on an Android phone

1. Install [Termux](https://termux.dev) and Termux:API, copy this folder to the phone, then run
   `bash scripts/setup.sh` once.
2. Start with `bash scripts/start.sh`. It prints the local address, the access token and your
   ntfy topic. `bash scripts/stop.sh` stops it.
3. Subscribe to the ntfy topic in the ntfy app to get reminders.

Setup also adds a Termux:Boot entry, so Radar starts again after a reboot.

## Configuration

Created on first start in `data/` and never committed:

| File | Purpose | Override |
|---|---|---|
| `radar.db` | SQLite database | |
| `access_token.txt` | login token for the app and API | `RADAR_TOKEN` |
| `ntfy_topic.txt` | private ntfy topic for pushes | `NTFY_TOPIC` |

Interest keywords, your city and search radius are set in the app's Settings.

## Credits

State boundaries on the map come from [Datameet](https://github.com/datameet/maps) (CC BY 4.0).
Listings belong to the sites they come from; Radar links back to each one.
See [terms](frontend/terms.html) and [privacy](frontend/privacy.html).
