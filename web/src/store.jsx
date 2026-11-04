import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react';
import { api, getSaved, getSettings, hasToken, loadHome, removeSaved, saveItem, updateSaved, write } from './api.js';

const Radar = createContext(null);
const Live = createContext(null);
const Detail = createContext(null);
export const useRadar = () => useContext(Radar);
export const useLive = () => useContext(Live);
export const useDetail = () => useContext(Detail);

export function RadarProvider({ children }) {
    const [locked, setLocked] = useState(!hasToken());
    const [saved, setSaved] = useState(new Map());
    const [settings, setSettings] = useState(null);
    const [home, setHomeState] = useState(loadHome);
    const [stats, setStats] = useState(null);
    const [detail, setDetail] = useState(null);
    const [toasts, setToasts] = useState([]);
    const [version, setVersion] = useState(0);
    const [notes, setNotes] = useState({ unread: 0, items: [] });
    const pollRef = useRef(0);
    const statsRef = useRef(null);
    statsRef.current = stats;

    useEffect(() => {
        const onLocked = () => setLocked(true);
        addEventListener('radar:locked', onLocked);
        return () => removeEventListener('radar:locked', onLocked);
    }, []);

    const toast = useCallback(text => {
        const id = Math.random();
        setToasts(t => [...t, { id, text }]);
        setTimeout(() => setToasts(t => t.filter(x => x.id !== id)), 2800);
    }, []);

    const refreshSaved = useCallback(async () => {
        const rows = await getSaved();
        setSaved(new Map(rows.map(r => [r.item_id, r])));
        return rows;
    }, []);

    const loadStats = useCallback(async () => {
        const s = await api('/api/stats');
        setStats(s);
        return s;
    }, []);

    const loadNotes = useCallback(async () => {
        const n = await api('/api/notifications?limit=80');
        setNotes(n);
        return n;
    }, []);

    const markRead = useCallback(async ids => {
        setNotes(n => ({
            unread: ids ? Math.max(0, n.unread - n.items.filter(x => ids.includes(x.id) && !x.read).length) : 0,
            items: n.items.map(x => (!ids || ids.includes(x.id) ? { ...x, read: true } : x)),
        }));
        try { await api('/api/notifications/read', { method: 'POST', body: JSON.stringify(ids ? { ids } : {}) }); } catch {  }
    }, []);

    const loadSettings = useCallback(async () => {
        const s = await getSettings();

        setSettings({ ...s, keywords: String(s.keywords || '').split(',').map(k => k.trim().toLowerCase()).filter(Boolean) });
        if (s.home) setHome(s.home);
        return s;
    }, []);

    useEffect(() => {
        if (locked) return;
        refreshSaved().catch(() => {});
        loadSettings().catch(() => {});
        loadStats().then(s => s.scanning && pollScan()).catch(() => {});
        loadNotes().catch(() => {});
        const t = setInterval(() => loadNotes().catch(() => {}), 60000);
        return () => clearInterval(t);
    }, [locked]);

    function setHome(h) {
        setHomeState(h);
        write('radar_home', h ? JSON.stringify(h) : null);
    }

    const saveSettings = useCallback(async changes => {
        await api('/api/settings', { method: 'POST', body: JSON.stringify(changes) });
        await loadSettings();
    }, [loadSettings]);

    const saveHome = useCallback(async h => {
        await api('/api/settings', { method: 'POST', body: JSON.stringify(h
            ? { home_city: h.city, home_lat: h.lat, home_lon: h.lon, radius_km: h.radius }
            : { home_city: null, home_lat: null, home_lon: null, radius_km: null }) });
        setHome(h);
    }, []);

    function pollScan() {
        clearInterval(pollRef.current);
        pollRef.current = setInterval(async () => {
            try {
                const s = await loadStats();
                loadNotes().catch(() => {});
                if (!s.scanning) {
                    clearInterval(pollRef.current);
                    setVersion(v => v + 1);
                    toast('Scan finished. Everything is up to date.');
                }
            } catch { clearInterval(pollRef.current); }
        }, 5000);
    }

    const scan = useCallback(async () => {
        if (statsRef.current?.scanning) return;
        try {
            await api('/api/radar/scan', { method: 'POST' });
            setStats(s => ({ ...(s || {}), scanning: true }));
            toast('Scanning 70+ sources. This takes 1 to 3 minutes.');
            pollScan();
        } catch (e) { if (e.message !== 'unauthorized') toast('Could not start a scan.'); }
    }, []);

    const run = useCallback(async (work, message) => {
        try {
            await work();
            await refreshSaved();
            loadStats().catch(() => {});
            if (message) toast(message);
        } catch (e) {
            if (e.message !== 'unauthorized') toast('That did not work. Check that the server is running.');
        }
    }, [refreshSaved, loadStats, toast]);

    const actions = useMemo(() => ({
        save: it => run(() => saveItem(it.id), 'Saved to your board'),
        track: (it, deadline) => run(() => saveItem(it.id, { track: true, deadline: deadline || undefined }),
            'Tracked. You get a reminder 2 days before.'),
        setStatus: (it, status) => run(() => updateSaved(saved.get(it.id).id, { status }),
            status === 'applied' ? 'Marked as applied' : status === 'done' ? 'Moved to done' : 'Moved back to saved'),
        remove: it => run(() => removeSaved(saved.get(it.id).id), 'Removed from your board'),
    }), [run, saved]);

    const value = useMemo(() => ({
        locked, setLocked, saved, refreshSaved, settings, saveSettings, keywords: settings?.keywords || [],
        home, saveHome, loadStats, scan, version, loadNotes, markRead, openDetail: setDetail, toast, ...actions,
    }), [locked, saved, settings, home, version, actions, refreshSaved, saveSettings, saveHome, loadStats, scan, loadNotes, markRead, toast]);
    const live = useMemo(() => ({ stats, notes, toasts }), [stats, notes, toasts]);
    return (
        <Radar.Provider value={value}>
            <Live.Provider value={live}>
                <Detail.Provider value={detail}>{children}</Detail.Provider>
            </Live.Provider>
        </Radar.Provider>
    );
}
