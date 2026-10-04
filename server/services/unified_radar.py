import os
import re
import json
import sqlite3
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.path.join(BASE_DIR, 'data', 'pocketbrain.db')

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"

# User's Customized Keywords
INTERN_KEYWORDS = [
    'intern', 'internship', 'trainee', 'c++', 'python', 'fintech', 'quant', 
    'trading', 'backend', 'full stack', 'fullstack', 'react', 'node', 
    'cloud', 'devops', 'cybersecurity', 'security', 'software'
]

TARGET_LOCATIONS = ['remote', 'wfh', 'delhi', 'noida', 'gurgaon', 'gurugram', 'anywhere', 'india']

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
            source TEXT NOT NULL,         -- 'LinkedIn', 'Remotive', 'Devpost', 'Devfolio', 'YourStory', etc.
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

def _fetch_json(url, headers=None, timeout=10):
    """Safely fetch and parse a JSON endpoint."""
    h = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            if response.status == 200:
                return json.loads(response.read().decode('utf-8'))
    except Exception as e:
        print(f"⚠️ JSON fetch error ({url}): {e}")
    return None

# =====================================================================
# 1. 💼 JOBS & INTERNSHIPS (C++, Python, Fintech, Backend, DevOps, WFH/Delhi)
# =====================================================================

def scan_jobs(limit=10):
    """Scan software & student internships, fintech, C++, Python, and early career roles."""
    init_radar_db()
    new_items = []
    conn = get_db()

    # Source A: Remotive (Python, Software Dev, Data)
    for cat in ['software-dev', 'data', 'devops-sysadmin']:
        try:
            url = f"https://remotive.com/api/remote-jobs?category={cat}&limit=10"
            data = _fetch_json(url)
            if data and "jobs" in data:
                for job in data["jobs"]:
                    title = job.get("title", "").strip()
                    desc = (job.get("description") or "").lower()
                    title_lower = title.lower()
                    
                    # Match user's customized keywords (Fintech, C++, Python, Backend, etc.)
                    is_match = any(kw in title_lower or kw in desc for kw in INTERN_KEYWORDS)
                    if not is_match:
                        continue

                    company = job.get("company_name", "Tech Startup")
                    job_url = job.get("url", "")
                    salary = job.get("salary", "") or "Competitive"
                    published = job.get("publication_date", "")[:10]

                    if not title or not job_url:
                        continue

                    tag = "💼 Remote / WFH"
                    if "fintech" in title_lower or "fintech" in desc:
                        tag = "💎 Fintech Role"
                    elif "c++" in title_lower or "c++" in desc:
                        tag = "⚡ C++ Role"
                    elif "python" in title_lower:
                        tag = "🐍 Python Role"

                    try:
                        conn.execute('''
                            INSERT INTO radar_items (pillar, source, title, organization, url, deadline_or_date, extra_info)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        ''', ('jobs', 'Remotive', title, company, job_url, published, f"{tag} • {salary}"))
                        new_items.append({'pillar': 'jobs', 'title': title, 'org': company, 'url': job_url})
                    except sqlite3.IntegrityError:
                        pass
        except Exception as e:
            print(f"⚠️ Jobs scan error (Remotive-{cat}): {e}")

    # Source B: Jobicy Remote Internships & Junior Roles Feed (Open RSS)
    try:
        url = "https://jobicy.com/?feed=job_feed&job_categories=engineering"
        root = _fetch_rss(url)
        if root is not None:
            for item in root.findall('.//item')[:10]:
                title = item.find('title').text if item.find('title') is not None else ""
                link = item.find('link').text if item.find('link') is not None else ""
                pub = item.find('pubDate').text[:16] if item.find('pubDate') is not None else ""
                title_lower = title.lower()
                
                if any(kw in title_lower for kw in INTERN_KEYWORDS):
                    try:
                        conn.execute('''
                            INSERT INTO radar_items (pillar, source, title, organization, url, deadline_or_date, extra_info)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        ''', ('jobs', 'Jobicy', title, 'Remote Tech', link, pub, "💼 Remote Engineering"))
                        new_items.append({'pillar': 'jobs', 'title': title, 'org': 'Remote Tech', 'url': link})
                    except sqlite3.IntegrityError:
                        pass
    except Exception as e:
        print(f"⚠️ Jobs scan error (Jobicy): {e}")

    conn.commit()
    conn.close()
    return new_items

# =====================================================================
# 2. 🚀 TECH EVENTS & HACKATHONS (Devpost, Devfolio, GDG, KonfHub)
# =====================================================================

def scan_events(limit=10):
    """Scan active hackathons, DevFest, and Indian tech conferences."""
    init_radar_db()
    new_items = []
    conn = get_db()

    # Source A: Devpost Online Hackathons
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
        print(f"⚠️ Events scan error (Devpost): {e}")

    # Source B: Google Developers & DevFest Announcements (RSS)
    try:
        url = "https://blog.google/technology/developers/rss/"
        root = _fetch_rss(url)
        if root is not None:
            for item in root.findall('.//item')[:5]:
                title = item.find('title').text if item.find('title') is not None else ""
                link = item.find('link').text if item.find('link') is not None else ""
                pub = item.find('pubDate').text[:16] if item.find('pubDate') is not None else ""
                title_lower = title.lower()
                if any(w in title_lower for w in ['devfest', 'hackathon', 'competition', 'summit', 'challenge', 'developer']):
                    try:
                        conn.execute('''
                            INSERT INTO radar_items (pillar, source, title, organization, url, deadline_or_date, extra_info)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        ''', ('events', 'Google Developers', title, 'Google GDG', link, pub, "🚀 Google DevFest / Event"))
                        new_items.append({'pillar': 'events', 'title': title, 'org': 'Google GDG', 'url': link})
                    except sqlite3.IntegrityError:
                        pass
    except Exception as e:
        print(f"⚠️ Events scan error (GDG): {e}")

    conn.commit()
    conn.close()
    return new_items

# =====================================================================
# 3. 📰 TECH NEWS & AI RADAR (Google AI, DeepMind, Hugging Face, YourStory, Inc42, TechCrunch, The Verge)
# =====================================================================

NEWS_FEEDS = [
    ("Google AI Blog", "https://blog.google/technology/ai/rss/", "🤖 AI / DeepMind"),
    ("Hugging Face", "https://huggingface.co/blog/feed.xml", "🤗 Open-Source AI"),
    ("TechCrunch", "https://techcrunch.com/category/artificial-intelligence/feed/", "⚡ Big Tech & AI"),
    ("The Verge", "https://www.theverge.com/rss/index.xml", "📱 Tech & Launches"),
    ("YourStory", "https://yourstory.com/feed", "🇮🇳 Indian Startups"),
    ("Inc42", "https://inc42.com/feed/", "💰 Indian Tech & Funding"),
]

def scan_news(limit_per_feed=2):
    """Scan breaking AI launches, Indian startups, and developer news."""
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
                    ''', ('news', source_name, title, category_tag, url, pub_date, f"{category_tag}"))
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
    """Scan all 3 customized pillars and push notifications."""
    print("📡 [Radar] Starting customized scan for Student Profile...")
    j = scan_jobs(limit=10)
    e = scan_events(limit=10)
    n = scan_news(limit_per_feed=2)
    
    total = len(j) + len(e) + len(n)
    print(f"📡 [Radar] Scan complete. Added {total} new items! (Jobs: {len(j)}, Events: {len(e)}, News: {len(n)})")

    if e or j:
        try:
            from services.notifier import notify
            if e:
                top_event = e[0]
                notify(
                    title=f"🚀 Hackathon: {top_event['title'][:40]}",
                    message=f"By: {top_event['org']}\nTap to check details.",
                    priority=4,
                    tags=["trophy", "computer"],
                    click_url=top_event['url']
                )
            if j:
                top_job = j[0]
                notify(
                    title=f"💼 Job Match: {top_job['title'][:40]}",
                    message=f"Company: {top_job['org']}\nTap to view role.",
                    priority=3,
                    tags=["briefcase"],
                    click_url=top_job['url']
                )
        except Exception as ex:
            print(f"⚠️ Radar notify error: {ex}")

    return {'jobs': len(j), 'events': len(e), 'news': len(n)}

def scan_high_priority():
    """High-priority scan: Jobs & Hackathons only (quick, focused)."""
    print("📡 [Radar] Running High-Priority scan (Jobs & Hackathons)...")
    j = scan_jobs(limit=10)
    e = scan_events(limit=10)
    print(f"📡 [Radar] High-priority scan complete: {len(j)} jobs, {len(e)} events found.")
    return {'jobs': len(j), 'events': len(e), 'news': 0}

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
