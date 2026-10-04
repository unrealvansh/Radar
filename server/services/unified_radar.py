import os
import re
import json
import sqlite3
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.path.join(BASE_DIR, 'data', 'pocketbrain.db')

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn

def init_radar_db():
    """Ensure radar_items table exists."""
    conn = get_db()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS radar_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pillar TEXT NOT NULL,         -- 'jobs', 'events', 'news'
            source TEXT NOT NULL,         -- 'Devpost', 'TechCrunch', 'YourStory', 'Remotive', etc.
            title TEXT NOT NULL,
            organization TEXT,            -- Company or Organizer
            url TEXT NOT NULL UNIQUE,
            deadline_or_date TEXT,
            extra_info TEXT,              -- Stipend, Prize, Tags, or Summary
            notified INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def _fetch_rss(url, timeout=10):
    """Safely fetch and parse an RSS feed."""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            if response.status == 200:
                xml_data = response.read()
                return ET.fromstring(xml_data)
    except Exception as e:
        print(f"⚠️ RSS fetch error ({url}): {e}")
    return None

def _fetch_json(url, timeout=10):
    """Safely fetch and parse a JSON endpoint."""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            if response.status == 200:
                return json.loads(response.read().decode('utf-8'))
    except Exception as e:
        print(f"⚠️ JSON fetch error ({url}): {e}")
    return None

# =====================================================================
# 1. 💼 JOBS & INTERNSHIPS
# =====================================================================

def scan_jobs(limit=10):
    """Scan software & student internships and early-career tech jobs."""
    init_radar_db()
    new_items = []
    conn = get_db()

    # Source: Remotive (Software & Dev Intern/Junior roles)
    try:
        url = "https://remotive.com/api/remote-jobs?category=software-dev&limit=15"
        data = _fetch_json(url)
        if data and "jobs" in data:
            for job in data["jobs"]:
                title = job.get("title", "").strip()
                company = job.get("company_name", "Tech Startup")
                job_url = job.get("url", "")
                salary = job.get("salary", "") or "Competitive"
                published = job.get("publication_date", "")[:10]

                if not title or not job_url:
                    continue

                try:
                    conn.execute('''
                        INSERT INTO radar_items (pillar, source, title, organization, url, deadline_or_date, extra_info)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', ('jobs', 'Remotive', title, company, job_url, published, f"💼 {salary}"))
                    new_items.append({'pillar': 'jobs', 'title': title, 'org': company, 'url': job_url})
                except sqlite3.IntegrityError:
                    pass
    except Exception as e:
        print(f"⚠️ Jobs scan error: {e}")

    conn.commit()
    conn.close()
    return new_items

# =====================================================================
# 2. 🚀 TECH EVENTS & HACKATHONS
# =====================================================================

def scan_events(limit=10):
    """Scan active hackathons, GDG events, and AI summits."""
    init_radar_db()
    new_items = []
    conn = get_db()

    # Source: Devpost Online Hackathons
    try:
        url = "https://devpost.com/api/hackathons?challenge_type[]=online&status[]=open"
        data = _fetch_json(url)
        if data and "hackathons" in data:
            for item in data["hackathons"][:limit]:
                title = item.get("title", "").strip()
                event_url = item.get("url", "")
                raw_prize = item.get("prize_amount", "")
                prize = re.sub(r'<[^>]+>', '', raw_prize).strip() if raw_prize else "Certificates/Swag"
                dates = item.get("submission_period_dates", "")
                org = item.get("organization_name") or "Global Devs"

                if not title or not event_url:
                    continue

                try:
                    conn.execute('''
                        INSERT INTO radar_items (pillar, source, title, organization, url, deadline_or_date, extra_info)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', ('events', 'Devpost', title, org, event_url, dates, f"💰 {prize}"))
                    new_items.append({'pillar': 'events', 'title': title, 'org': org, 'url': event_url})
                except sqlite3.IntegrityError:
                    pass
    except Exception as e:
        print(f"⚠️ Events Devpost scan error: {e}")

    conn.commit()
    conn.close()
    return new_items

# =====================================================================
# 3. 📰 TECH NEWS & PRODUCT UPDATES
# =====================================================================

NEWS_FEEDS = [
    ("TechCrunch", "https://techcrunch.com/feed/", "Global Tech & AI"),
    ("YourStory", "https://yourstory.com/feed", "Indian Startups & Tech"),
    ("Inc42", "https://inc42.com/feed/", "Indian Startup Ecosystem"),
    ("Google Developers", "https://blog.google/technology/developers/rss/", "Developer & AI Tools"),
]

def scan_news(limit_per_feed=3):
    """Scan latest breaking tech news, AI models, and startup announcements."""
    init_radar_db()
    new_items = []
    conn = get_db()

    for source_name, feed_url, category_tag in NEWS_FEEDS:
        try:
            root = _fetch_rss(feed_url)
            if root is None:
                continue

            items = root.findall('.//item')
            for item in items[:limit_per_feed]:
                title_elem = item.find('title')
                link_elem = item.find('link')
                pub_elem = item.find('pubDate')

                title = title_elem.text.strip() if title_elem is not None and title_elem.text else ""
                url = link_elem.text.strip() if link_elem is not None and link_elem.text else ""
                pub_date = pub_elem.text[:16] if pub_elem is not None and pub_elem.text else ""

                if not title or not url:
                    continue

                try:
                    conn.execute('''
                        INSERT INTO radar_items (pillar, source, title, organization, url, deadline_or_date, extra_info)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', ('news', source_name, title, category_tag, url, pub_date, f"📰 {source_name}"))
                    new_items.append({'pillar': 'news', 'title': title, 'org': source_name, 'url': url})
                except sqlite3.IntegrityError:
                    pass
        except Exception as e:
            print(f"⚠️ News scan error ({source_name}): {e}")

    conn.commit()
    conn.close()
    return new_items

# =====================================================================
# UNIFIED SCAN & QUERIES
# =====================================================================

def scan_all_radar():
    """Scan all 3 pillars and push priority notifications."""
    print("📡 [Radar] Starting full scan (Jobs, Events, Tech News)...")
    j = scan_jobs(limit=10)
    e = scan_events(limit=10)
    n = scan_news(limit_per_feed=2)
    
    total = len(j) + len(e) + len(n)
    print(f"📡 [Radar] Scan complete. Added {total} new items! (Jobs: {len(j)}, Events: {len(e)}, News: {len(n)})")

    # Send up to 2 high-priority push notifications
    if e or j:
        try:
            from services.notifier import notify
            if e:
                top_event = e[0]
                notify(
                    title=f"🚀 Hackathon/Event: {top_event['title'][:40]}",
                    message=f"By: {top_event['org']}\nTap to check details.",
                    priority=4,
                    tags=["trophy", "computer"],
                    click_url=top_event['url']
                )
            if j:
                top_job = j[0]
                notify(
                    title=f"💼 Job Alert: {top_job['title'][:40]}",
                    message=f"Company: {top_job['org']}\nTap to view role.",
                    priority=3,
                    tags=["briefcase"],
                    click_url=top_job['url']
                )
        except Exception as ex:
            print(f"⚠️ Radar notify error: {ex}")

    return {'jobs': len(j), 'events': len(e), 'news': len(n)}

def get_radar_items(pillar=None, limit=5):
    """Retrieve items from DB for chat or frontend."""
    init_radar_db()
    conn = get_db()
    if pillar:
        rows = conn.execute(
            "SELECT * FROM radar_items WHERE pillar = ? ORDER BY id DESC LIMIT ?",
            (pillar, limit)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM radar_items ORDER BY id DESC LIMIT ?",
            (limit,)
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
