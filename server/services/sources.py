"""
Radar sources: every website the radar reads, in one registry.

Each adapter fetches one site and returns a list of plain dicts:
    pillar        'jobs' | 'events' | 'news'
    source        site name shown on the card
    title, organization, url
    deadline      ISO date: last day to apply / take part (None if unknown)
    starts_at     ISO date the event starts (None if unknown)
    posted_at     ISO date the item was published (None if unknown)
    extra_info    short tag line (prize, type, location)
    date_text     human readable date line for the card

Fetching is sequential and every adapter is wrapped in try/except by the
scanner, so one broken site never stops the others.
To add a website: write an adapter (or reuse rss/greenhouse/lever/ashby)
and add one line to SOURCES at the bottom.
"""

import json
import re
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
TIMEOUT = 12
IST = timezone(timedelta(hours=5, minutes=30))

INDIA_WORDS = ['india', 'bengaluru', 'bangalore', 'mumbai', 'pune', 'hyderabad', 'gurgaon',
               'gurugram', 'noida', 'delhi', 'chennai', 'kolkata', 'ahmedabad', 'jaipur']
REMOTE_OK_WORDS = ['worldwide', 'anywhere', 'global', 'apac', 'asia', 'india', 'remote']


# =====================================================================
# FETCH & DATE HELPERS
# =====================================================================

def fetch(url, data=None):
    headers = {"User-Agent": USER_AGENT,
               "Accept": "application/json, application/rss+xml, application/xml, text/xml, */*"}
    if data is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(data).encode()
    req = urllib.request.Request(url, data=data, headers=headers)
    with urllib.request.urlopen(req, timeout=TIMEOUT) as response:
        return response.read()


def fetch_json(url, data=None):
    return json.loads(fetch(url, data).decode('utf-8', 'replace'))


def to_date(value):
    """Epoch (s or ms), ISO string or RSS date -> 'YYYY-MM-DD' in IST, else None."""
    if value in (None, '', 0):
        return None
    try:
        if isinstance(value, (int, float)):
            ts = value / 1000 if value > 1e11 else value
            return datetime.fromtimestamp(ts, IST).strftime('%Y-%m-%d')
        value = str(value).strip()
        if re.match(r'^\d{4}-\d{2}-\d{2}', value):
            try:
                dt = datetime.fromisoformat(value.replace('Z', '+00:00').replace(' ', 'T', 1))
                if dt.tzinfo:
                    dt = dt.astimezone(IST)
                return dt.strftime('%Y-%m-%d')
            except ValueError:
                return value[:10]
        return parsedate_to_datetime(value).astimezone(IST).strftime('%Y-%m-%d')
    except Exception:
        return None


def nice(iso):
    """'2026-11-05' -> '5 Nov'."""
    try:
        d = datetime.strptime(iso, '%Y-%m-%d')
        return f"{d.day} {d.strftime('%b')}"
    except (TypeError, ValueError):
        return ''


def strip_html(text):
    return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', text or '')).strip()


EMOJI = re.compile('[\U0001F000-\U0001FAFF\u2600-\u27BF\u2B00-\u2BFF\uFE0F\u200D]')


def tidy(text):
    """Drop emojis and join parts with commas: 'Hackathon • Pune' -> 'Hackathon, Pune'."""
    text = EMOJI.sub('', text or '')
    text = re.sub(r'\s*[•·|]\s*|\s+[—–]\s+|—', ', ', text)
    text = re.sub(r'\s+', ' ', text)
    return re.sub(r'(,\s*)+', ', ', text).strip(' ,')


def item(pillar, source, title, url, organization='', deadline=None, starts_at=None,
         posted_at=None, extra_info='', date_text='', image='', logo=''):
    if not date_text:
        if starts_at:
            date_text = f"Starts {nice(starts_at)}"
        elif deadline:
            date_text = f"Apply by {nice(deadline)}"
    return {
        'pillar': pillar, 'source': source, 'title': tidy(strip_html(title))[:200],
        'organization': strip_html(organization)[:120], 'url': (url or '').strip(),
        'deadline': deadline, 'starts_at': starts_at, 'posted_at': posted_at,
        'extra_info': tidy(extra_info), 'date_text': date_text,
        'image': img_url(image), 'logo': img_url(logo),
    }


def img_url(url):
    """'//cdn/x.png' -> 'https://cdn/x.png'; anything that isn't an http(s) URL -> ''."""
    url = (url or '').strip()
    if url.startswith('//'):
        url = 'https:' + url
    return url if url.startswith(('https://', 'http://')) else ''


def location_ok(text, words=REMOTE_OK_WORDS):
    text = (text or '').lower()
    return not text.strip() or any(w in text for w in words)


# =====================================================================
# GENERIC ADAPTERS (RSS, company job boards)
# =====================================================================

def rss(url, source, pillar='news', tag='', limit=3):
    """Any RSS 2.0 or Atom feed."""
    def fetcher():
        root = ET.fromstring(fetch(url))
        out = []
        entries = root.findall('.//item') or root.findall('{http://www.w3.org/2005/Atom}entry')
        for e in entries[:limit]:
            title = e.findtext('title') or e.findtext('{http://www.w3.org/2005/Atom}title') or ''
            link = e.findtext('link') or ''
            if not link:
                a = e.find('{http://www.w3.org/2005/Atom}link')
                link = a.get('href') if a is not None else ''
            pub = (e.findtext('pubDate') or e.findtext('{http://www.w3.org/2005/Atom}published')
                   or e.findtext('{http://www.w3.org/2005/Atom}updated'))
            out.append(item(pillar, source, title, link, organization=tag,
                            posted_at=to_date(pub), extra_info=tag))
        return out
    return fetcher


def greenhouse(slug, company):
    """Company careers on Greenhouse: India roles only."""
    def fetcher():
        data = fetch_json(f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs")
        out = []
        for j in data.get('jobs', []):
            loc = (j.get('location') or {}).get('name', '')
            if not loc or not location_ok(loc, INDIA_WORDS):
                continue
            out.append(item('jobs', f"{company} Careers", j.get('title'), j.get('absolute_url'),
                            organization=company, posted_at=to_date(j.get('first_published') or j.get('updated_at')),
                            extra_info=f"{loc}"))
        return out
    return fetcher


def lever(slug, company):
    """Company careers on Lever: India roles only."""
    def fetcher():
        out = []
        for j in fetch_json(f"https://api.lever.co/v0/postings/{slug}?mode=json"):
            cats = j.get('categories') or {}
            loc = ', '.join(cats.get('allLocations') or [cats.get('location') or ''])
            if not loc or not location_ok(loc, INDIA_WORDS):
                continue
            out.append(item('jobs', f"{company} Careers", j.get('text'), j.get('hostedUrl'),
                            organization=company, posted_at=to_date(j.get('createdAt')),
                            extra_info=f"{loc}"))
        return out
    return fetcher


def ashby(slug, company):
    """Company careers on Ashby: India roles only."""
    def fetcher():
        out = []
        for j in fetch_json(f"https://api.ashbyhq.com/posting-api/job-board/{slug}").get('jobs', []):
            loc = j.get('location') or ''
            if not loc or not location_ok(loc, INDIA_WORDS):
                continue
            out.append(item('jobs', f"{company} Careers", j.get('title'), j.get('jobUrl'),
                            organization=company, posted_at=to_date(j.get('publishedAt')),
                            extra_info=f"{loc or 'Remote'}"))
        return out
    return fetcher


# =====================================================================
# HACKATHONS, COMPETITIONS, EVENTS, CODING CONTESTS
# =====================================================================

def unstop(kind, pillar, label):
    """Unstop: hackathons / competitions / internships / jobs / scholarships / workshops."""
    def fetcher():
        url = (f"https://unstop.com/api/public/opportunity/search-result"
               f"?opportunity={kind}&per_page=20&oppstatus=open")
        out = []
        for d in fetch_json(url)['data']['data']:
            regn = d.get('regnRequirements') or {}
            deadline = to_date(regn.get('end_regn_dt') or d.get('end_date'))
            org = (d.get('organisation') or {}).get('name', '')
            region = (d.get('region') or '').title()
            city = ((d.get('address_with_country_logo') or {}).get('city') or '') if region != 'Online' else ''
            where = ', '.join(p for p in (region, city) if p)
            out.append(item(pillar, 'Unstop', d.get('title'), d.get('seo_url'), organization=org,
                            deadline=deadline, posted_at=to_date(d.get('approved_date') or d.get('updated_at')),
                            extra_info=f"{label}{', ' + where if where else ''}",
                            date_text=f"Apply by {nice(deadline)}" if deadline else '',
                            image=d.get('logoUrl2'), logo=(d.get('organisation') or {}).get('logoUrl')))
        return out
    return fetcher


def devpost():
    data = fetch_json("https://devpost.com/api/hackathons?status[]=upcoming&status[]=open")
    out = []
    for h in data.get('hackathons', []):
        dates = h.get('submission_period_dates', '')
        prize = strip_html(h.get('prize_amount', '')) or 'Certificates/Swag'
        where = (h.get('displayed_location') or {}).get('location', '')
        out.append(item('events', 'Devpost', h.get('title'), h.get('url'),
                        organization=h.get('organization_name') or 'Devpost',
                        deadline=parse_range_end(dates), extra_info=f"Prize {prize} • {where}",
                        date_text=dates, image=h.get('thumbnail_url')))
    return out


def parse_range_end(dates):
    """'Oct 01 - Nov 15, 2026' / 'Oct 15 - 30, 2026' -> '2026-11-15' (or None)."""
    if not dates or '-' not in dates:
        return None
    start, end = [p.strip() for p in dates.rsplit('-', 1)]
    if re.match(r'^\d{1,2}, \d{4}$', end):
        end = start.split()[0] + ' ' + end
    for fmt in ('%b %d, %Y', '%B %d, %Y'):
        try:
            return datetime.strptime(end, fmt).strftime('%Y-%m-%d')
        except ValueError:
            continue
    return None


def devfolio():
    data = fetch_json("https://api.devfolio.co/api/search/hackathons",
                      {"type": "application_open", "from": 0, "size": 30})
    out = []
    for hit in data['hits']['hits']:
        h = hit['_source']
        setting = h.get('hackathon_setting') or {}
        where = 'Online' if h.get('is_online') else (h.get('city') or h.get('location') or '')
        out.append(item('events', 'Devfolio', h.get('name'), f"https://{h.get('slug')}.devfolio.co/",
                        organization=h.get('tagline') or 'Devfolio',
                        deadline=to_date(setting.get('reg_ends_at') or h.get('starts_at')),
                        starts_at=to_date(h.get('starts_at')), extra_info=f"Hackathon • {where}",
                        image=h.get('cover_img'), logo=setting.get('logo')))
    return out


def hackerearth():
    out = []
    for h in fetch_json("https://www.hackerearth.com/chrome-extension/events/").get('response', []):
        out.append(item('events', 'HackerEarth', h.get('title'), h.get('url'), organization='HackerEarth',
                        deadline=to_date(h.get('end_tz')), starts_at=to_date(h.get('start_tz')),
                        extra_info=f"{h.get('challenge_type') or 'Challenge'}"))
    return out


def mlh():
    year = datetime.now().year + (1 if datetime.now().month >= 8 else 0)  # MLH seasons start in autumn
    html = fetch(f"https://mlh.io/seasons/{year}/events").decode('utf-8', 'replace')
    out = []
    for block in html.split('itemType="https://schema.org/Event"')[1:]:
        url = re.search(r'itemProp="url" content="([^"]+)"', block)
        start = re.search(r'itemProp="startDate" content="([^"]+)"', block)
        name = re.search(r'<h4[^>]*>(.*?)</h4>', block, re.S)
        city = re.search(r'itemProp="addressLocality" content="([^"]*)"', block)
        country = re.search(r'itemProp="addressCountry" content="([^"]*)"', block)
        if not (url and start and name):
            continue
        starts = to_date(start.group(1))
        where = ', '.join(x.group(1) for x in (city, country) if x and x.group(1)) or 'Online'
        out.append(item('events', 'MLH', name.group(1), url.group(1), organization='Major League Hacking',
                        deadline=starts, starts_at=starts, extra_info=f"MLH Hackathon • {where}"))
    return out


def dev_events():
    root = ET.fromstring(fetch("https://dev.events/rss.xml"))
    out = []
    for e in root.findall('.//item'):
        desc = e.findtext('description') or ''
        m = re.search(r'happening on ([A-Z][a-z]+ \d{1,2}, \d{4})', desc)
        starts = datetime.strptime(m.group(1), '%B %d, %Y').strftime('%Y-%m-%d') if m else None
        where = re.search(r'\d{4}, ([^.]+)\.', desc)
        out.append(item('events', 'dev.events', e.findtext('title'), e.findtext('link'),
                        organization='Developer conference', deadline=starts, starts_at=starts,
                        extra_info=f"Conference • {where.group(1) if where else ''}"))
    return out


def gdg():
    data = fetch_json("https://gdg.community.dev/api/search/?result_types=upcoming_event&country_code=IN")
    out = []
    for e in data.get('results', []):
        starts = to_date(e.get('start_date'))
        out.append(item('events', 'GDG', e.get('title'), e.get('url'),
                        organization=(e.get('chapter') or {}).get('title', 'Google Developer Groups'),
                        deadline=starts, starts_at=starts, extra_info=f"GDG Event • {e.get('city') or ''}"))
    return out


def codeforces():
    out = []
    for c in fetch_json("https://codeforces.com/api/contest.list?gym=false").get('result', []):
        if c.get('phase') != 'BEFORE':
            continue
        starts = to_date(c.get('startTimeSeconds'))
        out.append(item('events', 'Codeforces', f"{c['name']}: {nice(starts)}",
                        f"https://codeforces.com/contests/{c['id']}", organization='Codeforces',
                        deadline=starts, starts_at=starts, extra_info="Coding contest"))
    return out


def codechef():
    data = fetch_json("https://www.codechef.com/api/list/contests/all?sort_by=START&sorting_order=asc&offset=0&mode=all")
    out = []
    for c in data.get('future_contests', []) + data.get('present_contests', []):
        starts = to_date(c.get('contest_start_date_iso'))
        out.append(item('events', 'CodeChef', f"{c['contest_name']}: {nice(starts)}",
                        f"https://www.codechef.com/{c['contest_code']}", organization='CodeChef',
                        deadline=to_date(c.get('contest_end_date_iso')), starts_at=starts,
                        extra_info="Coding contest"))
    return out


def leetcode():
    data = fetch_json("https://leetcode.com/graphql",
                      {"query": "{ upcomingContests { title titleSlug startTime } }"})
    out = []
    for c in data['data']['upcomingContests']:
        starts = to_date(c.get('startTime'))
        out.append(item('events', 'LeetCode', f"{c['title']}: {nice(starts)}",
                        f"https://leetcode.com/contest/{c['titleSlug']}/", organization='LeetCode',
                        deadline=starts, starts_at=starts, extra_info="Coding contest"))
    return out


def hackerrank():
    out = []
    for c in fetch_json("https://www.hackerrank.com/rest/contests/upcoming?offset=0&limit=20").get('models', []):
        if c.get('ended'):
            continue
        out.append(item('events', 'HackerRank', c.get('name'), f"https://www.hackerrank.com/contests/{c['slug']}",
                        organization='HackerRank', deadline=to_date(c.get('epoch_endtime')),
                        starts_at=to_date(c.get('epoch_starttime')), extra_info="Coding contest"))
    return out


# =====================================================================
# JOB & INTERNSHIP BOARDS
# =====================================================================

def remotive(category):
    def fetcher():
        data = fetch_json(f"https://remotive.com/api/remote-jobs?category={category}&limit=50")
        out = []
        for j in data.get('jobs', []):
            loc = j.get('candidate_required_location', '')
            if not location_ok(loc):
                continue
            out.append(item('jobs', 'Remotive', j.get('title'), j.get('url'), organization=j.get('company_name'),
                            posted_at=to_date(j.get('publication_date')),
                            extra_info=f"Remote • {loc}{', ' + j['salary'] if j.get('salary') else ''}"))
        return out
    return fetcher


def jobicy():
    out = []
    for j in fetch_json("https://jobicy.com/api/v2/remote-jobs?count=50&industry=dev").get('jobs', []):
        if not location_ok(j.get('jobGeo')):
            continue
        out.append(item('jobs', 'Jobicy', j.get('jobTitle'), j.get('url'), organization=j.get('companyName'),
                        posted_at=to_date(j.get('pubDate')), extra_info=f"Remote • {j.get('jobGeo', '')}"))
    return out


def weworkremotely(category):
    def fetcher():
        root = ET.fromstring(fetch(f"https://weworkremotely.com/categories/{category}.rss"))
        out = []
        for e in root.findall('.//item'):
            region = e.findtext('region') or ''
            if not location_ok(region):
                continue
            company, _, title = (e.findtext('title') or '').partition(': ')
            out.append(item('jobs', 'We Work Remotely', title or company, e.findtext('link'), organization=company,
                            posted_at=to_date(e.findtext('pubDate')), extra_info=f"Remote • {region}"))
        return out
    return fetcher


def remoteok():
    out = []
    for j in fetch_json("https://remoteok.com/api")[1:]:  # first element is the legal notice
        if not location_ok(j.get('location')):
            continue
        out.append(item('jobs', 'RemoteOK', j.get('position'), j.get('url'), organization=j.get('company'),
                        posted_at=to_date(j.get('date')), extra_info="Remote"))
    return out


def himalayas():
    out = []
    for j in fetch_json("https://himalayas.app/jobs/api?limit=50").get('jobs', []):
        places = ', '.join(j.get('locationRestrictions') or [])
        if places and 'india' not in places.lower():
            continue
        out.append(item('jobs', 'Himalayas', j.get('title'), j.get('guid') or j.get('applicationLink'),
                        organization=j.get('companyName'), posted_at=to_date(j.get('pubDate')),
                        deadline=to_date(j.get('expiryDate')),
                        extra_info=f"Remote • {places or 'Worldwide'}"))
    return out


def working_nomads():
    out = []
    for j in fetch_json("https://www.workingnomads.com/api/exposed_jobs/"):
        if j.get('category_name') != 'Development' or not location_ok(j.get('location')):
            continue
        out.append(item('jobs', 'Working Nomads', j.get('title'), j.get('url'), organization=j.get('company_name'),
                        posted_at=to_date(j.get('pub_date')), extra_info=f"Remote • {j.get('location', '')}"))
    return out


def hn_jobs():
    root = ET.fromstring(fetch("https://hnrss.org/jobs"))
    out = []
    for e in root.findall('.//item'):
        out.append(item('jobs', 'Hacker News Jobs', e.findtext('title'), e.findtext('link'),
                        organization='YC startup', posted_at=to_date(e.findtext('pubDate')), extra_info="Startup"))
    return out


# =====================================================================
# REGISTRY: (name, pillar, fetcher)
# =====================================================================

SOURCES = [
    # ---- Hackathons, competitions, events, contests (14) ----
    ('Unstop Hackathons', 'events', unstop('hackathons', 'events', 'Hackathon')),
    ('Unstop Competitions', 'events', unstop('competitions', 'events', 'Competition')),
    ('Unstop Scholarships', 'events', unstop('scholarships', 'events', 'Scholarship')),
    ('Unstop Workshops', 'events', unstop('workshops', 'events', 'Workshop')),
    ('Devpost', 'events', devpost),
    ('Devfolio', 'events', devfolio),
    ('HackerEarth', 'events', hackerearth),
    ('MLH', 'events', mlh),
    ('dev.events', 'events', dev_events),
    ('GDG India', 'events', gdg),
    ('Codeforces', 'events', codeforces),
    ('CodeChef', 'events', codechef),
    ('LeetCode', 'events', leetcode),
    ('HackerRank', 'events', hackerrank),

    # ---- Job & internship boards (12) ----
    ('Unstop Internships', 'jobs', unstop('internships', 'jobs', 'Internship')),
    ('Unstop Jobs', 'jobs', unstop('jobs', 'jobs', 'Job')),
    ('Remotive Software', 'jobs', remotive('software-dev')),
    ('Remotive Data', 'jobs', remotive('data')),
    ('Jobicy', 'jobs', jobicy),
    ('WWR Programming', 'jobs', weworkremotely('remote-programming-jobs')),
    ('WWR Back-End', 'jobs', weworkremotely('remote-back-end-programming-jobs')),
    ('WWR DevOps', 'jobs', weworkremotely('remote-devops-sysadmin-jobs')),
    ('RemoteOK', 'jobs', remoteok),
    ('Himalayas', 'jobs', himalayas),
    ('Working Nomads', 'jobs', working_nomads),
    ('Hacker News Jobs', 'jobs', hn_jobs),

    # ---- Company career pages, India / remote roles (23) ----
    ('Groww', 'jobs', greenhouse('groww', 'Groww')),
    ('Druva', 'jobs', greenhouse('druva', 'Druva')),
    ('Rubrik', 'jobs', greenhouse('rubrik', 'Rubrik')),
    ('Databricks', 'jobs', greenhouse('databricks', 'Databricks')),
    ('MongoDB', 'jobs', greenhouse('mongodb', 'MongoDB')),
    ('GitLab', 'jobs', greenhouse('gitlab', 'GitLab')),
    ('Okta', 'jobs', greenhouse('okta', 'Okta')),
    ('Zscaler', 'jobs', greenhouse('zscaler', 'Zscaler')),
    ('Elastic', 'jobs', greenhouse('elastic', 'Elastic')),
    ('Netskope', 'jobs', greenhouse('netskope', 'Netskope')),
    ('Coursera', 'jobs', greenhouse('coursera', 'Coursera')),
    ('Twilio', 'jobs', greenhouse('twilio', 'Twilio')),
    ('InMobi', 'jobs', greenhouse('inmobi', 'InMobi')),
    ('Airbnb', 'jobs', greenhouse('airbnb', 'Airbnb')),
    ('Stripe', 'jobs', greenhouse('stripe', 'Stripe')),
    ('Smartsheet', 'jobs', greenhouse('smartsheet', 'Smartsheet')),
    ('CRED', 'jobs', lever('cred', 'CRED')),
    ('Meesho', 'jobs', lever('meesho', 'Meesho')),
    ('Zeta', 'jobs', lever('zeta', 'Zeta')),
    ('Paytm', 'jobs', lever('paytm', 'Paytm')),
    ('FamPay', 'jobs', lever('fampay', 'FamPay')),
    ('Sarvam AI', 'jobs', ashby('sarvam', 'Sarvam AI')),
    ('Atlan', 'jobs', ashby('atlan', 'Atlan')),

    # ---- Tech news (22) ----
    ('Google AI Blog', 'news', rss("https://blog.google/technology/ai/rss/", 'Google AI Blog', tag='AI')),
    ('Google Developers', 'news', rss("https://developers.googleblog.com/feeds/posts/default?alt=rss", 'Google Developers', tag='Dev')),
    ('Hugging Face', 'news', rss("https://huggingface.co/blog/feed.xml", 'Hugging Face', tag='Open-Source AI')),
    ('OpenAI', 'news', rss("https://openai.com/news/rss.xml", 'OpenAI', tag='AI')),
    ('TechCrunch', 'news', rss("https://techcrunch.com/category/artificial-intelligence/feed/", 'TechCrunch', tag='Big Tech & AI')),
    ('The Verge', 'news', rss("https://www.theverge.com/rss/index.xml", 'The Verge', tag='Tech')),
    ('Ars Technica', 'news', rss("https://feeds.arstechnica.com/arstechnica/technology-lab", 'Ars Technica', tag='Tech')),
    ('MIT Technology Review', 'news', rss("https://www.technologyreview.com/feed/", 'MIT Technology Review', tag='Research')),
    ('Hacker News', 'news', rss("https://hnrss.org/frontpage?points=300", 'Hacker News', tag='Trending')),
    ('GitHub Blog', 'news', rss("https://github.blog/feed/", 'GitHub Blog', tag='Dev')),
    ('Stack Overflow Blog', 'news', rss("https://stackoverflow.blog/feed/", 'Stack Overflow Blog', tag='Dev')),
    ('DEV Community', 'news', rss("https://dev.to/feed", 'DEV Community', tag='Dev')),
    ('JetBrains Blog', 'news', rss("https://blog.jetbrains.com/feed/", 'JetBrains Blog', tag='Dev')),
    ('Cloudflare Blog', 'news', rss("https://blog.cloudflare.com/rss/", 'Cloudflare Blog', tag='Cloud')),
    ('AWS News', 'news', rss("https://aws.amazon.com/blogs/aws/feed/", 'AWS News', tag='Cloud')),
    ('Product Hunt', 'news', rss("https://www.producthunt.com/feed", 'Product Hunt', tag='Launches')),
    ('YourStory', 'news', rss("https://yourstory.com/feed", 'YourStory', tag='Indian Startups')),
    ('Inc42', 'news', rss("https://inc42.com/feed/", 'Inc42', tag='Indian Tech & Funding')),
    ('Analytics India Magazine', 'news', rss("https://analyticsindiamag.com/feed/", 'Analytics India Magazine', tag='AI in India')),
    ('ET Tech', 'news', rss("https://economictimes.indiatimes.com/tech/rssfeeds/13357270.cms", 'ET Tech', tag='Indian Tech')),
    ('Mint Tech', 'news', rss("https://www.livemint.com/rss/technology", 'Mint Tech', tag='Indian Tech')),
    ('MediaNama', 'news', rss("https://www.medianama.com/feed/", 'MediaNama', tag='Tech Policy')),
]
