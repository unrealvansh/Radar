import { useEffect, useMemo, useRef, useState } from 'react';
import { AnimatePresence, motion } from 'motion/react';
import { TYPE_LABEL, listItems, lock, whenText } from '../api.js';
import { useRadar } from '../store.jsx';
import { IconSearch } from './Icons.jsx';

export default function Palette({ open, onClose, go }) {
    const { openDetail, scan, home } = useRadar();
    const [q, setQ] = useState('');
    const [results, setResults] = useState([]);
    const [index, setIndex] = useState(0);
    const inputRef = useRef(null);

    const commands = useMemo(() => [
        { label: 'Home', run: () => go('home') },
        { label: 'Feed', run: () => go('feed', { sort: 'latest', loc: '' }) },
        { label: 'Closing soon', run: () => go('feed', { sort: 'closing' }) },
        { label: 'Picks for me', run: () => go('feed', { sort: 'picks' }) },
        { label: 'Hackathons and events', run: () => go('feed', { pillar: 'events' }) },
        { label: 'Jobs and internships', run: () => go('feed', { pillar: 'jobs' }) },
        ...(home ? [{ label: `Near ${home.city}`, run: () => go('feed', { loc: 'near' }) }] : []),
        { label: 'Online and remote only', run: () => go('feed', { loc: 'online' }) },
        { label: 'Map', run: () => go('map') },
        { label: 'Calendar', run: () => go('calendar') },
        { label: 'Board', run: () => go('board') },
        { label: 'Settings', run: () => go('settings') },
        { label: 'Scan now', run: scan },
        { label: 'Lock this device', run: lock },
    ], [go, scan, home]);

    useEffect(() => {
        if (!open) return;
        setQ('');
        setIndex(0);
        setTimeout(() => inputRef.current?.focus(), 30);
    }, [open]);

    useEffect(() => {
        if (q.trim().length < 2) { setResults([]); return; }
        const t = setTimeout(() => listItems({ q, limit: 8 }).then(setResults).catch(() => {}), 200);
        return () => clearTimeout(t);
    }, [q]);

    const cmds = commands.filter(c => !q || c.label.toLowerCase().includes(q.toLowerCase()));
    const rows = [
        ...results.map(it => ({ key: `i${it.id}`, label: it.title, sub: [TYPE_LABEL[it.pillar], it.organization, whenText(it)].filter(Boolean).join(', '),
                                run: () => openDetail(it) })),
        ...cmds.map(c => ({ key: c.label, label: c.label, sub: 'Go', run: c.run })),
    ];

    const choose = r => { onClose(); r?.run(); };
    const onKey = e => {
        if (e.key === 'Escape') onClose();
        if (e.key === 'ArrowDown') { e.preventDefault(); setIndex(i => Math.min(rows.length - 1, i + 1)); }
        if (e.key === 'ArrowUp') { e.preventDefault(); setIndex(i => Math.max(0, i - 1)); }
        if (e.key === 'Enter') { e.preventDefault(); choose(rows[index]); }
    };

    return (
        <AnimatePresence>
            {open && (
                <motion.div className="palette-wrap" onClick={e => e.target === e.currentTarget && onClose()}
                            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
                    <motion.div className="palette" role="dialog" aria-modal="true" aria-label="Search and commands"
                                initial={{ opacity: 0, y: -14, scale: 0.98 }} animate={{ opacity: 1, y: 0, scale: 1 }}
                                exit={{ opacity: 0, y: -10, scale: 0.98 }} transition={{ duration: 0.2 }}>
                        <div className="palette-input">
                            <IconSearch />
                            <input ref={inputRef} value={q} onChange={e => { setQ(e.target.value); setIndex(0); }} onKeyDown={onKey}
                                   placeholder="Search opportunities or type a command" aria-label="Search"
                                   role="combobox" aria-expanded="true" aria-controls="palette-list" />
                            <kbd>Esc</kbd>
                        </div>
                        <ul className="palette-list" id="palette-list" role="listbox">
                            {rows.map((r, i) => (
                                <li key={r.key} role="option" aria-selected={i === index}
                                    onMouseEnter={() => setIndex(i)} onClick={() => choose(r)}>
                                    <strong>{r.label}</strong><span>{r.sub}</span>
                                </li>
                            ))}
                            {rows.length === 0 && <li className="palette-empty">No matches</li>}
                        </ul>
                    </motion.div>
                </motion.div>
            )}
        </AnimatePresence>
    );
}
