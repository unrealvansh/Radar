"""
PocketBrain — Smart Chat Parser
================================
Understands natural language messages and routes them to the right action.
No LLM needed — uses keyword matching + regex patterns.

How it works:
1. User types a message (e.g., "chai 20")
2. Parser checks against pattern rules (top to bottom)
3. First matching pattern wins → executes the action
4. Returns a friendly response

Supports:
- Expenses:    "chai 20", "spent 50 on xerox", "auto 30"
- Attendance:  "bunked OS", "attended DBMS", "absent CN"
- Habits:      "gym done", "did dsa", "reading done"
- Queries:     "how much spent today", "attendance OS", "kitni attendance"
- Help:        "help", "kya kar sakta hai"
"""

import re
import sqlite3
import os
from datetime import datetime, timedelta

# Database path (same as app.py)
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DB_PATH = os.path.join(BASE_DIR, 'data', 'pocketbrain.db')


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


# ================================================================
# CATEGORY GUESSER — Guesses expense category from description
# ================================================================

CATEGORY_KEYWORDS = {
    'food': [
        'chai', 'tea', 'coffee', 'maggi', 'noodles', 'samosa', 'momos',
        'biryani', 'pizza', 'burger', 'lunch', 'dinner', 'breakfast',
        'snack', 'juice', 'lassi', 'coke', 'pepsi', 'water', 'bottle',
        'canteen', 'mess', 'dhaba', 'restaurant', 'zomato', 'swiggy',
        'biscuit', 'chips', 'chocolate', 'ice cream', 'kulfi', 'pani puri',
        'chowmein', 'paratha', 'dosa', 'idli', 'thali', 'khana', 'nashta',
        'bread', 'milk', 'egg', 'fruit', 'banana', 'apple', 'chole',
        'bhature', 'roll', 'wrap', 'sandwich', 'pav bhaji', 'vada pav',
    ],
    'transport': [
        'auto', 'rickshaw', 'uber', 'ola', 'cab', 'taxi', 'bus',
        'metro', 'train', 'petrol', 'diesel', 'fuel', 'parking',
        'toll', 'rapido', 'bike', 'scooty', 'travel', 'fare',
    ],
    'study': [
        'xerox', 'photocopy', 'print', 'book', 'notebook', 'pen',
        'pencil', 'eraser', 'highlighter', 'marker', 'stationary',
        'stationery', 'course', 'udemy', 'subscription', 'notes',
        'assignment', 'project', 'lab', 'practical',
    ],
    'recharge': [
        'recharge', 'mobile', 'data', 'wifi', 'internet', 'jio',
        'airtel', 'vi', 'bsnl', 'broadband',
    ],
    'health': [
        'medicine', 'medical', 'doctor', 'hospital', 'pharmacy',
        'gym', 'protein', 'supplement', 'haircut', 'salon',
    ],
    'entertainment': [
        'movie', 'netflix', 'prime', 'hotstar', 'spotify', 'game',
        'gaming', 'outing', 'trip', 'picnic',
    ],
}


def guess_category(description):
    """Guess expense category from the description text."""
    desc_lower = description.lower()
    for category, keywords in CATEGORY_KEYWORDS.items():
        for keyword in keywords:
            if keyword in desc_lower:
                return category
    return 'misc'


# ================================================================
# PATTERN MATCHERS — Each function tries to match a user message
# ================================================================

def try_parse_expense(message):
    """
    Matches expense patterns:
      "chai 20"
      "spent 50 on xerox"
      "50 chai"
      "auto 30"
      "20 rupees chai"
      "khana 150"
    """
    msg = message.lower().strip()

    # Pattern 1: "spent <amount> on <description>"
    m = re.match(r'(?:spent|kharch|paid)\s+(\d+)\s+(?:on|for|pe)?\s*(.*)', msg)
    if m:
        amount = float(m.group(1))
        desc = m.group(2).strip() or 'misc'
        return {'amount': amount, 'description': desc, 'category': guess_category(desc)}

    # Pattern 2: "<description> <amount>" (e.g., "chai 20", "auto 30")
    m = re.match(r'([a-z\s]+?)\s+(\d+(?:\.\d+)?)\s*(?:rs|rupees|₹|rupaiye|ka|ki|ke)?$', msg)
    if m:
        desc = m.group(1).strip()
        amount = float(m.group(2))
        # Make sure desc is not just a number or a command word
        if desc and desc not in ['spent', 'paid', 'remind', 'set', 'add']:
            return {'amount': amount, 'description': desc, 'category': guess_category(desc)}

    # Pattern 3: "<amount> <description>" (e.g., "20 chai", "50 xerox")
    m = re.match(r'(\d+(?:\.\d+)?)\s*(?:rs|rupees|₹|rupaiye)?\s+(?:on|for|pe|ka|ki|ke)?\s*(.*)', msg)
    if m:
        amount = float(m.group(1))
        desc = m.group(2).strip()
        if desc and amount > 0:
            return {'amount': amount, 'description': desc, 'category': guess_category(desc)}

    # Pattern 4: Just a number with a food/transport word anywhere
    m = re.match(r'(\d+(?:\.\d+)?)\s*(?:rs|rupees|₹)?$', msg)
    if m:
        return None  # Just a number alone, can't determine what it's for

    return None


def try_parse_attendance(message):
    """
    Matches attendance patterns:
      "bunked OS"
      "attended DBMS"
      "absent in CN"
      "present OS"
      "OS bunked"
      "cancel CN" / "CN cancelled"
    """
    msg = message.lower().strip()

    # Pattern: "<action> <subject>" or "<action> in <subject>"
    m = re.match(
        r'(bunked?|absent|skip(?:ped)?|missed|chutti|nahi gaya|attended|present|gaya|went|cancel(?:led)?|no class)\s+(?:in\s+)?(\w+)',
        msg
    )
    if m:
        action = m.group(1)
        subject = m.group(2).upper()
        if action in ['bunked', 'bunk', 'absent', 'skipped', 'skip', 'missed', 'chutti', 'nahi gaya']:
            return {'subject': subject, 'status': 'absent'}
        elif action in ['attended', 'present', 'gaya', 'went']:
            return {'subject': subject, 'status': 'present'}
        elif action in ['cancelled', 'cancel', 'no class']:
            return {'subject': subject, 'status': 'cancelled'}

    # Pattern: "<subject> <action>" (e.g., "OS bunked", "DBMS attended")
    m = re.match(
        r'(\w+)\s+(bunked?|absent|skip(?:ped)?|attended|present|cancel(?:led)?|no class)',
        msg
    )
    if m:
        subject = m.group(1).upper()
        action = m.group(2)
        if action in ['bunked', 'bunk', 'absent', 'skipped', 'skip']:
            return {'subject': subject, 'status': 'absent'}
        elif action in ['attended', 'present']:
            return {'subject': subject, 'status': 'present'}
        elif action in ['cancelled', 'cancel', 'no class']:
            return {'subject': subject, 'status': 'cancelled'}

    return None


def try_parse_habit(message):
    """
    Matches habit check-in patterns:
      "gym done"
      "did dsa"
      "reading done"
      "completed gym"
      "dsa ✅"
      "dsa ho gaya"
    """
    msg = message.lower().strip()

    # Get list of registered habits from DB
    conn = get_db()
    habits = [r['name'].lower() for r in conn.execute('SELECT name FROM habits').fetchall()]
    conn.close()

    if not habits:
        return None

    # Pattern 1: "<habit> done/✅/hogaya/complete/kar liya"
    m = re.match(r'(\w+)\s+(?:done|✅|hogaya|ho gaya|complete[d]?|kar liya|kar diya|finished|kiya)', msg)
    if m and m.group(1).lower() in habits:
        return {'name': m.group(1).lower()}

    # Pattern 2: "did/completed/done <habit>"
    m = re.match(r'(?:did|done|completed|finished|kiya|kar liya)\s+(\w+)', msg)
    if m and m.group(1).lower() in habits:
        return {'name': m.group(1).lower()}

    # Pattern 3: Just the habit name alone (e.g., user types "gym")
    if msg in habits:
        return {'name': msg}

    return None


def _parse_date_string(date_str):
    date_str = date_str.lower().strip()
    today = datetime.now()
    
    if date_str == 'today' or date_str == 'aaj':
        return today.strftime('%Y-%m-%d')
    elif date_str in ['tomorrow', 'kal']:
        return (today + timedelta(days=1)).strftime('%Y-%m-%d')
    elif date_str in ['day after tomorrow', 'parso', 'parson']:
        return (today + timedelta(days=2)).strftime('%Y-%m-%d')
        
    weekdays = {'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3, 'friday': 4, 'saturday': 5, 'sunday': 6}
    if date_str in weekdays:
        days_ahead = weekdays[date_str] - today.weekday()
        if days_ahead <= 0:
            days_ahead += 7
        return (today + timedelta(days=days_ahead)).strftime('%Y-%m-%d')
            
    m = re.match(r'(\d{1,2})\s+([a-z]+)', date_str) or re.match(r'([a-z]+)\s+(\d{1,2})', date_str)
    if m:
        try:
            if m.group(1).isdigit():
                day = int(m.group(1))
                month_str = m.group(2)[:3]
            else:
                day = int(m.group(2))
                month_str = m.group(1)[:3]
            months = {'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6, 'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12}
            if month_str in months:
                target_date = datetime(today.year, months[month_str], day)
                if target_date.date() < today.date():
                    target_date = datetime(today.year + 1, months[month_str], day)
                return target_date.strftime('%Y-%m-%d')
        except:
            pass

    m = re.match(r'(\d{1,2})[/\-](\d{1,2})', date_str)
    if m:
        try:
            target_date = datetime(today.year, int(m.group(2)), int(m.group(1)))
            if target_date.date() < today.date():
                target_date = datetime(today.year + 1, int(m.group(2)), int(m.group(1)))
            return target_date.strftime('%Y-%m-%d')
        except:
            pass

    return None


def _parse_time_string(time_str):
    """Parse time string like '19:30', '4:40', '4:40 pm' into 'HH:MM' (24-hr)."""
    time_str = time_str.strip().lower()
    m = re.match(r'(\d{1,2}):(\d{2})(?:\s*([ap]m))?', time_str)
    if not m:
        return None
    h = int(m.group(1))
    mins = int(m.group(2))
    ampm = m.group(3)
    
    if ampm == 'pm' and h < 12:
        h += 12
    elif ampm == 'am' and h == 12:
        h = 0
    elif not ampm:
        # If user typed e.g. 4:40 without am/pm, and it's already past 4 AM, assume PM (16:40)
        curr_h = datetime.now().hour
        if h <= 7 and curr_h >= h:
            h += 12
            
    return f"{h:02d}:{mins:02d}"


def try_parse_reminder(message):
    """
    Matches:
      - 'remind me to call mom at 19:30'
      - 'remind me call roshan at 4:40'
      - 'remind me tomorrow at 10:00 to submit assignment'
      - 'remind me in 10 mins to drink water'
      - 'remind me 10 mins before OS assignment'
      - Multiple: 'remind me today at 17:30 and tomorrow at 14:30 to study'
    """
    msg = message.strip()
    msg_lower = msg.lower()
    
    remind_triggers = ['remind', 'reminder', 'remin', 'remider', 'alert', 'alarm', 'yaad']
    if not any(trig in msg_lower for trig in remind_triggers):
        return None
        
    now = datetime.now()
    created_reminders = []
    
    # Pattern 1: "remind me X mins/hours before <task/subject>"
    m_before = re.search(r'remind\s+(?:me\s+)?(\d+)\s*(mins?|minutes?|hours?|hrs?)\s+before\s+(.*)', msg_lower)
    if m_before:
        amount = int(m_before.group(1))
        unit = m_before.group(2)
        target = m_before.group(3).strip()
        delta = timedelta(minutes=amount) if 'min' in unit else timedelta(hours=amount)
        
        # Look for deadline in DB matching target
        conn = get_db()
        deadlines = conn.execute(
            'SELECT * FROM deadlines WHERE completed = 0 ORDER BY due_date ASC'
        ).fetchall()
        
        matched_dl = None
        for dl in deadlines:
            if target in dl['title'].lower() or (dl['subject'] and target in dl['subject'].lower()):
                matched_dl = dl
                break
                
        if matched_dl:
            due_str = f"{matched_dl['due_date']} {matched_dl['due_time'] or '23:59'}"
            try:
                due_dt = datetime.strptime(due_str, '%Y-%m-%d %H:%M')
                remind_dt = due_dt - delta
                remind_str = remind_dt.strftime('%Y-%m-%d %H:%M')
                title = f"{matched_dl['title']} (Due {matched_dl['due_date']})"
                
                conn.execute(
                    'INSERT INTO reminders (title, remind_at, category) VALUES (?, ?, ?)',
                    (title, remind_str, 'assignment')
                )
                conn.commit()
                conn.close()
                return {
                    'action': 'reminder',
                    'response': f"⏰ Reminder set for {remind_str}! ({amount} {unit} before {matched_dl['title']})",
                    'data': [{'title': title, 'remind_at': remind_str}]
                }
            except Exception as e:
                pass
        conn.close()

    # Pattern 2: "remind me in X mins/hours to <task>" or "remind me in X mins <task>"
    m_in = re.search(r'remind\s+(?:me\s+)?in\s+(\d+)\s*(mins?|minutes?|hours?|hrs?)(?:\s+(?:to\s+|for\s+)?(.*))?$', msg_lower)
    if m_in:
        amount = int(m_in.group(1))
        unit = m_in.group(2)
        title = m_in.group(3) or 'Quick Reminder'
        delta = timedelta(minutes=amount) if 'min' in unit else timedelta(hours=amount)
        remind_dt = now + delta
        remind_str = remind_dt.strftime('%Y-%m-%d %H:%M')
        
        conn = get_db()
        conn.execute(
            'INSERT INTO reminders (title, remind_at, category) VALUES (?, ?, ?)',
            (title.strip(), remind_str, 'personal')
        )
        conn.commit()
        conn.close()
        return {
            'action': 'reminder',
            'response': f"⏰ Reminder set for {remind_str} ({amount} {unit} from now): '{title.strip()}'",
            'data': [{'title': title, 'remind_at': remind_str}]
        }

    # Pattern 3: Standard or Multiple Reminders:
    # Check if there is an "and" connecting multiple times, e.g.:
    # "remind me today at 5:30 and tomorrow at 2:30 to do assignment"
    # Or single: "remind me to call mom at 19:30"
    
    # Find all times mentioned in message: e.g. "at 19:30" or "at 4:40 pm"
    time_matches = list(re.finditer(r'(?:on\s+([a-zA-Z0-9\s/\-]+?)\s+)?at\s+(\d{1,2}:\d{2}(?:\s*[ap]m)?)', msg_lower))
    if time_matches:
        clean_title = re.sub(r'^(?:remind|reminder|remin|remider|alert|alarm)\s+(?:me\s+)?(?:to\s+)?', '', msg, flags=re.IGNORECASE)
        for tm in time_matches:
            clean_title = clean_title.replace(tm.group(0), '')
        clean_title = re.sub(r'\s+and\s+', ' ', clean_title).strip()
        if not clean_title:
            clean_title = 'Reminder'
            
        conn = get_db()
        results = []
        for tm in time_matches:
            date_part = tm.group(1)
            time_part = tm.group(2)
            
            parsed_time = _parse_time_string(time_part)
            if not parsed_time:
                continue
                
            if date_part:
                parsed_date = _parse_date_string(date_part) or now.strftime('%Y-%m-%d')
            else:
                # If time is earlier than current time today, default to tomorrow
                if parsed_time < now.strftime('%H:%M'):
                    parsed_date = (now + timedelta(days=1)).strftime('%Y-%m-%d')
                else:
                    parsed_date = now.strftime('%Y-%m-%d')
                    
            remind_str = f"{parsed_date} {parsed_time}"
            conn.execute(
                'INSERT INTO reminders (title, remind_at, category) VALUES (?, ?, ?)',
                (clean_title, remind_str, 'personal')
            )
            results.append(remind_str)
            
        conn.commit()
        conn.close()
        
        if results:
            dates_formatted = ", ".join(results)
            return {
                'action': 'reminder',
                'response': f"⏰ {len(results)} Reminder(s) set for '{clean_title}': {dates_formatted}",
                'data': [{'title': clean_title, 'remind_at': r} for r in results]
            }

    return None

def try_parse_deadline(message):
    msg = message.lower().strip()
    
    if not any(kw in msg for kw in ['submit', 'exam', 'deadline', 'viva', 'reminder', 'project', 'assignment']):
        return None

    date_pattern = r'(.*?)\s+(?:by|on|before)?\s*(tomorrow|day after tomorrow|parso|monday|tuesday|wednesday|thursday|friday|saturday|sunday|\d{1,2}\s+[a-z]+|[a-z]+\s+\d{1,2}|\d{1,2}[/\-]\d{1,2})$'
    m = re.search(date_pattern, msg)
    if m:
        rest = m.group(1).strip()
        date_str = m.group(2).strip()
        due_date = _parse_date_string(date_str)
        if not due_date:
            return None
            
        orig_rest = message[:m.start(2)].strip()
        orig_rest = re.sub(r'\s+(by|on|before)$', '', orig_rest, flags=re.IGNORECASE).strip()
        
        if orig_rest.lower().startswith('reminder '):
            orig_rest = orig_rest[9:]
        if orig_rest.lower().startswith('deadline '):
            orig_rest = orig_rest[9:]
            
        subject = ''
        title_words = []
        words = orig_rest.split()
        for w in words:
            if w.isupper() and 2 <= len(w) <= 4:
                subject = w
            else:
                if w.lower() != 'submit':
                    title_words.append(w)
                    
        if not subject:
            for i, w in enumerate(title_words):
                if w.lower() in ['os', 'dbms', 'cn', 'toc', 'coa', 'se', 'math']:
                    subject = w.upper()
                    title_words.pop(i)
                    break

        if 'submit' in orig_rest.lower() and not subject and 'assignment' in orig_rest.lower():
            title = 'submit assignment'
        else:
            title = ' '.join(title_words)
            
        if not title:
            title = orig_rest
            
        return {'title': title.strip(), 'subject': subject, 'due_date': due_date}
    return None

def try_parse_note(message):
    msg = message.strip()
    m = re.match(r'^(?:save|note|remember)(?:\:)?\s+(.*)', msg, flags=re.IGNORECASE)
    if m:
        content = m.group(1).strip()
        if content:
            return {'content': content}
    return None

def try_parse_budget(message):
    msg = message.lower().strip()
    m = re.match(r'^(?:set\s+)?budget\s+(\d+)(?:\s+per\s+week)?$', msg)
    if m:
        return {'budget': int(m.group(1))}
    return None


def try_parse_query(message):
    """
    Matches query patterns:
      "how much spent today"
      "aaj kitna kharch"
      "attendance OS"
      "total spending"
      "kitni attendance"
      "habits"
      "status"
    """
    msg = message.lower().strip()

    # Spending queries
    if any(word in msg for word in ['spent', 'spending', 'kharch', 'kitna', 'total', 'paisa']):
        conn = get_db()
        if 'month' in msg or 'mahine' in msg:
            row = conn.execute(
                "SELECT COALESCE(SUM(amount), 0) as total FROM expenses "
                "WHERE strftime('%Y-%m', date) = strftime('%Y-%m', 'now')"
            ).fetchone()
            conn.close()
            return {'type': 'spending', 'message': f"💸 This month: ₹{row['total']}"}
        else:
            row = conn.execute(
                "SELECT COALESCE(SUM(amount), 0) as total FROM expenses WHERE date = date('now')"
            ).fetchone()
            conn.close()
            return {'type': 'spending', 'message': f"💸 Today: ₹{row['total']}"}

    # Attendance query for specific subject
    m = re.match(r'(?:attendance|attend)\s+(\w+)', msg)
    if m:
        subject = m.group(1).upper()
        conn = get_db()
        total = conn.execute(
            "SELECT COUNT(*) as c FROM attendance WHERE subject = ? AND status != 'cancelled'",
            (subject,)
        ).fetchone()['c']
        present = conn.execute(
            "SELECT COUNT(*) as c FROM attendance WHERE subject = ? AND status = 'present'",
            (subject,)
        ).fetchone()['c']
        conn.close()
        if total == 0:
            return {'type': 'attendance', 'message': f"📊 No attendance records for {subject}"}
        pct = round(present / total * 100, 1)
        safe = 0
        t, p = total, present
        while (p / (t + 1)) * 100 >= 75:
            t += 1
            safe += 1
        bunk_msg = f"🟢 Can bunk {safe} more" if safe > 0 else "🔴 Cannot bunk!"
        return {'type': 'attendance', 'message': f"📊 {subject}: {present}/{total} = {pct}% | {bunk_msg}"}

    # General attendance query
    if 'attendance' in msg or 'attend' in msg or 'kitni' in msg:
        conn = get_db()
        subjects = conn.execute('SELECT DISTINCT subject FROM attendance').fetchall()
        if not subjects:
            conn.close()
            return {'type': 'attendance', 'message': "📊 No attendance logged yet."}
        lines = []
        for s in subjects:
            subj = s['subject']
            total = conn.execute(
                "SELECT COUNT(*) as c FROM attendance WHERE subject = ? AND status != 'cancelled'",
                (subj,)
            ).fetchone()['c']
            present = conn.execute(
                "SELECT COUNT(*) as c FROM attendance WHERE subject = ? AND status = 'present'",
                (subj,)
            ).fetchone()['c']
            pct = round(present / total * 100, 1) if total > 0 else 0
            emoji = "🟢" if pct >= 78 else "🔴"
            lines.append(f"{emoji} {subj}: {pct}%")
        conn.close()
        return {'type': 'attendance', 'message': "📊 Attendance:\n" + "\n".join(lines)}

    # Habit status query
    if any(word in msg for word in ['habits', 'habit', 'streak', 'status']):
        conn = get_db()
        habits = conn.execute('SELECT * FROM habits').fetchall()
        if not habits:
            conn.close()
            return {'type': 'habits', 'message': "🎯 No habits tracked yet."}
        lines = []
        for h in habits:
            log = conn.execute(
                "SELECT * FROM habit_logs WHERE habit_name = ? AND date = date('now')",
                (h['name'],)
            ).fetchone()
            status = "✅" if log else "❌"
            lines.append(f"{h['icon']} {h['name']}: {status}")
        conn.close()
        return {'type': 'habits', 'message': "🎯 Today's Habits:\n" + "\n".join(lines)}

    # Deadline queries
    if msg in ['deadlines', 'upcoming', 'kya pending hai']:
        conn = get_db()
        deadlines = conn.execute(
            "SELECT * FROM deadlines WHERE due_date >= date('now') ORDER BY due_date ASC LIMIT 5"
        ).fetchall()
        conn.close()
        if not deadlines:
            return {'type': 'deadlines', 'message': "📅 No upcoming deadlines! Chill piyo. ☕"}
        lines = ["📅 Upcoming Deadlines:"]
        for d in deadlines:
            subj = f"[{d['subject']}] " if d['subject'] else ""
            # Format date friendly
            try:
                date_obj = datetime.strptime(d['due_date'], '%Y-%m-%d')
                date_str = date_obj.strftime('%b %d')
                days_left = (date_obj.date() - datetime.now().date()).days
                if days_left == 0:
                    date_str = "Today!"
                elif days_left == 1:
                    date_str = "Tomorrow!"
                else:
                    date_str += f" ({days_left} days)"
            except:
                date_str = d['due_date']
            lines.append(f"• {subj}{d['title']} → {date_str}")
        return {'type': 'deadlines', 'message': "\n".join(lines)}

    # Note queries
    if msg in ['saved', 'notes', 'my notes']:
        conn = get_db()
        notes = conn.execute(
            "SELECT * FROM notes ORDER BY created_at DESC LIMIT 5"
        ).fetchall()
        conn.close()
        if not notes:
            return {'type': 'notes', 'message': "📌 No saved notes."}
        lines = ["📌 Recent Notes:"]
        for n in notes:
            lines.append(f"• {n['content']}")
        return {'type': 'notes', 'message': "\n".join(lines)}

    # Opportunity queries (hackathons / competitions)
    if any(k in msg for k in ['hackathon', 'hackathons', 'competition', 'competitions', 'events', 'radar']):
        try:
            from services.opportunity_radar import get_latest_opportunities, scan_unstop
            items = get_latest_opportunities(limit=5)
            if not items:
                # First time fetch
                scan_unstop('hackathons', limit=5)
                items = get_latest_opportunities(limit=5)
                
            if not items:
                return {'type': 'opportunities', 'message': "📡 No hackathons found right now. Check back soon!"}
                
            lines = ["🚀 Upcoming Hackathons & Events:"]
            for it in items:
                dd = f" (Deadline: {it['deadline']})" if it.get('deadline') else ""
                lines.append(f"• {it['title']} by {it['organization']}{dd}\n  🔗 {it['url']}")
            return {'type': 'opportunities', 'message': "\n".join(lines)}
        except Exception as e:
            return {'type': 'opportunities', 'message': f"⚠️ Error fetching opportunities: {e}"}

    # Budget query
    if msg == 'budget':
        conn = get_db()
        row = conn.execute("SELECT value FROM settings WHERE key = 'weekly_budget'").fetchone()
        if not row:
            conn.close()
            return {'type': 'budget', 'message': "💰 No weekly budget set. Type 'budget 2000' to set one."}
        budget = float(row['value'])
        
        # calculate week's spending
        spent = conn.execute(
            "SELECT COALESCE(SUM(amount), 0) as total FROM expenses WHERE strftime('%Y-%W', date) = strftime('%Y-%W', 'now')"
        ).fetchone()['total']
        conn.close()
        return {'type': 'budget', 'message': f"💰 Weekly Budget: ₹{budget}\nSpent so far: ₹{spent}\nRemaining: ₹{budget - spent}"}

    return None


# ================================================================
# HELP RESPONSE
# ================================================================

HELP_TEXT = """🧠 **PocketBrain Chat Commands**

💸 **Expenses:**
• `chai 20` — logs ₹20 expense (food)
• `auto 30` — logs ₹30 expense (transport)
• `spent 50 on xerox` — logs ₹50 (study)

📊 **Attendance:**
• `bunked OS` — marks OS as absent
• `attended DBMS` — marks DBMS as present
• `cancel CN` — marks CN as cancelled

🎯 **Habits:**
• `gym done` — checks in gym habit
• `did dsa` — checks in DSA habit
• Just type the habit name: `gym`

❓ **Queries:**
• `how much spent today`
• `attendance OS`
• `habits` — today's habit status
• `status` — overall summary

💡 Hinglish bhi chalega: `bunked OS`, `chai 20`, `gym ho gaya`"""


# ================================================================
# MAIN PARSER — The brain that routes messages
# ================================================================

def parse_message(message):
    """
    Parse a user message and return an action + response.
    
    Returns a dict with:
      - 'action': what was done ('expense', 'attendance', 'habit', 'query', 'help', 'unknown')
      - 'response': friendly text response to show the user
      - 'data': parsed data (if applicable)
    """
    msg = message.strip()
    if not msg:
        return {'action': 'unknown', 'response': "Kuch toh likh! 😄 Type `help` for commands."}

    msg_lower = msg.lower()

    # --- Help ---
    if msg_lower in ['help', 'h', '?', 'commands', 'kya kar sakta hai', 'kya kya kar sakta hai']:
        return {'action': 'help', 'response': HELP_TEXT}

    # --- Try Custom Reminder (Exact time, multiple, or before deadline) ---
    reminder = try_parse_reminder(msg)
    if reminder:
        return reminder

    # --- Try Deadline ---
    deadline = try_parse_deadline(msg)
    if deadline:
        conn = get_db()
        conn.execute(
            'INSERT INTO deadlines (title, subject, due_date) VALUES (?, ?, ?)',
            (deadline['title'], deadline['subject'], deadline['due_date'])
        )
        conn.commit()
        conn.close()
        
        target_date = datetime.strptime(deadline['due_date'], '%Y-%m-%d')
        days_left = (target_date.date() - datetime.now().date()).days
        days_str = f" ({days_left} days left)" if days_left > 1 else " (Tomorrow!)" if days_left == 1 else " (Today!)" if days_left == 0 else " (Overdue!)"
        subj_str = f"{deadline['subject']} " if deadline['subject'] else ""
        
        # Trigger phone push notification!
        try:
            from services.notifier import send_push
            send_push(
                title=f"📅 New Deadline: {subj_str}{deadline['title']}",
                message=f"Due on {target_date.strftime('%b %d')}{days_str}",
                priority="high",
                tags=["calendar", "alarm_clock"]
            )
        except Exception:
            pass
        
        return {
            'action': 'deadline',
            'response': f"📅 Deadline set! '{subj_str}{deadline['title']}' → {target_date.strftime('%b %d')}{days_str}",
            'data': deadline
        }

    # --- Try Note ---
    note = try_parse_note(msg)
    if note:
        conn = get_db()
        conn.execute(
            'INSERT INTO notes (content) VALUES (?)',
            (note['content'],)
        )
        conn.commit()
        conn.close()
        return {
            'action': 'note',
            'response': f"📌 Saved! '{note['content']}'",
            'data': note
        }

    # --- Try Budget ---
    budget = try_parse_budget(msg_lower)
    if budget:
        conn = get_db()
        conn.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES ('weekly_budget', ?)",
            (str(budget['budget']),)
        )
        conn.commit()
        conn.close()
        return {
            'action': 'budget',
            'response': f"💰 Weekly budget set to ₹{budget['budget']}!",
            'data': budget
        }

    # --- Try Attendance (check before expense, because "bunked" is more specific) ---
    att = try_parse_attendance(msg)
    if att:
        conn = get_db()
        conn.execute(
            'INSERT INTO attendance (subject, status) VALUES (?, ?)',
            (att['subject'], att['status'])
        )
        conn.commit()

        # Get updated stats
        total = conn.execute(
            "SELECT COUNT(*) as c FROM attendance WHERE subject = ? AND status != 'cancelled'",
            (att['subject'],)
        ).fetchone()['c']
        present = conn.execute(
            "SELECT COUNT(*) as c FROM attendance WHERE subject = ? AND status = 'present'",
            (att['subject'],)
        ).fetchone()['c']
        conn.close()
        pct = round(present / total * 100, 1) if total > 0 else 0

        status_emoji = {'present': '✅', 'absent': '❌', 'cancelled': '🚫'}
        emoji = status_emoji.get(att['status'], '📊')
        
        return {
            'action': 'attendance',
            'response': f"{emoji} {att['subject']} → {att['status']}\n📊 Now: {present}/{total} = {pct}%",
            'data': att
        }

    # --- Try Habit ---
    habit = try_parse_habit(msg)
    if habit:
        conn = get_db()
        try:
            conn.execute(
                'INSERT INTO habit_logs (habit_name) VALUES (?)',
                (habit['name'],)
            )
            conn.commit()
            response = f"🎯 {habit['name']} ✅ Done for today!"
        except sqlite3.IntegrityError:
            response = f"🎯 {habit['name']} — already checked in today! 💪"
        conn.close()
        return {'action': 'habit', 'response': response, 'data': habit}

    # --- Try Query ---
    query = try_parse_query(msg)
    if query:
        return {'action': 'query', 'response': query['message']}

    # --- Try Expense (last, because it's the most flexible pattern) ---
    expense = try_parse_expense(msg)
    if expense:
        conn = get_db()
        conn.execute(
            'INSERT INTO expenses (amount, description, category) VALUES (?, ?, ?)',
            (expense['amount'], expense['description'], expense['category'])
        )
        conn.commit()

        # Get today's total
        today = conn.execute(
            "SELECT COALESCE(SUM(amount), 0) as total FROM expenses WHERE date = date('now')"
        ).fetchone()['total']
        conn.close()

        cat_emoji = {
            'food': '🍕', 'transport': '🚌', 'study': '📚',
            'recharge': '📱', 'health': '💊', 'entertainment': '🎬', 'misc': '📦'
        }
        emoji = cat_emoji.get(expense['category'], '📦')

        return {
            'action': 'expense',
            'response': f"{emoji} ₹{expense['amount']} logged → {expense['description']} ({expense['category']})\n💸 Today's total: ₹{today}",
            'data': expense
        }

    # --- Try SmolLM2 360M Fallback (if smart parser didn't match) ---
    try:
        from services.llm_parser import llm_parse
        llm_action = llm_parse(msg)
        if llm_action and isinstance(llm_action, dict):
            act = llm_action.get('action')
            
            if act == 'expense' and 'amount' in llm_action:
                conn = get_db()
                amt = float(llm_action['amount'])
                desc = llm_action.get('description', 'Expense')
                cat = llm_action.get('category', 'misc')
                conn.execute('INSERT INTO expenses (amount, description, category) VALUES (?, ?, ?)', (amt, desc, cat))
                conn.commit()
                conn.close()
                return {'action': 'expense', 'response': f"🤖 (AI) Logged ₹{amt} for {desc} ({cat})", 'data': llm_action}
                
            elif act == 'reminder' and 'title' in llm_action:
                remind_at = f"{llm_action.get('date', datetime.now().strftime('%Y-%m-%d'))} {llm_action.get('time', '09:00')}"
                conn = get_db()
                conn.execute('INSERT INTO reminders (title, remind_at, category) VALUES (?, ?, ?)', (llm_action['title'], remind_at, 'personal'))
                conn.commit()
                conn.close()
                return {'action': 'reminder', 'response': f"🤖 (AI) ⏰ Reminder scheduled for {remind_at}: '{llm_action['title']}'", 'data': llm_action}

            elif act == 'deadline' and 'title' in llm_action:
                due_date = llm_action.get('due_date', datetime.now().strftime('%Y-%m-%d'))
                subj = llm_action.get('subject', '')
                conn = get_db()
                conn.execute('INSERT INTO deadlines (title, subject, due_date) VALUES (?, ?, ?)', (llm_action['title'], subj, due_date))
                conn.commit()
                conn.close()
                return {'action': 'deadline', 'response': f"🤖 (AI) 📅 Deadline saved: '{llm_action['title']}' due {due_date}", 'data': llm_action}

            elif act == 'note' and 'content' in llm_action:
                conn = get_db()
                conn.execute('INSERT INTO notes (content) VALUES (?)', (llm_action['content'],))
                conn.commit()
                conn.close()
                return {'action': 'note', 'response': f"🤖 (AI) 📌 Saved: '{llm_action['content']}'", 'data': llm_action}

            elif act == 'habit' and 'name' in llm_action:
                conn = get_db()
                try:
                    conn.execute('INSERT INTO habit_logs (habit_name) VALUES (?)', (llm_action['name'],))
                    conn.commit()
                except Exception:
                    pass
                conn.close()
                return {'action': 'habit', 'response': f"🤖 (AI) 🎯 Habit marked: {llm_action['name']}", 'data': llm_action}
    except Exception as e:
        print(f"LLM fallback error: {e}")

    # --- Unknown ---
    return {
        'action': 'unknown',
        'response': f"🤔 Samajh nahi aaya: \"{msg}\"\nType `help` to see what I can understand!"
    }
