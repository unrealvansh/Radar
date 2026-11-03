"""
Radar: Student Opportunity Radar
Main Flask application with all API routes.
"""

from flask import Flask, jsonify, redirect, request, send_from_directory
from datetime import datetime, timedelta
import gzip
import secrets
import sqlite3
import os
import sys

# Fix Windows console encoding for emoji/unicode
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# Ensure server directory is always in sys.path
SERVER_DIR = os.path.dirname(os.path.abspath(__file__))
if SERVER_DIR not in sys.path:
    sys.path.insert(0, SERVER_DIR)

from services.unified_radar import (init_radar_db, get_radar_items, get_counts, get_city_counts,
                                    is_scanning, DEFAULT_KEYWORDS, add_notification,
                                    get_notifications, mark_notifications_read)
from services import locations
from services.sources import SOURCES
from services.notifier import send_push, get_topic

# ============ APP SETUP ============

# __file__ = this file's path
# We go up one level (..) to reach the project root
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

app = Flask(__name__,
    static_folder=os.path.join(BASE_DIR, 'frontend'),  # Serve dashboard files
    static_url_path=''                                   # Serve at root URL
)

# Same DB file as before, so existing radar items carry over
DB_PATH = os.path.join(BASE_DIR, 'data', 'pocketbrain.db')
TOKEN_FILE = os.path.join(BASE_DIR, 'data', 'access_token.txt')


# ============ DATABASE HELPERS ============

def get_db():
    """Connect to SQLite database.

    - row_factory = sqlite3.Row makes rows behave like dictionaries
    - WAL mode = better performance for concurrent reads/writes
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    """Create tables if they don't exist.

    Old PocketBrain tables (expenses, habits, ...) are left untouched,
    so no data is lost: they are simply no longer used.
    """
    init_radar_db()
    conn = get_db()
    conn.executescript('''
        -- Settings (key-value store: keywords, preferences)
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );

        -- Saved / tracked radar items
        CREATE TABLE IF NOT EXISTS saved_items (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            item_id     INTEGER NOT NULL UNIQUE REFERENCES radar_items(id),
            deadline    TEXT,                  -- ISO date; set = tracked
            status      TEXT DEFAULT 'saved',  -- saved, applied
            reminded_2d INTEGER DEFAULT 0,
            reminded_0d INTEGER DEFAULT 0,
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    ''')

    # One-time carry-over: old bookmarks that point at radar items
    has_bookmarks = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='bookmarks'"
    ).fetchone()
    if has_bookmarks:
        conn.execute('''
            INSERT OR IGNORE INTO saved_items (item_id)
            SELECT r.id FROM bookmarks b JOIN radar_items r ON r.url = b.url
        ''')

    conn.commit()
    conn.close()
    print("Database initialized!")


# ============ AUTH ============

def get_access_token():
    """Access token for the API.

    Generated once into data/access_token.txt (git-ignored).
    RADAR_TOKEN env var overrides it.
    """
    env_token = os.environ.get('RADAR_TOKEN')
    if env_token:
        return env_token
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE) as f:
            token = f.read().strip()
        if token:
            return token
    token = secrets.token_urlsafe(16)
    os.makedirs(os.path.dirname(TOKEN_FILE), exist_ok=True)
    with open(TOKEN_FILE, 'w') as f:
        f.write(token)
    return token


@app.before_request
def require_token():
    """Every /api/* route except /api/health needs the X-Access-Token header."""
    if not request.path.startswith('/api/') or request.path == '/api/health':
        return None
    sent = request.headers.get('X-Access-Token', '')
    if not secrets.compare_digest(sent, get_access_token()):
        return jsonify({'status': 'error', 'message': 'unauthorized'}), 401
    return None


# ============ COMPRESSION & CACHING ============
# The server is a phone on Wi-Fi: gzip text (JSON lists shrink ~6x) and let the browser keep
# the built app files, whose names change on every build, so a reload downloads nothing again.

_GZ_TYPES = ('application/json', 'application/javascript', 'text/javascript', 'text/css', 'text/html', 'image/svg+xml')
_gz_cache = {}  # static file path -> (mtime, gzipped bytes)


@app.after_request
def compress_and_cache(resp):
    if request.path.startswith('/app/assets/'):
        resp.headers['Cache-Control'] = 'public, max-age=31536000, immutable'
    elif request.path in ('/', '/app/index.html'):
        resp.headers['Cache-Control'] = 'no-cache'  # always check for a new build
    if ('gzip' not in request.headers.get('Accept-Encoding', '') or resp.status_code != 200
            or 'Content-Encoding' in resp.headers or not resp.mimetype or not resp.mimetype.startswith(_GZ_TYPES)):
        return resp
    resp.direct_passthrough = False  # static files are streamed; read them so they can be compressed
    data = resp.get_data()
    if len(data) < 1024:
        return resp
    key = request.path if request.path.startswith('/app/assets/') else None
    if key and key in _gz_cache:
        body = _gz_cache[key]
    else:
        body = gzip.compress(data, compresslevel=6)
        if key:
            _gz_cache[key] = body  # build files never change under the same name
    resp.set_data(body)
    resp.headers['Content-Encoding'] = 'gzip'
    resp.headers['Vary'] = 'Accept-Encoding'
    resp.headers['Content-Length'] = str(len(body))
    return resp


# ============ API: HEALTH CHECK ============

@app.route('/api/health')
def health():
    """Check if the server is alive.

    Try it: curl http://localhost:5000/api/health
    """
    return jsonify({
        'status': 'alive',
        'server': 'Radar',
        'time': datetime.now().isoformat(),
    })


@app.route('/api/auth/check')
def auth_check():
    """Lets the frontend verify a token (the before_request hook does the work)."""
    return jsonify({'status': 'ok'})


# ============ API: RADAR FEED ============

@app.route('/api/radar', methods=['GET'])
def get_radar():
    """Feed items. Query params: pillar (opps/jobs/events/news), q, source,
    sort (latest/closing/picks), limit, offset,
    near=lat,lon + radius (km) + loc (near/near_online/online) for location filtering."""
    pillar = request.args.get('pillar') or None
    q = (request.args.get('q') or '').strip() or None
    limit = min(int(request.args.get('limit', 30)), 600)  # the ring and the map load everything open
    offset = int(request.args.get('offset', 0))
    try:
        near = tuple(float(v) for v in request.args['near'].split(','))[:2] if request.args.get('near') else None
    except ValueError:
        near = None
    items = get_radar_items(pillar=pillar, limit=limit, q=q, offset=offset,
                            sort=request.args.get('sort', 'latest'),
                            source=request.args.get('source') or None,
                            near=near, radius=float(request.args.get('radius', 50)),
                            loc=request.args.get('loc') or None)

    conn = get_db()
    saved = {r['item_id']: r['id'] for r in conn.execute('SELECT id, item_id FROM saved_items')}
    conn.close()
    for it in items:
        it['saved_id'] = saved.get(it['id'])
    return jsonify({'items': items})


@app.route('/api/radar/scan', methods=['POST'])
def trigger_radar_scan():
    """Trigger background scan across Jobs, Events, and Tech News."""
    from services.unified_radar import scan_all_radar
    import threading
    threading.Thread(target=scan_all_radar, daemon=True).start()
    return jsonify({'status': 'ok', 'message': 'Full radar scan initiated!'})


@app.route('/api/notifications', methods=['GET'])
def list_notifications():
    """The bell: everything scans found and every deadline reminder, newest first."""
    return jsonify(get_notifications(min(200, int(request.args.get('limit', 60)))))


@app.route('/api/notifications/read', methods=['POST'])
def read_notifications():
    """JSON {"ids": [1, 2]} marks those; no ids marks everything read."""
    ids = [int(i) for i in (request.get_json(silent=True) or {}).get('ids') or []]
    mark_notifications_read(ids or None)
    return jsonify({'status': 'ok'})


@app.route('/api/sources', methods=['GET'])
def get_sources():
    """Sources with visible item counts (feed source filter)."""
    _, sources, _ = get_counts()
    return jsonify(sources)


# ============ API: DASHBOARD STATS ============

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Numbers for the dashboard tiles and the scan status."""
    pillars, sources, new_today = get_counts()
    conn = get_db()
    saved = conn.execute('''
        SELECT
            SUM(status = 'saved') AS saved,
            SUM(status = 'applied') AS applied,
            SUM(status = 'done') AS done,
            SUM(deadline IS NOT NULL AND status != 'done') AS tracked,
            SUM(deadline BETWEEN date('now', 'localtime') AND date('now', 'localtime', '+7 days')
                AND status = 'saved') AS closing_week
        FROM saved_items
    ''').fetchone()
    last = conn.execute("SELECT value FROM settings WHERE key = 'last_scan_at'").fetchone()
    conn.close()
    return jsonify({
        'new_today': new_today,
        'pillars': pillars,
        'saved': saved['saved'] or 0,
        'applied': saved['applied'] or 0,
        'done': saved['done'] or 0,
        'tracked': saved['tracked'] or 0,
        'closing_week': saved['closing_week'] or 0,
        'sources_total': len(SOURCES),
        'sources_active': len({s['source'] for s in sources}),
        'last_scan_at': last['value'] if last else None,
        'scanning': is_scanning(),
    })


# ============ API: CALENDAR ============

@app.route('/api/calendar', methods=['GET'])
def get_calendar():
    """Tracked deadlines + upcoming events in a month. Query: month=YYYY-MM"""
    month = request.args.get('month') or datetime.now().strftime('%Y-%m')
    conn = get_db()
    tracked = conn.execute('''
        SELECT r.*, s.id AS saved_id, s.status, s.deadline AS date
        FROM saved_items s JOIN radar_items r ON r.id = s.item_id
        WHERE s.deadline IS NOT NULL AND strftime('%Y-%m', s.deadline) = ?
    ''', (month,)).fetchall()
    tracked_ids = {r['item_id'] for r in conn.execute('SELECT item_id FROM saved_items')}
    events = conn.execute('''
        SELECT *, COALESCE(starts_at, deadline) AS date FROM radar_items
        WHERE pillar = 'events' AND strftime('%Y-%m', COALESCE(starts_at, deadline)) = ?
        AND COALESCE(starts_at, deadline) >= date('now', 'localtime')
    ''', (month,)).fetchall()
    conn.close()
    entries = [dict(r, kind='tracked') for r in tracked]
    entries += [dict(r, kind='event', saved_id=None) for r in events if r['id'] not in tracked_ids]
    entries.sort(key=lambda e: e['date'])
    return jsonify({'month': month, 'entries': entries})


# ============ API: SAVED & TRACKED ============

def _days_left(deadline):
    try:
        due = datetime.strptime(deadline, '%Y-%m-%d').date()
        return (due - datetime.now().date()).days
    except (TypeError, ValueError):
        return None


@app.route('/api/saved', methods=['GET'])
def get_saved():
    """Saved items, tracked ones (with deadline) first, soonest deadline first."""
    conn = get_db()
    rows = conn.execute('''
        SELECT s.id, s.item_id, s.deadline, s.status, s.created_at AS saved_at,
               r.pillar, r.source, r.title, r.organization, r.url,
               r.deadline_or_date, r.extra_info, r.starts_at, r.posted_at,
               r.image, r.logo, r.city, r.mode, r.deadline AS item_deadline
        FROM saved_items s JOIN radar_items r ON r.id = s.item_id
        ORDER BY s.deadline IS NULL, s.deadline ASC, s.id DESC
    ''').fetchall()
    conn.close()

    result = []
    for r in rows:
        d = dict(r)
        d['days_left'] = _days_left(d['deadline'])
        result.append(d)
    return jsonify(result)


@app.route('/api/saved', methods=['POST'])
def save_item():
    """Save or track a radar item.

    Send JSON: {"item_id": 12, "track": true, "deadline": "2026-11-15"}
    Tracking without a deadline uses the item's known deadline, else +14 days.
    """
    data = request.get_json() or {}
    if 'item_id' not in data:
        return jsonify({'status': 'error', 'message': 'item_id is required'}), 400

    conn = get_db()
    item = conn.execute('SELECT * FROM radar_items WHERE id = ?', (data['item_id'],)).fetchone()
    if not item:
        conn.close()
        return jsonify({'status': 'error', 'message': 'item not found'}), 404

    deadline = data.get('deadline')
    if data.get('track') and not deadline:
        deadline = item['deadline'] or (datetime.now().date() + timedelta(days=14)).strftime('%Y-%m-%d')

    conn.execute('INSERT OR IGNORE INTO saved_items (item_id) VALUES (?)', (item['id'],))
    if deadline:
        conn.execute(
            'UPDATE saved_items SET deadline = ?, reminded_2d = 0, reminded_0d = 0 WHERE item_id = ?',
            (deadline, item['id'])
        )
    conn.commit()
    conn.close()
    return jsonify({'status': 'ok', 'message': 'Tracked' if deadline else 'Saved', 'deadline': deadline})


@app.route('/api/saved/<int:id>', methods=['PUT'])
def update_saved(id):
    """Update deadline and/or status. JSON: {"deadline": "2026-11-15" | null, "status": "applied"}
    status: saved -> applied -> done (Board columns)."""
    data = request.get_json() or {}
    conn = get_db()
    if 'deadline' in data:
        conn.execute(
            'UPDATE saved_items SET deadline = ?, reminded_2d = 0, reminded_0d = 0 WHERE id = ?',
            (data['deadline'] or None, id)
        )
    if data.get('status') in ('saved', 'applied', 'done'):
        conn.execute('UPDATE saved_items SET status = ? WHERE id = ?', (data['status'], id))
    conn.commit()
    conn.close()
    return jsonify({'status': 'ok', 'message': 'Updated!'})


@app.route('/api/saved/<int:id>', methods=['DELETE'])
def delete_saved(id):
    """Remove a saved item."""
    conn = get_db()
    conn.execute('DELETE FROM saved_items WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    return jsonify({'status': 'ok', 'message': 'Removed!'})


# ============ API: SETTINGS ============

@app.route('/api/settings', methods=['GET'])
def get_settings():
    """Interest keywords, display name, home location + the private ntfy topic."""
    conn = get_db()
    values = {r['key']: r['value'] for r in conn.execute(
        "SELECT key, value FROM settings WHERE key IN ({})".format(','.join('?' * len(SETTING_KEYS))),
        SETTING_KEYS)}
    conn.close()
    home = None
    if values.get('home_lat') and values.get('home_lon'):
        home = {'city': values.get('home_city', ''), 'lat': float(values['home_lat']),
                'lon': float(values['home_lon']), 'radius': float(values.get('radius_km') or 50)}
    return jsonify({
        'keywords': values.get('keywords', ', '.join(DEFAULT_KEYWORDS)),
        'display_name': values.get('display_name', ''),
        'home': home,
        'ntfy_topic': get_topic(),
    })


# Keys the settings API may store
SETTING_KEYS = ('keywords', 'display_name', 'home_city', 'home_lat', 'home_lon', 'radius_km')


@app.route('/api/settings', methods=['POST'])
def set_settings():
    """Save settings. JSON: any of keywords, display_name, home_city, home_lat, home_lon, radius_km.
    A null value removes the key (e.g. clearing the home location)."""
    data = request.get_json() or {}
    fields = {k: str(data[k]).strip() for k in SETTING_KEYS if k in data and data[k] is not None}
    cleared = [k for k in SETTING_KEYS if k in data and data[k] is None]
    if not fields and not cleared:
        return jsonify({'status': 'error', 'message': 'nothing to save'}), 400
    conn = get_db()
    for key in cleared:
        conn.execute("DELETE FROM settings WHERE key = ?", (key,))
    for key, value in fields.items():
        conn.execute("REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
    conn.commit()
    conn.close()
    return jsonify({'status': 'ok', 'message': 'Settings saved!'})


@app.route('/api/cities', methods=['GET'])
def get_cities():
    """Known cities with how many open opportunities each has (location picker).
    With ?lat=..&lon=.. also returns the nearest known city to that position."""
    counts = get_city_counts()
    cities = [{'name': name, 'region': region or name, 'lat': lat, 'lon': lon, 'count': counts.get(name, 0)}
              for name, (lat, lon, region, _) in locations.CITIES.items()]
    cities.sort(key=lambda c: (-c['count'], c['name']))
    result = {'cities': cities}
    if request.args.get('lat') and request.args.get('lon'):
        name, km = locations.nearest_city(float(request.args['lat']), float(request.args['lon']))
        result['nearest'] = {'name': name, 'km': round(km)}
    return jsonify(result)


@app.route('/api/notify/test', methods=['POST'])
def test_notification():
    ok = send_push("Radar test", "Notifications are working!", tags=["white_check_mark"])
    return jsonify({'status': 'ok' if ok else 'error'})


# ============ SERVE DASHBOARD ============

@app.route('/')
def serve_dashboard():
    """Serve the app (built from web/ into frontend/app)."""
    return send_from_directory(os.path.join(app.static_folder, 'app'), 'index.html')


@app.route('/explore')
@app.route('/explore/')
def old_explore():
    """Explore used to be a separate page; it is part of the app now."""
    return redirect('/')


# ============ BACKGROUND SCHEDULER & NOTIFICATIONS ============

from apscheduler.schedulers.background import BackgroundScheduler

def scheduled_morning_digest():
    """Every morning: what's new in the last 24h + tracked deadlines closing soon."""
    try:
        conn = get_db()
        new_jobs = conn.execute(
            "SELECT title, organization FROM radar_items WHERE pillar = 'jobs' "
            "AND created_at >= datetime('now', '-1 day') ORDER BY id DESC LIMIT 3"
        ).fetchall()
        new_events = conn.execute(
            "SELECT title, organization FROM radar_items WHERE pillar = 'events' "
            "AND created_at >= datetime('now', '-1 day') ORDER BY id DESC LIMIT 3"
        ).fetchall()
        closing = conn.execute(
            "SELECT r.title, s.deadline FROM saved_items s JOIN radar_items r ON r.id = s.item_id "
            "WHERE s.deadline IS NOT NULL AND s.status != 'applied' "
            "AND s.deadline BETWEEN date('now') AND date('now', '+7 days') ORDER BY s.deadline"
        ).fetchall()
        conn.close()

        sections = []
        if closing:
            sections.append("CLOSING THIS WEEK:\n" + "\n".join(f"- {c['title']} ({c['deadline']})" for c in closing))
        if new_jobs:
            sections.append("NEW ROLES:\n" + "\n".join(f"- {j['title']}, {j['organization']}" for j in new_jobs))
        if new_events:
            sections.append("NEW HACKATHONS:\n" + "\n".join(f"- {e['title']}" for e in new_events))
        if not sections:
            return  # Nothing worth a notification

        send_push(
            title="Radar Morning Digest",
            message="\n\n".join(sections),
            priority="high",
            tags=["satellite"]
        )
    except Exception as e:
        print(f"Error running morning digest: {e}")


def check_tracked_deadlines():
    """Remind 2 days before and on the day of each tracked deadline."""
    try:
        conn = get_db()
        rows = conn.execute(
            "SELECT s.id, s.item_id, s.deadline, s.reminded_2d, s.reminded_0d, r.title, r.url "
            "FROM saved_items s JOIN radar_items r ON r.id = s.item_id "
            "WHERE s.deadline IS NOT NULL AND s.status != 'applied'"
        ).fetchall()
        for r in rows:
            days = _days_left(r['deadline'])
            if days is None or days < 0:
                continue
            if days == 0 and not r['reminded_0d']:
                send_push(f"Closes today: {r['title'][:50]}", "Last day to apply. Tap to open.",
                          priority="urgent", tags=["fire"], click_url=r['url'])
                add_notification(conn, r['item_id'], 'reminder', r['title'], 'Closes today. Last day to apply.')
                conn.execute('UPDATE saved_items SET reminded_0d = 1, reminded_2d = 1 WHERE id = ?', (r['id'],))
            elif days <= 2 and not r['reminded_2d']:
                send_push(f"{days} day(s) left: {r['title'][:50]}", f"Deadline {r['deadline']}. Tap to open.",
                          priority="high", tags=["alarm_clock"], click_url=r['url'])
                add_notification(conn, r['item_id'], 'reminder', r['title'], f"{days} day(s) left, deadline {r['deadline']}.")
                conn.execute('UPDATE saved_items SET reminded_2d = 1 WHERE id = ?', (r['id'],))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error checking deadlines: {e}")


# ============ START SERVER ============

if __name__ == '__main__':
    # Create data directory if it doesn't exist
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

    init_db()

    # Start APScheduler with timezone fallback for Termux/Android
    try:
        import zoneinfo
        tz = zoneinfo.ZoneInfo("Asia/Kolkata")
    except Exception:
        tz = None

    # If the phone dozes past a job's time, still run it (up to 15 min late) instead of skipping it
    job_defaults = {'misfire_grace_time': 900, 'coalesce': True}
    if tz:
        scheduler = BackgroundScheduler(timezone=tz, job_defaults=job_defaults)
    else:
        scheduler = BackgroundScheduler(job_defaults=job_defaults)

    from services.unified_radar import scan_all_radar, scan_high_priority, scan_jobs_only, cleanup_old_items

    # 5 scans a day, none at night. Jobs change fastest, so they're in every scan:
    # 07:30 full -> 11:00 jobs -> 15:00 jobs + events -> 19:00 jobs -> 22:00 full
    scheduler.add_job(scan_all_radar, 'cron', hour=7, minute=30)
    scheduler.add_job(scan_jobs_only, 'cron', hour=11, minute=0)
    scheduler.add_job(scan_high_priority, 'cron', hour=15, minute=0)
    scheduler.add_job(scan_jobs_only, 'cron', hour=19, minute=0)
    scheduler.add_job(scan_all_radar, 'cron', hour=22, minute=0)
    # 08:00 -> Morning digest, right after the 07:30 full scan
    scheduler.add_job(scheduled_morning_digest, 'cron', hour=8, minute=0)
    # 09:00 / 18:00 -> Tracked deadline reminders
    scheduler.add_job(check_tracked_deadlines, 'cron', hour=9, minute=0)
    scheduler.add_job(check_tracked_deadlines, 'cron', hour=18, minute=0)
    # 03:00 -> Drop expired / stale items nobody saved
    scheduler.add_job(cleanup_old_items, 'cron', hour=3, minute=0)

    scheduler.start()

    print("=" * 50)
    print("Radar Server Starting...")
    print(f"Dashboard:     http://0.0.0.0:5000")
    print(f"Database:      {DB_PATH}")
    print(f"Access token:  {get_access_token()}")
    print(f"ntfy topic:    {get_topic()}  (subscribe to this in the ntfy app)")
    print("=" * 50)

    app.run(host='0.0.0.0', port=5000, debug=False)
