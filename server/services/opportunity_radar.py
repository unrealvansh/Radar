import json
import sqlite3
import urllib.request
import urllib.parse
from datetime import datetime
import os
import re

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.path.join(BASE_DIR, 'data', 'pocketbrain.db')
DEVPOST_API = "https://devpost.com/api/hackathons?challenge_type[]=online&status[]=open"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn

def init_radar_table():
    """Ensure opportunities table exists."""
    conn = get_db()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS opportunities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_id TEXT UNIQUE,
            title TEXT NOT NULL,
            organization TEXT,
            opp_type TEXT DEFAULT 'hackathon',
            url TEXT NOT NULL,
            deadline TEXT,
            banner_url TEXT,
            prize TEXT,
            notified INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def scan_hackathons(limit=10):
    """
    Lightweight, fast scan of active online hackathons via Devpost public API.
    Zero heavy dependencies, 100% reliable without bot protection.
    """
    init_radar_table()
    
    req = urllib.request.Request(
        DEVPOST_API,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json"
        }
    )
    
    new_items = []
    try:
        with urllib.request.urlopen(req, timeout=12) as response:
            if response.status != 200:
                return []
            res_json = json.loads(response.read().decode('utf-8'))
            items = res_json.get("hackathons", [])
            
            conn = get_db()
            for item in items[:limit]:
                source_id = str(item.get("id"))
                title = item.get("title", "").strip()
                url = item.get("url", "")
                if not title or not source_id or not url:
                    continue
                    
                # Clean prize HTML if present
                raw_prize = item.get("prize_amount", "")
                prize = re.sub(r'<[^>]+>', '', raw_prize).strip() if raw_prize else "N/A"
                
                # Organization / Host
                org = item.get("organization_name") or item.get("displayed_location", {}).get("location") or "Online"
                
                # Deadline / Dates
                deadline = item.get("submission_period_dates") or ""
                
                banner_url = item.get("thumbnail_url") or ""
                
                existing = conn.execute(
                    "SELECT id FROM opportunities WHERE source_id = ?",
                    (source_id,)
                ).fetchone()
                
                if not existing:
                    conn.execute('''
                        INSERT INTO opportunities (source_id, title, organization, opp_type, url, deadline, banner_url, prize)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (source_id, title, org, 'hackathon', url, deadline, banner_url, prize))
                    new_items.append({
                        "title": title,
                        "organization": org,
                        "url": url,
                        "deadline": deadline,
                        "prize": prize,
                        "type": "hackathon"
                    })
            
            conn.commit()
            conn.close()
            
    except Exception as e:
        print(f"⚠️ Hackathon scan error: {e}")
        
    return new_items

def get_latest_opportunities(limit=5):
    """Fetch stored opportunities from DB."""
    init_radar_table()
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM opportunities ORDER BY id DESC LIMIT ?",
        (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def run_opportunity_check_and_notify():
    """Scheduled task: scans for fresh hackathons and pushes ntfy notifications."""
    print("📡 [Radar] Scanning for new hackathons...")
    new_hacks = scan_hackathons(limit=10)
    
    if not new_hacks:
        print("📡 [Radar] No new hackathons found.")
        return
        
    print(f"📡 [Radar] Found {len(new_hacks)} new hackathons!")
    
    # Notify via ntfy
    try:
        from services.notifier import notify
        for item in new_hacks[:2]:  # Send max 2 to prevent spam
            title_msg = f"🏆 Hackathon: {item['title'][:40]}"
            body_msg = f"Prize: {item.get('prize', 'N/A')}\nDates: {item['deadline']}\nLink: {item['url']}"
            notify(
                title=title_msg,
                message=body_msg,
                priority=4,
                tags=["trophy", "fire"],
                click_url=item['url']
            )
    except Exception as e:
        print(f"⚠️ Radar notify error: {e}")
