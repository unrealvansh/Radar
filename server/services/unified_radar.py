"""
Radar scan engine.

- Reads every website in services/sources.py, one at a time (low RAM).
- Keeps only student-relevant jobs (interest keywords / early-career, no senior roles).
- Keeps only upcoming events and fresh jobs/news.
- Removes duplicates: same link (ignoring tracking params) or same title.
"""

import os
import re
import sqlite3
import threading
from datetime import datetime, timedelta
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

from services.sources import SOURCES, IST, tidy
from services import locations

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.path.join(BASE_DIR, 'data', 'pocketbrain.db')

# Default interest keywords (overridable from the Settings screen)
DEFAULT_KEYWORDS = [
    'intern', 'internship', 'trainee', 'c++', 'python', 'fintech', 'quant',
    'trading', 'backend', 'full stack', 'fullstack', 'react', 'node',
    'cloud', 'devops', 'cybersecurity', 'security', 'software',
    'developer', 'engineer', 'engineering', 'sde', 'data', 'machine learning', 'ml', 'ai'
]

# Always relevant for students, whatever the interests are
EARLY_CAREER = ['intern', 'internship', 'internships', 'trainee', 'graduate', 'new grad', 'fresher',
                'freshers', 'campus', 'junior', 'entry level', 'entry-level', 'apprentice', 'student']

# Never relevant for students: senior / mid-level grades, non-tech roles, roles tied to other countries
SENIOR = ['senior', 'sr', 'lead', 'principal', 'staff', 'manager', 'director', 'head', 'vp',
          'architect', 'chief', 'president', 'expert', 'intermediate', 'ii', 'iii', 'iv',
          'sde2', 'sde3', 'sde-2', 'sde-3', 'sde 2', 'sde 3']
NON_TECH = ['sales', 'account', 'accounts', 'counsel', 'legal', 'marketing', 'recruiter',
            'recruiting', 'finance', 'audit', 'customer success', 'bilingual']
FOREIGN = ['emea', 'latam', 'usa', 'united states', 'uk', 'europe', 'spain', 'germany', 'france',
           'canada', 'brazil', 'mexico', 'japan', 'australia', 'san francisco', 'new york',
           'london', 'berlin', 'amsterdam', 'singapore', 'dubai']
EXCLUDE = SENIOR + NON_TECH + FOREIGN

# Freshness windows (days)
JOB_MAX_AGE = 21
NEWS_MAX_AGE = 3
EVENT_UNDATED_MAX_AGE = 14

# Max new items kept per website per scan, so one site can't flood the feed
PER_SOURCE_CAP = {'events': 12, 'jobs': 12, 'news': 3}

TRACKING_PARAMS = re.compile(r'^(utm_.*|ref|ref_src|source|src|fbclid|gclid|mc_cid|mc_eid|trk|lever-source|gh_src)$', re.I)

_scan_lock = threading.Lock()


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def get_keywords():
    """Interest keywords saved in settings ('keywords', comma separated)."""
    try:
        conn = get_db()
        row = conn.execute("SELECT value FROM settings WHERE key = 'keywords'").fetchone()
        conn.close()
        if row and row['value'].strip():
            return [k.strip().lower() for k in row['value'].split(',') if k.strip()]
    except sqlite3.Error:
        pass
    return DEFAULT_KEYWORDS


# =====================================================================
# DUPLICATE KEYS
# =====================================================================

def url_key(url):
    """Same page = same key: lower-case host, no www, no tracking params, no trailing slash."""
    try:
        parts = urlsplit(url.strip())
        host = parts.netloc.lower().removeprefix('www.')
        query = urlencode([(k, v) for k, v in parse_qsl(parts.query) if not TRACKING_PARAMS.match(k)])
        return urlunsplit(('https', host, parts.path.rstrip('/'), query, ''))
    except Exception:
        return url


def title_key(pillar, title, organization):
    """Jobs are unique per title + company; events and news per title."""
    norm = lambda s: re.sub(r'[^a-z0-9]', '', (s or '').lower())
    return norm(title) + ('|' + norm(organization) if pillar == 'jobs' else '')


# =====================================================================
# FILTERS
# =====================================================================

def _has_word(text, words):
    return any(re.search(r'(?<![a-z0-9])' + re.escape(w) + r'(?![a-z0-9])', text) for w in words)


def is_relevant_job(title, keywords):
    """No senior roles, and the title must match a field keyword (python, data, ...).
    'Intern' alone isn't enough: that lets in Sales / HR internships."""
    t = (title or '').lower()
    if _has_word(t, EXCLUDE):
        return False
    field_words = [k for k in keywords if k not in EARLY_CAREER] or EARLY_CAREER
    return _has_word(t, field_words)


def is_fresh(it, today):
    """Upcoming events only; jobs and news only if recent."""
    days_old = lambda iso: (today - datetime.strptime(iso, '%Y-%m-%d').date()).days
    try:
        if it['deadline'] and it['deadline'] < today.isoformat():
            return False
        if it['pillar'] == 'events':
            if not it['deadline'] and it['starts_at']:
                return it['starts_at'] >= today.isoformat()
            if not it['deadline'] and it['posted_at']:
                return days_old(it['posted_at']) <= EVENT_UNDATED_MAX_AGE
            return True
        if it['pillar'] == 'jobs':
            return it['deadline'] is not None or not it['posted_at'] or days_old(it['posted_at']) <= JOB_MAX_AGE
        return not it['posted_at'] or days_old(it['posted_at']) <= NEWS_MAX_AGE
    except (TypeError, ValueError):
        return True


# Same rules as is_fresh, in SQL, for the feed and the cleanup job
VISIBLE_SQL = f"""(
    (deadline IS NOT NULL AND deadline >= date('now', 'localtime'))
    OR (deadline IS NULL AND pillar = 'events' AND (
        starts_at >= date('now', 'localtime')
        OR (starts_at IS NULL AND COALESCE(posted_at, date(created_at)) >= date('now', 'localtime', '-{EVENT_UNDATED_MAX_AGE} days'))))
    OR (deadline IS NULL AND pillar = 'jobs'
        AND COALESCE(posted_at, date(created_at)) >= date('now', 'localtime', '-{JOB_MAX_AGE} days'))
    OR (deadline IS NULL AND pillar = 'news'
        AND COALESCE(posted_at, date(created_at)) >= date('now', 'localtime', '-{NEWS_MAX_AGE} days'))
)"""


# =====================================================================
# DATABASE SETUP & ONE-TIME CLEANUP OF OLD DUPLICATES
# =====================================================================

def init_radar_db():
    """Create radar_items, add new columns to old DBs, remove existing duplicates once."""
    conn = get_db()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS radar_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pillar TEXT NOT NULL,         -- 'jobs', 'events', 'news'
            source TEXT NOT NULL,
            title TEXT NOT NULL,
            organization TEXT,
            url TEXT NOT NULL UNIQUE,
            deadline_or_date TEXT,        -- human readable date line
            extra_info TEXT,              -- prize, type, location
            notified INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cols = [r['name'] for r in conn.execute("PRAGMA table_info(radar_items)")]
    for col, kind in (('deadline', 'TEXT'), ('starts_at', 'TEXT'), ('posted_at', 'TEXT'),
                      ('url_key', 'TEXT'), ('title_key', 'TEXT'),
                      ('city', 'TEXT'), ('region', 'TEXT'), ('lat', 'REAL'), ('lon', 'REAL'),
                      ('mode', 'TEXT'), ('loc_done', 'INTEGER')):
        if col not in cols:
            conn.execute(f"ALTER TABLE radar_items ADD COLUMN {col} {kind}")

    if conn.execute("SELECT 1 FROM radar_items WHERE url_key IS NULL LIMIT 1").fetchone():
        _dedupe_existing(conn)
    if conn.execute("SELECT 1 FROM radar_items WHERE loc_done IS NULL LIMIT 1").fetchone():
        _locate_existing(conn)
    _tidy_existing(conn)

    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_radar_url_key ON radar_items(url_key)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_radar_title_key ON radar_items(pillar, title_key)")
    conn.commit()
    conn.close()


def _location_text(it):
    return ' '.join(filter(None, (it.get('extra_info'), it.get('organization'), it.get('title'))))


def _locate_existing(conn):
    """One-time: detect city / mode for rows stored before location support."""
    rows = conn.execute("SELECT id, source, title, organization, extra_info FROM radar_items WHERE loc_done IS NULL").fetchall()
    for r in rows:
        loc = locations.detect(_location_text(dict(r)), r['source'])
        conn.execute("UPDATE radar_items SET city = ?, region = ?, lat = ?, lon = ?, mode = ?, loc_done = 1 WHERE id = ?",
                     (loc['city'], loc['region'], loc['lat'], loc['lon'], loc['mode'], r['id']))


def _tidy_existing(conn):
    """Strip emojis and bullet separators from rows stored before tidy() existed."""
    for r in conn.execute("SELECT id, title, extra_info FROM radar_items").fetchall():
        title, extra = tidy(r['title']), tidy(r['extra_info'])
        if (title, extra) != (r['title'], r['extra_info'] or ''):
            conn.execute("UPDATE radar_items SET title = ?, extra_info = ? WHERE id = ?", (title, extra, r['id']))


def _dedupe_existing(conn):
    """Fill keys for old rows and delete duplicates, keeping saved / oldest copies."""
    # Old 'events' from the Google Developers blog were really news posts
    conn.execute("UPDATE radar_items SET pillar = 'news' WHERE source = 'Google Developers' AND pillar = 'events'")
    has_saved = conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='saved_items'").fetchone()
    saved = {r[0] for r in conn.execute("SELECT item_id FROM saved_items")} if has_saved else set()

    seen = {}
    rows = conn.execute("SELECT id, pillar, title, organization, url FROM radar_items ORDER BY id").fetchall()
    rows = sorted(rows, key=lambda r: (r['id'] not in saved, r['id']))  # saved copies win
    for r in rows:
        keys = (url_key(r['url']), (r['pillar'], title_key(r['pillar'], r['title'], r['organization'])))
        keep = seen.get(keys[0]) or seen.get(keys[1])
        if keep:
            if has_saved:
                conn.execute("UPDATE OR IGNORE saved_items SET item_id = ? WHERE item_id = ?", (keep, r['id']))
                conn.execute("DELETE FROM saved_items WHERE item_id = ?", (r['id'],))
            conn.execute("DELETE FROM radar_items WHERE id = ?", (r['id'],))
            continue
        seen[keys[0]] = seen[keys[1]] = r['id']
        conn.execute("UPDATE radar_items SET url_key = ?, title_key = ? WHERE id = ?",
                     (keys[0], keys[1][1], r['id']))


# =====================================================================
# SCANNING
# =====================================================================

def _store(conn, it):
    """Insert one item unless it's a duplicate. Returns True when new."""
    ukey = url_key(it['url'])
    tkey = title_key(it['pillar'], it['title'], it['organization'])
    dup = conn.execute(
        "SELECT id, deadline FROM radar_items WHERE url_key = ? OR (pillar = ? AND title_key = ?) LIMIT 1",
        (ukey, it['pillar'], tkey)
    ).fetchone()
    if dup:
        if not dup['deadline'] and it['deadline']:  # Another site knows the deadline: keep it
            conn.execute("UPDATE radar_items SET deadline = ? WHERE id = ?", (it['deadline'], dup['id']))
        return False
    loc = locations.detect(_location_text(it), it['source'])
    try:
        conn.execute('''
            INSERT INTO radar_items (pillar, source, title, organization, url, deadline_or_date, extra_info,
                                     deadline, starts_at, posted_at, url_key, title_key,
                                     city, region, lat, lon, mode, loc_done)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
        ''', (it['pillar'], it['source'], it['title'], it['organization'], it['url'], it['date_text'],
              it['extra_info'], it['deadline'], it['starts_at'], it['posted_at'], ukey, tkey,
              loc['city'], loc['region'], loc['lat'], loc['lon'], loc['mode']))
        return True
    except sqlite3.IntegrityError:
        return False


def scan(pillars=('jobs', 'events', 'news')):
    """Scan every website of the given pillars, sequentially."""
    if not _scan_lock.acquire(blocking=False):
        print("[Radar] Scan already running, skipped.")
        return {}
    try:
        init_radar_db()
        keywords = get_keywords()
        today = datetime.now(IST).date()
        new_items, failed = [], []

        for name, pillar, fetcher in SOURCES:
            if pillar not in pillars:
                continue
            try:
                items = [it for it in fetcher() if it['title'] and it['url'].startswith('http')]
            except Exception as e:
                failed.append(name)
                print(f"[Radar] {name} failed: {e}")
                continue

            if pillar == 'jobs':
                items = [it for it in items if is_relevant_job(it['title'], keywords)]
            items = [it for it in items if is_fresh(it, today)]
            if pillar == 'events':  # soonest first
                items.sort(key=lambda it: it['starts_at'] or it['deadline'] or '9999')
            else:  # newest first
                items.sort(key=lambda it: it['posted_at'] or '', reverse=True)

            conn = get_db()
            for it in items[:PER_SOURCE_CAP[pillar]]:
                if _store(conn, it):
                    new_items.append(it)
            conn.commit()
            conn.close()

        cleanup_old_items()
        conn = get_db()
        conn.execute("REPLACE INTO settings (key, value) VALUES ('last_scan_at', ?)",
                     (datetime.now(IST).strftime('%Y-%m-%dT%H:%M:%S'),))
        conn.commit()
        conn.close()
        counts = {p: sum(1 for it in new_items if it['pillar'] == p) for p in pillars}
        print(f"[Radar] Scan complete: {counts}. Failed sources: {failed or 'none'}")
        _notify_new(new_items)
        return counts
    finally:
        _scan_lock.release()


def _notify_new(new_items):
    """One summary push per scan for new jobs/events (news never pushes)."""
    opps = [it for it in new_items if it['pillar'] in ('jobs', 'events')]
    if not opps:
        return
    try:
        from services.notifier import notify
        jobs = sum(1 for it in opps if it['pillar'] == 'jobs')
        events = len(opps) - jobs
        lines = [f"• {it['title'][:60]} ({it['source']})" for it in opps[:4]]
        notify(
            title=f"{jobs} new roles, {events} new events",
            message="\n".join(lines),
            priority="default",
            tags=["satellite"]
        )
    except Exception as ex:
        print(f"Radar notify error: {ex}")


def scan_all_radar():
    return scan(('jobs', 'events', 'news'))


def scan_high_priority():
    """Jobs & hackathons only (quick, focused)."""
    return scan(('jobs', 'events'))


def scan_jobs_only():
    """Jobs & internships only: they change fastest."""
    return scan(('jobs',))


def cleanup_old_items():
    """Delete expired / stale items nobody saved, so the DB stays small."""
    conn = get_db()
    has_saved = conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='saved_items'").fetchone()
    keep_saved = "id NOT IN (SELECT item_id FROM saved_items) AND" if has_saved else ""
    conn.execute(f"DELETE FROM radar_items WHERE {keep_saved} NOT {VISIBLE_SQL}")
    conn.commit()
    conn.close()


# =====================================================================
# QUERIES
# =====================================================================

def is_scanning():
    return _scan_lock.locked()


def _pick_score(row, keywords):
    """How many interest keywords appear in the item: used for 'Top picks'."""
    text = ' '.join(filter(None, (row['title'], row['organization'], row['extra_info']))).lower()
    return sum(1 for k in keywords if _has_word(text, [k]))


ONLINE_MODES = ('online', 'remote', 'hybrid')


def _with_distance(items, near):
    """Add distance_km (from the user's location) to items that have a known city."""
    for it in items:
        it['distance_km'] = (round(locations.distance_km(near[0], near[1], it['lat'], it['lon']))
                             if near and it.get('lat') is not None else None)
    return items


def get_radar_items(pillar=None, limit=5, q=None, offset=0, sort='latest', source=None,
                    near=None, radius=50, loc=None):
    """Visible (upcoming / fresh) items.

    sort: 'latest' (newest first), 'closing' (nearest deadline first),
          'picks' (best match with interest keywords, then newest).
    near: (lat, lon) of the user; adds distance_km to every item.
    loc:  None (anywhere), 'near' (within radius km, nearest first),
          'near_online' (near + anything online/remote), 'online' (online/remote only).
    """
    if loc in ('near', 'near_online') and near:
        rows = get_radar_items(pillar=pillar, limit=600, q=q, sort=sort, source=source)
        _with_distance(rows, near)
        # "Near" means you can go there: online / remote items only come with 'near_online'
        close = [r for r in rows if r['distance_km'] is not None and r['distance_km'] <= radius
                 and r.get('mode') not in ('online', 'remote')]
        close.sort(key=lambda r: r['distance_km'])  # stable: keeps the chosen sort for ties
        if loc == 'near_online':
            close += [r for r in rows if r not in close and r.get('mode') in ONLINE_MODES]
        return close[offset:offset + limit]

    init_radar_db()
    conn = get_db()
    sql = f"SELECT * FROM radar_items WHERE {VISIBLE_SQL}"
    args = []
    if pillar == 'opps':  # Jobs + events, without news
        sql += " AND pillar IN ('jobs', 'events')"
    elif pillar:
        sql += " AND pillar = ?"
        args.append(pillar)
    if source:
        sql += " AND source = ?"
        args.append(source)
    if loc == 'online':
        sql += " AND mode IN ('online', 'remote', 'hybrid')"
    if q:
        sql += " AND (title LIKE ? OR organization LIKE ? OR extra_info LIKE ? OR source LIKE ?)"
        args += [f"%{q}%"] * 4

    latest = " ORDER BY COALESCE(posted_at, date(created_at)) DESC, id DESC"
    if sort == 'picks':
        rows = conn.execute(sql + latest + " LIMIT 400", args).fetchall()
        conn.close()
        keywords = get_keywords()
        scored = [(_pick_score(r, keywords), i, r) for i, r in enumerate(rows)]
        scored = [s for s in scored if s[0] > 0]
        scored.sort(key=lambda s: (-s[0], s[1]))  # best score, then newest
        return _with_distance([dict(r, score=sc) for sc, _, r in scored[offset:offset + limit]], near)

    if sort == 'closing':
        sql += " AND deadline IS NOT NULL ORDER BY deadline ASC, id DESC"
    else:
        sql += latest
    sql += " LIMIT ? OFFSET ?"
    args += [limit, offset]
    rows = conn.execute(sql, args).fetchall()
    conn.close()
    return _with_distance([dict(r) for r in rows], near)


def get_city_counts():
    """Visible opportunities per detected city (for the location picker)."""
    init_radar_db()
    conn = get_db()
    counts = {r[0]: r[1] for r in conn.execute(
        f"SELECT city, COUNT(*) FROM radar_items WHERE {VISIBLE_SQL} AND pillar IN ('jobs', 'events') "
        "AND city IS NOT NULL GROUP BY city")}
    conn.close()
    return counts


def get_counts():
    """Visible items per pillar and per source (feed chips and source filter)."""
    init_radar_db()
    conn = get_db()
    pillars = {r[0]: r[1] for r in conn.execute(
        f"SELECT pillar, COUNT(*) FROM radar_items WHERE {VISIBLE_SQL} GROUP BY pillar")}
    sources = [{'source': r[0], 'pillar': r[1], 'count': r[2]} for r in conn.execute(
        f"SELECT source, pillar, COUNT(*) FROM radar_items WHERE {VISIBLE_SQL} "
        "GROUP BY source, pillar ORDER BY COUNT(*) DESC")]
    new_today = conn.execute(
        f"SELECT COUNT(*) FROM radar_items WHERE {VISIBLE_SQL} AND pillar IN ('jobs', 'events') "
        "AND date(created_at, 'localtime') = date('now', 'localtime')").fetchone()[0]
    conn.close()
    return pillars, sources, new_today
