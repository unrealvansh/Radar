import { useEffect, useState } from 'react';
import { AnimatePresence, motion } from 'motion/react';
import { useLive, useRadar } from '../store.jsx';
import { IconSearch } from './Icons.jsx';

export const VIEWS = [
    { id: 'simple', label: 'Simple', key: '1' },
    { id: 'aura', label: 'Aura', key: '2' },
    { id: 'map', label: 'Map', key: '3' },
];

/** Segmented view switch; the highlight slides between options. */
export function ViewSwitch({ view, onChange }) {
    return (
        <div className="switch" role="tablist" aria-label="View">
            {VIEWS.map(v => (
                <button key={v.id} role="tab" aria-selected={view === v.id} onClick={() => onChange(v.id)}
                        title={`${v.label} view (${v.key})`}>
                    {view === v.id && (
                        <motion.span className="switch-hl" layoutId="switch-hl"
                                     transition={{ type: 'spring', stiffness: 420, damping: 34 }} />
                    )}
                    <span className="switch-label">{v.label}</span>
                </button>
            ))}
        </div>
    );
}

const PILLARS = [['opps', 'All'], ['jobs', 'Jobs and internships'], ['events', 'Hackathons and events'], ['news', 'Tech news']];
const MAP_PILLARS = PILLARS.filter(([id]) => id !== 'news');

/** Type, place, ranking and search. Shared by all three views. */
export function FilterBar({ filters, setFilters, hideSearch = false, noNews = false }) {
    const { home } = useRadar();
    const [q, setQ] = useState(filters.q);
    useEffect(() => {
        const t = setTimeout(() => q !== filters.q && setFilters(f => ({ ...f, q })), 300);
        return () => clearTimeout(t);
    }, [q]);  // eslint-disable-line react-hooks/exhaustive-deps

    const toggleLoc = loc => setFilters(f => ({ ...f, loc: f.loc === loc ? '' : loc }));

    return (
        <div className="filters">
            <div className="pillars" role="group" aria-label="Type">
                {(noNews ? MAP_PILLARS : PILLARS).map(([id, label]) => (
                    <button key={id} aria-pressed={filters.pillar === id} onClick={() => setFilters(f => ({ ...f, pillar: id }))}>
                        {filters.pillar === id && <motion.span className="pillar-hl" layoutId="pillar-hl"
                                                               transition={{ type: 'spring', stiffness: 420, damping: 34 }} />}
                        <span>{label}</span>
                    </button>
                ))}
            </div>
            <button className="chip" aria-pressed={filters.sort === 'picks'}
                    onClick={() => setFilters(f => ({ ...f, sort: f.sort === 'picks' ? 'latest' : 'picks' }))}>For you</button>
            <button className="chip" aria-pressed={filters.sort === 'closing'}
                    onClick={() => setFilters(f => ({ ...f, sort: f.sort === 'closing' ? 'latest' : 'closing' }))}>Closing soon</button>
            <button className="chip" aria-pressed={filters.loc === 'near'} disabled={!home}
                    title={home ? `Within ${home.radius} km of ${home.city}` : 'Set your city in Radar settings first'}
                    onClick={() => toggleLoc('near')}>{home ? `Near ${home.city}` : 'Near me'}</button>
            <button className="chip" aria-pressed={filters.loc === 'online'} onClick={() => toggleLoc('online')}>Online</button>
            {!hideSearch && (
                <label className="search">
                    <IconSearch />
                    <span className="sr-only">Search</span>
                    <input type="search" value={q} onChange={e => setQ(e.target.value)} placeholder="Search roles, hackathons, companies" />
                </label>
            )}
        </div>
    );
}

export function Toasts() {
    const { toasts } = useLive();
    return (
        <div className="toasts" aria-live="polite">
            <AnimatePresence>
                {toasts.map(t => (
                    <motion.div key={t.id} className="toast" layout
                                initial={{ opacity: 0, y: 16, scale: 0.98 }} animate={{ opacity: 1, y: 0, scale: 1 }}
                                exit={{ opacity: 0, y: 8 }}>{t.text}</motion.div>
                ))}
            </AnimatePresence>
        </div>
    );
}
