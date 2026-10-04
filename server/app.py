"""
PocketBrain — Your Personal Automation Server
Main Flask application with all API routes.
"""

from flask import Flask, jsonify, request, send_from_directory
from datetime import datetime, timedelta
import sqlite3
import os
import sys

# Fix Windows console encoding for emoji/unicode
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

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

        -- Deadlines
        CREATE TABLE IF NOT EXISTS deadlines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            subject TEXT,
            due_date TEXT NOT NULL,  -- ISO format: 2026-10-08
            due_time TEXT DEFAULT '23:59',  -- HH:MM format
            completed INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- Quick Notes / Saved Messages
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT NOT NULL,
            tags TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- Settings (key-value store for budget, preferences, etc.)
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );

        -- Custom User Reminders
        CREATE TABLE IF NOT EXISTS reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            remind_at TEXT NOT NULL,       -- YYYY-MM-DD HH:MM
            category TEXT DEFAULT 'personal', -- homework, assignment, gym, skills, exam, personal
            repeat TEXT DEFAULT 'none',     -- none, daily, weekly
            notified INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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


@app.route('/api/expenses/<int:id>', methods=['PUT'])
def update_expense(id):
    """Update an existing expense."""
    data = request.get_json()
    if not data or 'amount' not in data:
        return jsonify({'status': 'error', 'message': 'amount is required'}), 400
    conn = get_db()
    conn.execute(
        'UPDATE expenses SET amount = ?, description = ?, category = ? WHERE id = ?',
        (data['amount'], data.get('description', ''), data.get('category', 'misc'), id)
    )
    conn.commit()
    conn.close()
    return jsonify({'status': 'ok', 'message': 'Expense updated!'})


@app.route('/api/expenses/<int:id>', methods=['DELETE'])
def delete_expense(id):
    """Delete an expense."""
    conn = get_db()
    conn.execute('DELETE FROM expenses WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    return jsonify({'status': 'ok', 'message': 'Expense deleted!'})


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


@app.route('/api/habits/uncheck', methods=['POST'])
def uncheck_habit():
    """Uncheck a habit for today."""
    data = request.get_json()
    conn = get_db()
    conn.execute(
        "DELETE FROM habit_logs WHERE habit_name = ? AND date = date('now')",
        (data['name'],)
    )
    conn.commit()
    conn.close()
    return jsonify({'status': 'ok', 'message': f'{data["name"]} unchecked!'})


@app.route('/api/habits/<name>', methods=['DELETE'])
def delete_habit(name):
    """Delete a habit completely."""
    conn = get_db()
    conn.execute('DELETE FROM habits WHERE name = ?', (name,))
    conn.execute('DELETE FROM habit_logs WHERE habit_name = ?', (name,))
    conn.commit()
    conn.close()
    return jsonify({'status': 'ok', 'message': f'{name} deleted!'})


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


# ============ API: DEADLINES ============

@app.route('/api/deadlines', methods=['GET'])
def get_deadlines():
    """Get all incomplete deadlines sorted by due_date ASC."""
    conn = get_db()
    rows = conn.execute(
        'SELECT * FROM deadlines WHERE completed = 0 ORDER BY due_date ASC'
    ).fetchall()
    
    result = []
    today = datetime.now().date()
    for r in rows:
        d = dict(r)
        try:
            due = datetime.strptime(d['due_date'], '%Y-%m-%d').date()
            days_left = (due - today).days
        except ValueError:
            days_left = 999
            
        d['days_left'] = days_left
        if days_left < 0:
            d['urgency'] = 'overdue'
        elif days_left == 0:
            d['urgency'] = 'today'
        elif days_left <= 2:
            d['urgency'] = 'urgent'
        elif days_left <= 5:
            d['urgency'] = 'soon'
        else:
            d['urgency'] = 'ok'
        result.append(d)
        
    conn.close()
    return jsonify(result)

@app.route('/api/deadlines', methods=['POST'])
def add_deadline():
    """Create deadline."""
    data = request.get_json()
    if not data or 'title' not in data or 'due_date' not in data:
        return jsonify({'status': 'error', 'message': 'title and due_date are required'}), 400
        
    conn = get_db()
    conn.execute(
        'INSERT INTO deadlines (title, subject, due_date, due_time) VALUES (?, ?, ?, ?)',
        (data['title'], data.get('subject'), data['due_date'], data.get('due_time', '23:59'))
    )
    conn.commit()
    conn.close()
    return jsonify({'status': 'ok', 'message': 'Deadline added!'})

@app.route('/api/deadlines/<int:id>/complete', methods=['POST'])
def complete_deadline(id):
    """Mark a deadline as completed."""
    conn = get_db()
    conn.execute('UPDATE deadlines SET completed = 1 WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    return jsonify({'status': 'ok', 'message': 'Deadline completed!'})

@app.route('/api/deadlines/<int:id>', methods=['PUT'])
def update_deadline(id):
    """Update a deadline."""
    data = request.get_json()
    if not data or 'title' not in data or 'due_date' not in data:
        return jsonify({'status': 'error', 'message': 'title and due_date are required'}), 400
    conn = get_db()
    conn.execute(
        'UPDATE deadlines SET title = ?, subject = ?, due_date = ?, due_time = ? WHERE id = ?',
        (data['title'], data.get('subject'), data['due_date'], data.get('due_time', '23:59'), id)
    )
    conn.commit()
    conn.close()
    return jsonify({'status': 'ok', 'message': 'Deadline updated!'})


@app.route('/api/deadlines/<int:id>', methods=['DELETE'])
def delete_deadline(id):
    """Delete a deadline."""
    conn = get_db()
    conn.execute('DELETE FROM deadlines WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    return jsonify({'status': 'ok', 'message': 'Deadline deleted!'})


# ============ API: REMINDERS (Custom User Reminders) ============

@app.route('/api/reminders', methods=['GET'])
def get_reminders():
    """Get all upcoming and recent custom reminders."""
    conn = get_db()
    rows = conn.execute(
        'SELECT * FROM reminders ORDER BY remind_at ASC LIMIT 100'
    ).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route('/api/reminders', methods=['POST'])
def add_reminder():
    """Create a new custom reminder.
    JSON: { "title": "Buy medicine", "remind_at": "2026-10-04 18:00", "category": "personal", "repeat": "none" }
    """
    data = request.get_json()
    if not data or 'title' not in data or 'remind_at' not in data:
        return jsonify({'status': 'error', 'message': 'title and remind_at are required'}), 400
        
    conn = get_db()
    cursor = conn.execute(
        'INSERT INTO reminders (title, remind_at, category, repeat) VALUES (?, ?, ?, ?)',
        (data['title'], data['remind_at'], data.get('category', 'personal'), data.get('repeat', 'none'))
    )
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()
    
    # Send a quick confirmation push
    try:
        from services.notifier import send_push
        send_push(
            title="⏰ Reminder Set",
            message=f"'{data['title']}' for {data['remind_at']}",
            priority="default",
            tags=["bell", "clock"]
        )
    except Exception:
        pass
        
    return jsonify({'status': 'ok', 'id': new_id, 'message': 'Reminder set!'})


@app.route('/api/reminders/<int:id>', methods=['PUT'])
def update_reminder(id):
    """Update a custom reminder."""
    data = request.get_json()
    if not data or 'title' not in data or 'remind_at' not in data:
        return jsonify({'status': 'error', 'message': 'title and remind_at are required'}), 400
    conn = get_db()
    conn.execute(
        'UPDATE reminders SET title = ?, remind_at = ?, category = ?, repeat = ?, notified = 0 WHERE id = ?',
        (data['title'], data['remind_at'], data.get('category', 'personal'), data.get('repeat', 'none'), id)
    )
    conn.commit()
    conn.close()
    return jsonify({'status': 'ok', 'message': 'Reminder updated!'})


@app.route('/api/reminders/<int:id>', methods=['DELETE'])
def delete_reminder(id):
    """Delete a custom reminder."""
    conn = get_db()
    conn.execute('DELETE FROM reminders WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    return jsonify({'status': 'ok', 'message': 'Reminder deleted!'})

# ============ API: NOTES ============

@app.route('/api/notes', methods=['GET'])
def get_notes():
    """Returns all notes, newest first, limit 50."""
    conn = get_db()
    rows = conn.execute(
        'SELECT * FROM notes ORDER BY created_at DESC LIMIT 50'
    ).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route('/api/notes', methods=['POST'])
def add_note():
    """Create a note."""
    data = request.get_json()
    if not data or 'content' not in data:
        return jsonify({'status': 'error', 'message': 'content is required'}), 400
        
    conn = get_db()
    conn.execute(
        'INSERT INTO notes (content, tags) VALUES (?, ?)',
        (data['content'], data.get('tags', ''))
    )
    conn.commit()
    conn.close()
    return jsonify({'status': 'ok', 'message': 'Note added!'})

# ============ API: SETTINGS ============

@app.route('/api/settings/<key>', methods=['GET'])
def get_setting(key):
    """Get a setting value."""
    conn = get_db()
    row = conn.execute('SELECT value FROM settings WHERE key = ?', (key,)).fetchone()
    conn.close()
    if row:
        return jsonify({'key': key, 'value': row['value']})
    return jsonify({'status': 'error', 'message': 'Setting not found'}), 404

@app.route('/api/settings', methods=['POST'])
def set_setting():
    """Set a setting."""
    data = request.get_json()
    if not data or 'key' not in data or 'value' not in data:
        return jsonify({'status': 'error', 'message': 'key and value are required'}), 400
        
    conn = get_db()
    # Using REPLACE since key is PRIMARY KEY
    conn.execute(
        'REPLACE INTO settings (key, value) VALUES (?, ?)',
        (data['key'], data['value'])
    )
    conn.commit()
    conn.close()
    return jsonify({'status': 'ok', 'message': 'Setting saved!'})

# ============ API: BRIEFING ============

@app.route('/api/briefing', methods=['GET'])
def get_briefing():
    """Returns the morning briefing data."""
    conn = get_db()
    
    # 1. Deadlines (upcoming 5)
    dl_rows = conn.execute(
        'SELECT * FROM deadlines WHERE completed = 0 ORDER BY due_date ASC LIMIT 5'
    ).fetchall()
    
    deadlines = []
    today = datetime.now().date()
    for r in dl_rows:
        d = dict(r)
        try:
            due = datetime.strptime(d['due_date'], '%Y-%m-%d').date()
            days_left = (due - today).days
        except ValueError:
            days_left = 999
            
        d['days_left'] = days_left
        if days_left < 0:
            d['urgency'] = 'overdue'
        elif days_left == 0:
            d['urgency'] = 'today'
        elif days_left <= 2:
            d['urgency'] = 'urgent'
        elif days_left <= 5:
            d['urgency'] = 'soon'
        else:
            d['urgency'] = 'ok'
        deadlines.append(d)
        
    # 2. Attendance Warnings (below 78%)
    subjects = conn.execute('SELECT DISTINCT subject FROM attendance').fetchall()
    attendance_warnings = []
    for s in subjects:
        subj = s['subject']
        total = conn.execute(
            "SELECT COUNT(*) as c FROM attendance WHERE subject = ? AND status != 'cancelled'", (subj,)
        ).fetchone()['c']
        present = conn.execute(
            "SELECT COUNT(*) as c FROM attendance WHERE subject = ? AND status = 'present'", (subj,)
        ).fetchone()['c']
        
        pct = round((present / total * 100), 1) if total > 0 else 0
        
        if total > 0 and pct < 78:
            safe_bunks = 0
            t, p = total, present
            while (p / (t + 1)) * 100 >= 75:
                t += 1
                safe_bunks += 1
            attendance_warnings.append({
                'subject': subj,
                'percentage': pct,
                'safe_bunks': safe_bunks
            })
            
    # 3. Spending
    today_spending = conn.execute(
        "SELECT COALESCE(SUM(amount), 0) as total FROM expenses WHERE date = date('now')"
    ).fetchone()['total']
    
    # SQLite strftime('%W') returns week number
    week_spending = conn.execute(
        "SELECT COALESCE(SUM(amount), 0) as total FROM expenses "
        "WHERE strftime('%W', date) = strftime('%W', 'now') AND strftime('%Y', date) = strftime('%Y', 'now')"
    ).fetchone()['total']
    
    budget_row = conn.execute("SELECT value FROM settings WHERE key = 'weekly_budget'").fetchone()
    weekly_budget = float(budget_row['value']) if budget_row else 2000
    budget_remaining = weekly_budget - week_spending
    
    # 4. Habits
    habits = conn.execute('SELECT * FROM habits').fetchall()
    habits_today = []
    for h in habits:
        log = conn.execute(
            "SELECT * FROM habit_logs WHERE habit_name = ? AND date = date('now')",
            (h['name'],)
        ).fetchone()
        habits_today.append({
            'name': h['name'],
            'icon': h['icon'],
            'done': log is not None
        })
        
    conn.close()
    
    return jsonify({
        "deadlines": deadlines,
        "attendance_warnings": attendance_warnings,
        "today_spending": today_spending,
        "week_spending": week_spending,
        "weekly_budget": weekly_budget,
        "budget_remaining": budget_remaining,
        "habits_today": habits_today,
        "server_time": datetime.now().strftime('%I:%M %p, %d %b %Y')
    })


# ============ API: CHAT (Smart Parser) ============

from chat_parser import parse_message

@app.route('/api/chat', methods=['POST'])
def chat():
    """Send a natural language message to PocketBrain.
    
    Send JSON: {"message": "chai 20"}
    Returns: {"action": "expense", "response": "🍕 ₹20 logged → chai (food)"}
    """
    data = request.get_json()
    if not data or 'message' not in data:
        return jsonify({'status': 'error', 'message': 'message is required'}), 400
    
    result = parse_message(data['message'])
    return jsonify(result)


# ============ SERVE DASHBOARD ============

@app.route('/')
def serve_dashboard():
    """Serve the PWA dashboard (index.html)."""
    return send_from_directory(app.static_folder, 'index.html')


# ============ BACKGROUND SCHEDULER & NOTIFICATIONS ============

from apscheduler.schedulers.background import BackgroundScheduler
from services.notifier import send_push

def scheduled_morning_briefing():
    """Triggered every morning at 7:30 AM."""
    try:
        conn = get_db()
        # Check today's deadlines
        today_str = datetime.now().strftime('%Y-%m-%d')
        deadlines = conn.execute(
            'SELECT title, subject FROM deadlines WHERE completed = 0 AND due_date = ?',
            (today_str,)
        ).fetchall()
        
        # Check attendance warnings
        subjects = conn.execute('SELECT DISTINCT subject FROM attendance').fetchall()
        low_att = []
        for s in subjects:
            subj = s['subject']
            tot = conn.execute("SELECT COUNT(*) as c FROM attendance WHERE subject = ? AND status != 'cancelled'", (subj,)).fetchone()['c']
            pres = conn.execute("SELECT COUNT(*) as c FROM attendance WHERE subject = ? AND status = 'present'", (subj,)).fetchone()['c']
            if tot > 0:
                pct = (pres / tot) * 100
                if pct < 78:
                    low_att.append(f"{subj}: {pct:.1f}%")
        
        conn.close()
        
        msg_parts = []
        if deadlines:
            d_list = ", ".join([f"{d['title']} ({d['subject'] or 'General'})" for d in deadlines])
            msg_parts.append(f"⏰ DUE TODAY: {d_list}")
        else:
            msg_parts.append("✅ No deadlines due today.")
            
        if low_att:
            msg_parts.append(f"⚠️ LOW ATTENDANCE: {', '.join(low_att)}")
            
        send_push(
            title="🌅 Morning Briefing",
            message="\n".join(msg_parts),
            priority="high",
            tags=["sunrise", "memo"]
        )
    except Exception as e:
        print(f"Error running morning briefing: {e}")

def scheduled_evening_checkin():
    """Triggered every evening at 9:00 PM for habits & tomorrow's preview."""
    try:
        conn = get_db()
        # Check uncompleted habits
        habits = conn.execute('SELECT name FROM habits').fetchall()
        uncompleted = []
        for h in habits:
            done = conn.execute("SELECT 1 FROM habit_logs WHERE habit_name = ? AND date = date('now')", (h['name'],)).fetchone()
            if not done:
                uncompleted.append(h['name'])
        
        # Check tomorrow's deadlines
        tomorrow_str = (datetime.now().date() + timedelta(days=1)).strftime('%Y-%m-%d')
        tom_deadlines = conn.execute(
            'SELECT title, subject FROM deadlines WHERE completed = 0 AND due_date = ?',
            (tomorrow_str,)
        ).fetchall()
        conn.close()
        
        msg = []
        if uncompleted:
            msg.append(f"🎯 Pending habits: {', '.join(uncompleted)}")
        if tom_deadlines:
            msg.append(f"📅 Due tomorrow: {', '.join([d['title'] for d in tom_deadlines])}")
            
        if msg:
            send_push(
                title="🌙 Evening Check-in",
                message="\n".join(msg),
                priority="default",
                tags=["moon", "check"]
            )
    except Exception as e:
        print(f"Error in evening checkin: {e}")

def check_pending_reminders():
    """Triggered every minute to fire due reminders as push alerts."""
    try:
        conn = get_db()
        now_str = datetime.now().strftime('%Y-%m-%d %H:%M')
        rows = conn.execute(
            'SELECT * FROM reminders WHERE notified = 0 AND remind_at <= ?',
            (now_str,)
        ).fetchall()
        
        for r in rows:
            cat_emoji = {
                'homework': '📚', 'assignment': '📝', 'gym': '💪',
                'skills': '💻', 'exam': '🎯', 'personal': '🔔'
            }
            emoji = cat_emoji.get(r['category'], '⏰')
            send_push(
                title=f"{emoji} {r['title']}",
                message=f"Reminder ({r['category'].title()}) - {r['remind_at']}",
                priority="high",
                tags=["alarm_clock", "bell"]
            )
            
            if r['repeat'] == 'daily':
                next_dt = datetime.strptime(r['remind_at'], '%Y-%m-%d %H:%M') + timedelta(days=1)
                conn.execute('UPDATE reminders SET remind_at = ? WHERE id = ?', (next_dt.strftime('%Y-%m-%d %H:%M'), r['id']))
            elif r['repeat'] == 'weekly':
                next_dt = datetime.strptime(r['remind_at'], '%Y-%m-%d %H:%M') + timedelta(days=7)
                conn.execute('UPDATE reminders SET remind_at = ? WHERE id = ?', (next_dt.strftime('%Y-%m-%d %H:%M'), r['id']))
            else:
                conn.execute('UPDATE reminders SET notified = 1 WHERE id = ?', (r['id'],))
                
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error checking reminders: {e}")

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

    scheduler.add_job(scheduled_morning_briefing, 'cron', hour=7, minute=30)
    scheduler.add_job(scheduled_evening_checkin, 'cron', hour=21, minute=0)
    scheduler.add_job(check_pending_reminders, 'interval', seconds=10)
    scheduler.start()
    
    print("=" * 50)
    print("🧠 PocketBrain Server Starting...")
    print(f"📱 Dashboard: http://0.0.0.0:5000")
    print(f"📂 Database:  {DB_PATH}")
    print(f"🔔 Notifications: ntfy -> Brain_x1 active")
    print("=" * 50)
    
    app.run(host='0.0.0.0', port=5000, debug=False)
