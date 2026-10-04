import json
import sqlite3
import urllib.request
import urllib.parse
from datetime import datetime
import os

UNSTOP_API = "https://unstop.com/api/public/opportunity/search-new"
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.path.join(BASE_DIR, 'data', 'pocketbrain.db')

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
            opp_type TEXT,
            url TEXT NOT NULL,
            deadline TEXT,
            banner_url TEXT,
            notified INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def scan_unstop(opp_type="hackathons", limit=10):
    """
    Lightweight scan of Unstop public API.
    Does not use heavy browser automation.
    opp_type can be 'hackathons', 'competitions', or 'internships'
    """
    init_radar_table()
    
    payload = {
        "search": "",
        "oppStatus": "open",
        "type": [opp_type],
        "page": 1,
        "size": limit
    }
    
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(
        UNSTOP_API,
        data=data,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
    )
    
    new_items = []
    try:
        with urllib.request.urlopen(req, timeout=12) as response:
            if response.status != 200:
                return []
            res_json = json.loads(response.read().decode('utf-8'))
            items = res_json.get("data", {}).get("data", [])
            
            conn = get_db()
            for item in items:
                source_id = str(item.get("id"))
                opp = item.get("organisation_opportunity", {}) or {}
                title = opp.get("title") or item.get("title") or ""
                org = item.get("organisation", {}) or {}
                organization = org.get("name") or "Various"
                slug = item.get("seo_url") or ""
                url = f"https://unstop.com/{slug}" if slug else "https://unstop.com"
                deadline = item.get("regnRequirements", {}).get("end_regn_dt") or item.get("end_date") or ""
                if deadline and "T" in deadline:
                    deadline = deadline.split("T")[0]
                
                banner_url = opp.get("banner_url") or ""
                
                if not title or not source_id:
                    continue
                    
                # Check if exists
                existing = conn.execute(
                    "SELECT id FROM opportunities WHERE source_id = ?",
                    (source_id,)
                ).fetchone()
                
                if not existing:
                    conn.execute('''
                        INSERT INTO opportunities (source_id, title, organization, opp_type, url, deadline, banner_url)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (source_id, title, organization, opp_type, url, deadline, banner_url))
                    new_items.append({
                        "title": title,
                        "organization": organization,
                        "url": url,
                        "deadline": deadline,
                        "type": opp_type
                    })
            
            conn.commit()
            conn.close()
            
    except Exception as e:
        print(f"⚠️ Unstop scan error: {e}")
        
    return new_items

def get_latest_opportunities(limit=5, opp_type=None):
    """Fetch opportunities from DB for chat or dashboard."""
    init_radar_table()
    conn = get_db()
    if opp_type:
        rows = conn.execute(
            "SELECT * FROM opportunities WHERE opp_type = ? ORDER BY id DESC LIMIT ?",
            (opp_type, limit)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM opportunities ORDER BY id DESC LIMIT ?",
            (limit,)
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def run_opportunity_check_and_notify():
    """Scheduled task: scans Unstop and pushes ntfy notifications for fresh finds."""
    print("📡 [Radar] Scanning Unstop for new hackathons & competitions...")
    new_hacks = scan_unstop("hackathons", limit=8)
    new_comps = scan_unstop("competitions", limit=6)
    
    total_new = new_hacks + new_comps
    if not total_new:
        print("📡 [Radar] No new opportunities found.")
        return
        
    print(f"📡 [Radar] Found {len(total_new)} new opportunities!")
    
    # Notify via ntfy
    try:
        from services.notifier import notify
        for item in total_new[:3]:  # Max 3 notifications to avoid spamming
            title_msg = f"🚀 New {item['type'].capitalize()}: {item['title'][:40]}"
            body_msg = f"Org: {item['organization']}\nDeadline: {item['deadline'] or 'N/A'}\nLink: {item['url']}"
            notify(
                title=title_msg,
                message=body_msg,
                priority=4,
                tags=["trophy", "computer"],
                click_url=item['url']
            )
    except Exception as e:
        print(f"⚠️ Radar notify error: {e}")
