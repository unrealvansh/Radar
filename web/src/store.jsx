import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { getSaved, getSettings, loadHome, removeSaved, saveItem, updateSaved } from './api.js';

// Shared state for every view: saved items, interests, home city, the open detail and toasts.
const Radar = createContext(null);
export const useRadar = () => useContext(Radar);

export function RadarProvider({ children }) {
    const [saved, setSaved] = useState(new Map());   // item id -> saved row
    const [keywords, setKeywords] = useState([]);
    const [home] = useState(loadHome);
    const [detail, setDetail] = useState(null);       // the item shown in the detail sheet
    const [toasts, setToasts] = useState([]);

    const refreshSaved = useCallback(async () => {
        const rows = await getSaved();
        setSaved(new Map(rows.map(r => [r.item_id, r])));
    }, []);

    useEffect(() => {
        refreshSaved().catch(() => {});
        // Stored as one comma-separated string
        getSettings().then(s => setKeywords(String(s.keywords || '').split(',').map(k => k.trim().toLowerCase()).filter(Boolean)))
            .catch(() => {});
    }, [refreshSaved]);

    const toast = useCallback(text => {
        const id = Math.random();
        setToasts(t => [...t, { id, text }]);
        setTimeout(() => setToasts(t => t.filter(x => x.id !== id)), 2600);
    }, []);

    const run = useCallback(async (work, message) => {
        try {
            await work();
            await refreshSaved();
            if (message) toast(message);
        } catch (e) {
            if (e.message !== 'unauthorized') toast('That did not work. Check that the server is running.');
        }
    }, [refreshSaved, toast]);

    const actions = useMemo(() => ({
        save: it => run(() => saveItem(it.id), 'Saved to your board'),
        track: (it, deadline) => run(() => saveItem(it.id, { track: true, deadline: deadline || undefined }),
            'Tracked. You get a reminder 2 days before.'),
        setStatus: (it, status) => run(() => updateSaved(saved.get(it.id).id, { status }),
            status === 'applied' ? 'Marked as applied' : 'Moved back to saved'),
        remove: it => run(() => removeSaved(saved.get(it.id).id), 'Removed from your board'),
    }), [run, saved]);

    const value = { saved, keywords, home, detail, openDetail: setDetail, toast, toasts, ...actions };
    return <Radar.Provider value={value}>{children}</Radar.Provider>;
}
