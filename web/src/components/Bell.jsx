import { useEffect, useRef, useState } from 'react';
import { AnimatePresence, motion } from 'motion/react';
import { useLive, useRadar } from '../store.jsx';
import { IconBell } from './Icons.jsx';

function ago(ts) {
    const mins = Math.round((Date.now() - new Date(ts.replace(' ', 'T'))) / 60000);
    if (mins < 1) return 'just now';
    if (mins < 60) return `${mins} min ago`;
    if (mins < 1440) return `${Math.round(mins / 60)} h ago`;
    return `${Math.round(mins / 1440)} d ago`;
}

export default function Bell() {
    const { markRead, openDetail, loadNotes } = useRadar();
    const { notes, stats } = useLive();
    const [open, setOpen] = useState(false);
    const ref = useRef(null);

    useEffect(() => {
        if (!open) return;
        loadNotes().catch(() => {});
        const close = e => { if (!ref.current?.contains(e.target)) setOpen(false); };
        const esc = e => { if (e.key === 'Escape') setOpen(false); };
        document.addEventListener('pointerdown', close);
        document.addEventListener('keydown', esc);
        return () => { document.removeEventListener('pointerdown', close); document.removeEventListener('keydown', esc); };
    }, [open, loadNotes]);

    return (
        <div className="bell" ref={ref}>
            <button className="icon-btn" aria-label={`Notifications${notes.unread ? `, ${notes.unread} unread` : ''}`}
                    aria-expanded={open} onClick={() => setOpen(o => !o)}>
                <IconBell />
                <AnimatePresence>
                    {notes.unread > 0 && (
                        <motion.span className="bell-badge" key="b" initial={{ scale: 0 }} animate={{ scale: 1 }} exit={{ scale: 0 }}>
                            {notes.unread > 99 ? '99+' : notes.unread}
                        </motion.span>
                    )}
                </AnimatePresence>
            </button>
            <AnimatePresence>
                {open && (
                    <motion.div className="bell-panel" role="dialog" aria-label="Notifications"
                                initial={{ opacity: 0, y: -8, scale: 0.98 }} animate={{ opacity: 1, y: 0, scale: 1 }}
                                exit={{ opacity: 0, y: -8, scale: 0.98 }} transition={{ duration: 0.18 }}>
                        <div className="bell-head">
                            <strong>Notifications</strong>
                            <button className="link-btn" disabled={!notes.unread} onClick={() => markRead(null)}>Mark all read</button>
                        </div>
                        {stats?.scanning && (
                            <div className="bell-scan"><span className="bell-pulse" />Scanning 70+ sources. New finds appear here as they come in.</div>
                        )}
                        <ul className="bell-list">
                            {notes.items.length === 0 && <li className="bell-empty">Nothing yet. New finds from each scan show up here.</li>}
                            {notes.items.map(n => (
                                <li key={n.id}>
                                    <button className={n.read ? '' : 'is-unread'}
                                            onClick={() => { if (!n.read) markRead([n.id]); setOpen(false); openDetail(n.item); }}>
                                        <span className={`bell-kind ${n.kind}`}>{n.kind === 'reminder' ? 'Reminder' : 'New'}</span>
                                        <strong>{n.title}</strong>
                                        <span className="bell-body">{n.body}</span>
                                        <span className="bell-time">{ago(n.created_at)}</span>
                                    </button>
                                </li>
                            ))}
                        </ul>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
}
