// Same origin as the Radar app: reuse its login token and endpoints.

function read(key) {
    try { return localStorage.getItem(key); } catch { return null; }
}

export function write(key, value) {
    try {
        if (value === null) localStorage.removeItem(key);
        else localStorage.setItem(key, value);
    } catch { /* storage blocked: the setting just won't persist */ }
}

export function hasToken() {
    return !!read('radar_token');
}

export async function api(path, options = {}) {
    const headers = { 'X-Access-Token': read('radar_token') || '' };
    if (options.body) headers['Content-Type'] = 'application/json';
    const res = await fetch(path, { ...options, headers });
    if (res.status === 401) {
        dispatchEvent(new Event('radar:locked'));  // the app shows its login screen
        throw new Error('unauthorized');
    }
    return res.json();
}

/** Try a token; keep it if the server accepts it. */
export async function unlock(token) {
    const res = await fetch('/api/auth/check', { headers: { 'X-Access-Token': token } });
    if (!res.ok) return false;
    write('radar_token', token);
    return true;
}

export function lock() {
    write('radar_token', null);
    dispatchEvent(new Event('radar:locked'));
}

/** The user's saved city ({ city, lat, lon, radius }) or null. */
export function loadHome() {
    try { return JSON.parse(read('radar_home') || 'null'); } catch { return null; }
}

export function listItems({ pillar = 'opps', sort = 'latest', q = '', loc = '', limit = 24, offset = 0 }, home) {
    const p = new URLSearchParams({ pillar, sort, limit, offset });
    if (q) p.set('q', q);
    if (home) {
        p.set('near', `${home.lat},${home.lon}`);
        p.set('radius', home.radius);
    }
    if (loc) p.set('loc', loc);
    return api('/api/radar?' + p).then(r => r.items || []);
}

export const getSaved = () => api('/api/saved');
export const getSettings = () => api('/api/settings');
export const saveItem = (itemId, extra = {}) =>
    api('/api/saved', { method: 'POST', body: JSON.stringify({ item_id: itemId, ...extra }) });
export const updateSaved = (savedId, changes) =>
    api(`/api/saved/${savedId}`, { method: 'PUT', body: JSON.stringify(changes) });
export const removeSaved = savedId => api(`/api/saved/${savedId}`, { method: 'DELETE' });

// ---------- small display helpers shared by every view ----------

export function daysUntil(iso) {
    if (!iso) return null;
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    return Math.round((new Date(iso.slice(0, 10) + 'T00:00:00') - today) / 86400000);
}

export function fmtDate(iso) {
    if (!iso) return '';
    return new Date(iso.slice(0, 10) + 'T00:00:00').toLocaleDateString('en-IN', { day: 'numeric', month: 'short' });
}

/** "5 days left", "Closes today", "Starts 3 Nov" or "Posted 2d ago". */
export function whenText(it) {
    const d = daysUntil(it.deadline);
    if (d !== null && d >= 0) return d === 0 ? 'Closes today' : `${d} day${d === 1 ? '' : 's'} left`;
    if (it.starts_at) return `Starts ${fmtDate(it.starts_at)}`;
    const age = it.posted_at ? -daysUntil(it.posted_at) : null;
    if (age !== null) return age <= 0 ? 'Posted today' : `Posted ${age}d ago`;
    return it.source;
}

export function whereText(it) {
    if (it.mode === 'online') return 'Online';
    if (it.mode === 'remote' && !it.city) return 'Remote';
    if (!it.city) return '';
    const near = it.distance_km !== null && it.distance_km !== undefined && it.distance_km <= 500;
    return near ? `${it.city}, ${it.distance_km} km` : it.city;
}

export const TYPE_LABEL = { jobs: 'Job', events: 'Event', news: 'News' };

export function initials(text) {
    const words = String(text || '?').replace(/[^\p{L}\p{N} ]/gu, ' ').split(/\s+/).filter(Boolean);
    return (words.length > 1 ? words[0][0] + words[1][0] : (words[0] || '?').slice(0, 2)).toUpperCase();
}

/** Interest keywords that appear in the item (whole words). */
export function matchedKeywords(it, keywords) {
    const text = ` ${it.title} ${it.organization || ''} ${it.extra_info || ''} `.toLowerCase();
    return keywords.filter(k => new RegExp(`[^a-z0-9]${k.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}[^a-z0-9]`).test(text));
}
