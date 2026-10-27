"""
Radar — Student Opportunity Radar
Main Flask application with all API routes.
"""

from flask import Flask, jsonify, request, send_from_directory
from datetime import datetime, timedelta
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

from services.unified_radar import init_radar_db, get_radar_items, DEFAULT_KEYWORDS
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
    so no data is lost — they are simply no longer used.
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
    print("✅ Database initialized!")


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
    """Feed items. Query params: pillar (jobs/events/news), q, limit, offset."""
    pillar = request.args.get('pillar') or None
    q = (request.args.get('q') or '').strip() or None
    limit = min(int(request.args.get('limit', 30)), 100)
    offset = int(request.args.get('offset', 0))
    items = get_radar_items(pillar=pillar, limit=limit, q=q, offset=offset)

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
               r.deadline_or_date, r.extra_info
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
    return jsonify({'status': 'ok', 'message': 'Tracked! 📅' if deadline else 'Saved! 🔖', 'deadline': deadline})


@app.route('/api/saved/<int:id>', methods=['PUT'])
def update_saved(id):
    """Update deadline and/or status. JSON: {"deadline": "2026-11-15" | null, "status": "applied"}"""
    data = request.get_json() or {}
    conn = get_db()
    if 'deadline' in data:
        conn.execute(
            'UPDATE saved_items SET deadline = ?, reminded_2d = 0, reminded_0d = 0 WHERE id = ?',
            (data['deadline'] or None, id)
        )
    if data.get('status') in ('saved', 'applied'):
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
    """Interest keywords + the private ntfy topic to subscribe to."""
    conn = get_db()
    row = conn.execute("SELECT value FROM settings WHERE key = 'keywords'").fetchone()
    conn.close()
    return jsonify({
        'keywords': row['value'] if row else ', '.join(DEFAULT_KEYWORDS),
        'ntfy_topic': get_topic(),
    })


@app.route('/api/settings', methods=['POST'])
def set_settings():
    """Save interest keywords. JSON: {"keywords": "python, c++, intern"}"""
    data = request.get_json() or {}
    if 'keywords' not in data:
        return jsonify({'status': 'error', 'message': 'keywords is required'}), 400
    conn = get_db()
    conn.execute("REPLACE INTO settings (key, value) VALUES ('keywords', ?)", (data['keywords'],))
    conn.commit()
    conn.close()
    return jsonify({'status': 'ok', 'message': 'Interests saved!'})


@app.route('/api/notify/test', methods=['POST'])
def test_notification():
    ok = send_push("📡 Radar test", "Notifications are working!", tags=["white_check_mark"])
    return jsonify({'status': 'ok' if ok else 'error'})


# ============ SERVE DASHBOARD ============

@app.route('/')
def serve_dashboard():
    """Serve the PWA dashboard (index.html)."""
    return send_from_directory(app.static_folder, 'index.html')


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
            sections.append("⏰ CLOSING THIS WEEK:\n" + "\n".join(f"• {c['title']} ({c['deadline']})" for c in closing))
        if new_jobs:
            sections.append("💼 NEW ROLES:\n" + "\n".join(f"• {j['title']} — {j['organization']}" for j in new_jobs))
        if new_events:
            sections.append("🚀 NEW HACKATHONS:\n" + "\n".join(f"• {e['title']}" for e in new_events))
        if not sections:
            return  # Nothing worth a notification

        send_push(
            title="📡 Radar Morning Digest",
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
            "SELECT s.id, s.deadline, s.reminded_2d, s.reminded_0d, r.title, r.url "
            "FROM saved_items s JOIN radar_items r ON r.id = s.item_id "
            "WHERE s.deadline IS NOT NULL AND s.status != 'applied'"
        ).fetchall()
        for r in rows:
            days = _days_left(r['deadline'])
            if days is None or days < 0:
                continue
            if days == 0 and not r['reminded_0d']:
                send_push(f"🔥 Closes today: {r['title'][:50]}", "Last day to apply. Tap to open.",
                          priority="urgent", tags=["fire"], click_url=r['url'])
                conn.execute('UPDATE saved_items SET reminded_0d = 1, reminded_2d = 1 WHERE id = ?', (r['id'],))
            elif days <= 2 and not r['reminded_2d']:
                send_push(f"⏰ {days} day(s) left: {r['title'][:50]}", f"Deadline {r['deadline']}. Tap to open.",
                          priority="high", tags=["alarm_clock"], click_url=r['url'])
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

    if tz:
        scheduler = BackgroundScheduler(timezone=tz)
    else:
        scheduler = BackgroundScheduler()

    from services.unified_radar import scan_all_radar, scan_high_priority, cleanup_old_items

    # 08:00 / 20:00 -> Full Scan, 14:00 / 02:00 -> High-Priority Scan (Jobs & Hackathons)
    scheduler.add_job(scan_all_radar, 'cron', hour=8, minute=0)
    scheduler.add_job(scan_high_priority, 'cron', hour=14, minute=0)
    scheduler.add_job(scan_all_radar, 'cron', hour=20, minute=0)
    scheduler.add_job(scan_high_priority, 'cron', hour=2, minute=0)
    # 08:30 -> Morning digest
    scheduler.add_job(scheduled_morning_digest, 'cron', hour=8, minute=30)
    # 09:00 / 18:00 -> Tracked deadline reminders
    scheduler.add_job(check_tracked_deadlines, 'cron', hour=9, minute=0)
    scheduler.add_job(check_tracked_deadlines, 'cron', hour=18, minute=0)
    # 03:00 -> Drop expired / stale items nobody saved
    scheduler.add_job(cleanup_old_items, 'cron', hour=3, minute=0)

    scheduler.start()

    print("=" * 50)
    print("📡 Radar Server Starting...")
    print(f"📱 Dashboard:     http://0.0.0.0:5000")
    print(f"📂 Database:      {DB_PATH}")
    print(f"🔑 Access token:  {get_access_token()}")
    print(f"🔔 ntfy topic:    {get_topic()}  (subscribe to this in the ntfy app)")
    print("=" * 50)

    app.run(host='0.0.0.0', port=5000, debug=False)
