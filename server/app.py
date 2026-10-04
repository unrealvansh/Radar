"""
PocketBrain — Your Personal Automation Server
Main Flask application with all API routes.
"""

from flask import Flask, jsonify, request, send_from_directory
from datetime import datetime
import sqlite3
import os

# ============ APP SETUP ============

# __file__ = this file's path
# We go up one level (..) to reach the project root (pocketbrain/)
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

app = Flask(__name__,
    static_folder=os.path.join(BASE_DIR, 'frontend'),  # Serve dashboard files
    static_url_path=''                                   # Serve at root URL
)

DB_PATH = os.path.join(BASE_DIR, 'data', 'pocketbrain.db')


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
    """Create all tables if they don't exist.
    
    This runs once when the server starts.
    IF NOT EXISTS means it won't break if tables already exist.
    """
    conn = get_db()
    conn.executescript('''
        CREATE TABLE IF NOT EXISTS expenses (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            amount      REAL NOT NULL,
            category    TEXT DEFAULT 'misc',
            description TEXT,
            date        TEXT DEFAULT (date('now')),
            created_at  TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS habits (
            id   INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            icon TEXT DEFAULT '✅'
        );

        CREATE TABLE IF NOT EXISTS habit_logs (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            habit_name TEXT NOT NULL,
            date       TEXT DEFAULT (date('now')),
            note       TEXT,
            UNIQUE(habit_name, date)
        );

        CREATE TABLE IF NOT EXISTS attendance (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            subject    TEXT NOT NULL,
            date       TEXT DEFAULT (date('now')),
            status     TEXT NOT NULL DEFAULT 'present',
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS bookmarks (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            url        TEXT NOT NULL,
            title      TEXT,
            tags       TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );
    ''')
    conn.commit()
    conn.close()
    print("✅ Database initialized!")


# ============ API: HEALTH CHECK ============

@app.route('/api/health')
def health():
    """Check if the server is alive.
    
    Useful for monitoring / uptime checks.
    Try it: curl http://localhost:5000/api/health
    """
    return jsonify({
        'status': 'alive',
        'server': 'PocketBrain',
        'time': datetime.now().isoformat(),
        'message': '🧠 PocketBrain is running!'
    })


# ============ API: EXPENSES ============

@app.route('/api/expenses', methods=['GET'])
def get_expenses():
    """Get expenses. Optional query param: ?date=2026-10-04"""
    conn = get_db()
    date = request.args.get('date')
    if date:
        rows = conn.execute(
            'SELECT * FROM expenses WHERE date = ? ORDER BY created_at DESC',
            (date,)
        ).fetchall()
    else:
        rows = conn.execute(
            'SELECT * FROM expenses ORDER BY created_at DESC LIMIT 50'
        ).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route('/api/expenses', methods=['POST'])
def add_expense():
    """Add a new expense.
    
    Send JSON body: {"amount": 20, "description": "chai", "category": "food"}
    """
    data = request.get_json()
    if not data or 'amount' not in data:
        return jsonify({'status': 'error', 'message': 'amount is required'}), 400
    
    conn = get_db()
    conn.execute(
        'INSERT INTO expenses (amount, description, category) VALUES (?, ?, ?)',
        (data['amount'], data.get('description', ''), data.get('category', 'misc'))
    )
    conn.commit()
    conn.close()
    return jsonify({'status': 'ok', 'message': f'₹{data["amount"]} logged!'})


@app.route('/api/expenses/summary')
def expense_summary():
    """Get today's and this month's total spending."""
    conn = get_db()
    today = conn.execute(
        "SELECT COALESCE(SUM(amount), 0) as total FROM expenses WHERE date = date('now')"
    ).fetchone()
    month = conn.execute(
        "SELECT COALESCE(SUM(amount), 0) as total FROM expenses "
        "WHERE strftime('%Y-%m', date) = strftime('%Y-%m', 'now')"
    ).fetchone()
    conn.close()
    return jsonify({
        'today': today['total'],
        'this_month': month['total']
    })


# ============ API: HABITS ============

@app.route('/api/habits', methods=['GET'])
def get_habits():
    """Get all habits with today's check-in status."""
    conn = get_db()
    habits = conn.execute('SELECT * FROM habits').fetchall()
    result = []
    for h in habits:
        log = conn.execute(
            "SELECT * FROM habit_logs WHERE habit_name = ? AND date = date('now')",
            (h['name'],)
        ).fetchone()
        result.append({
            'name': h['name'],
            'icon': h['icon'],
            'done_today': log is not None
        })
    conn.close()
    return jsonify(result)


@app.route('/api/habits', methods=['POST'])
def add_habit():
    """Create a new habit. Send JSON: {"name": "gym", "icon": "💪"}"""
    data = request.get_json()
    if not data or 'name' not in data:
        return jsonify({'status': 'error', 'message': 'name is required'}), 400
    
    conn = get_db()
    try:
        conn.execute(
            'INSERT INTO habits (name, icon) VALUES (?, ?)',
            (data['name'], data.get('icon', '✅'))
        )
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({'status': 'error', 'message': 'Habit already exists'}), 400
    conn.close()
    return jsonify({'status': 'ok', 'message': f'{data["name"]} added!'})


@app.route('/api/habits/check', methods=['POST'])
def check_habit():
    """Mark a habit as done today. Send JSON: {"name": "gym"}"""
    data = request.get_json()
    conn = get_db()
    try:
        conn.execute(
            'INSERT INTO habit_logs (habit_name) VALUES (?)',
            (data['name'],)
        )
        conn.commit()
        msg = f'{data["name"]} ✅ done!'
    except sqlite3.IntegrityError:
        msg = f'{data["name"]} already checked today'
    conn.close()
    return jsonify({'status': 'ok', 'message': msg})


# ============ API: ATTENDANCE ============

@app.route('/api/attendance', methods=['GET'])
def get_attendance():
    """Get attendance summary per subject with bunk calculation.
    
    The bunk calculator answers: "How many more classes can I skip 
    and still stay above 75%?"
    
    Formula: If I have P present out of T total,
    I can bunk B more if: P / (T + B + 1) >= 0.75
    Solving: B <= (P / 0.75) - T - 1
    """
    conn = get_db()
    subjects = conn.execute(
        'SELECT DISTINCT subject FROM attendance'
    ).fetchall()
    
    result = []
    for s in subjects:
        subj = s['subject']
        total = conn.execute(
            "SELECT COUNT(*) as c FROM attendance "
            "WHERE subject = ? AND status != 'cancelled'",
            (subj,)
        ).fetchone()['c']
        present = conn.execute(
            "SELECT COUNT(*) as c FROM attendance "
            "WHERE subject = ? AND status = 'present'",
            (subj,)
        ).fetchone()['c']
        
        pct = round((present / total * 100), 1) if total > 0 else 0
        
        # Bunk calculator
        safe_bunks = 0
        if total > 0:
            t, p = total, present
            while (p / (t + 1)) * 100 >= 75:
                t += 1
                safe_bunks += 1
        
        result.append({
            'subject': subj,
            'total': total,
            'present': present,
            'percentage': pct,
            'safe_bunks': safe_bunks,
            'danger': pct < 78  # Warn when getting close to 75%
        })
    
    conn.close()
    return jsonify(result)


@app.route('/api/attendance', methods=['POST'])
def log_attendance():
    """Log attendance for a subject.
    
    Send JSON: {"subject": "OS", "status": "present"}
    status can be: "present", "absent", "cancelled"
    """
    data = request.get_json()
    if not data or 'subject' not in data:
        return jsonify({'status': 'error', 'message': 'subject is required'}), 400
    
    conn = get_db()
    conn.execute(
        'INSERT INTO attendance (subject, status) VALUES (?, ?)',
        (data['subject'].upper(), data.get('status', 'present'))
    )
    conn.commit()
    conn.close()
    return jsonify({'status': 'ok', 'message': f'{data["subject"]} → {data.get("status", "present")}'})


# ============ API: BOOKMARKS ============

@app.route('/api/bookmarks', methods=['GET'])
def get_bookmarks():
    """Get all saved bookmarks."""
    conn = get_db()
    rows = conn.execute(
        'SELECT * FROM bookmarks ORDER BY created_at DESC LIMIT 50'
    ).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route('/api/bookmarks', methods=['POST'])
def add_bookmark():
    """Save a bookmark. Send JSON: {"url": "...", "title": "...", "tags": "python,tutorial"}"""
    data = request.get_json()
    if not data or 'url' not in data:
        return jsonify({'status': 'error', 'message': 'url is required'}), 400
    
    conn = get_db()
    conn.execute(
        'INSERT INTO bookmarks (url, title, tags) VALUES (?, ?, ?)',
        (data['url'], data.get('title', ''), data.get('tags', ''))
    )
    conn.commit()
    conn.close()
    return jsonify({'status': 'ok', 'message': 'Bookmark saved!'})


# ============ API: DASHBOARD ============

@app.route('/api/dashboard')
def dashboard():
    """Get a summary of everything for the dashboard home screen."""
    conn = get_db()
    
    today_spent = conn.execute(
        "SELECT COALESCE(SUM(amount), 0) as total FROM expenses WHERE date = date('now')"
    ).fetchone()['total']
    
    month_spent = conn.execute(
        "SELECT COALESCE(SUM(amount), 0) as total FROM expenses "
        "WHERE strftime('%Y-%m', date) = strftime('%Y-%m', 'now')"
    ).fetchone()['total']
    
    habits_total = conn.execute('SELECT COUNT(*) as c FROM habits').fetchone()['c']
    habits_done = conn.execute(
        "SELECT COUNT(*) as c FROM habit_logs WHERE date = date('now')"
    ).fetchone()['c']
    
    recent = conn.execute(
        'SELECT * FROM expenses ORDER BY created_at DESC LIMIT 5'
    ).fetchall()
    
    conn.close()
    return jsonify({
        'today_spent': today_spent,
        'month_spent': month_spent,
        'habits_total': habits_total,
        'habits_done': habits_done,
        'recent_expenses': [dict(r) for r in recent],
        'server_time': datetime.now().strftime('%I:%M %p, %d %b %Y')
    })


# ============ SERVE DASHBOARD ============

@app.route('/')
def serve_dashboard():
    """Serve the PWA dashboard (index.html)."""
    return send_from_directory(app.static_folder, 'index.html')


# ============ START SERVER ============

if __name__ == '__main__':
    # Create data directory if it doesn't exist
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    
    init_db()
    
    print("=" * 50)
    print("🧠 PocketBrain Server Starting...")
    print(f"📱 Dashboard: http://0.0.0.0:5000")
    print(f"📂 Database:  {DB_PATH}")
    print("=" * 50)
    
    app.run(host='0.0.0.0', port=5000, debug=True)
