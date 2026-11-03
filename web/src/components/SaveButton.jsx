import { useEffect, useRef, useState } from 'react';
import { AnimatePresence, motion } from 'motion/react';
import { useRadar } from '../store.jsx';
import { IconCheck, IconChevron, IconPlus } from './Icons.jsx';

/** Track: reminders before the deadline. Uses the known deadline, or asks for one in the detail sheet. */
export function TrackButton({ item }) {
    const { saved, track, openDetail } = useRadar();
    const row = saved.get(item.id);
    const tracked = !!row?.deadline;
    return (
        <motion.button type="button" className={`track-btn ${tracked ? 'is-on' : ''}`} whileTap={{ scale: 0.97 }}
                       aria-pressed={tracked}
                       onClick={e => {
                           e.stopPropagation();
                           if (tracked || !item.deadline) openDetail(item);  // change or pick the date there
                           else track(item, item.deadline);
                       }}>
            {tracked ? 'Tracked' : 'Track'}
        </motion.button>
    );
}

// "+ Save" until saved, then an outlined "Saved" menu: track, applied, remove.
export default function SaveButton({ item }) {
    const { saved, save, setStatus, remove, openDetail } = useRadar();
    const row = saved.get(item.id);
    const [open, setOpen] = useState(false);
    const ref = useRef(null);

    useEffect(() => {
        if (!open) return;
        const close = e => { if (!ref.current?.contains(e.target)) setOpen(false); };
        const esc = e => { if (e.key === 'Escape') setOpen(false); };
        document.addEventListener('pointerdown', close);
        document.addEventListener('keydown', esc);
        return () => { document.removeEventListener('pointerdown', close); document.removeEventListener('keydown', esc); };
    }, [open]);

    const label = !row ? 'Save' : row.status === 'applied' ? 'Applied' : row.deadline ? 'Tracked' : 'Saved';

    return (
        <div className="save" ref={ref} onClick={e => e.stopPropagation()}>
            <motion.button
                layout
                type="button"
                className={row ? 'save-btn is-saved' : 'save-btn'}
                aria-haspopup={row ? 'menu' : undefined}
                aria-expanded={row ? open : undefined}
                onClick={() => (row ? setOpen(o => !o) : save(item))}
                whileTap={{ scale: 0.97 }}
            >
                <AnimatePresence mode="popLayout" initial={false}>
                    <motion.span key={label} className="save-label"
                                 initial={{ y: 12, opacity: 0 }} animate={{ y: 0, opacity: 1 }} exit={{ y: -12, opacity: 0 }}
                                 transition={{ duration: 0.18 }}>
                        {row ? null : <IconPlus />}{label}
                    </motion.span>
                </AnimatePresence>
                {row && <IconChevron className="save-chev" style={{ transform: open ? 'rotate(180deg)' : 'none' }} />}
            </motion.button>
            <AnimatePresence>
                {open && row && (
                    <motion.div className="menu" role="menu"
                                initial={{ opacity: 0, y: -6, scale: 0.98 }} animate={{ opacity: 1, y: 0, scale: 1 }}
                                exit={{ opacity: 0, y: -6, scale: 0.98 }} transition={{ duration: 0.16 }}>
                        <button role="menuitem" onClick={() => { setOpen(false); openDetail(item); }}>
                            {row.deadline ? 'Change deadline' : 'Track deadline'}
                        </button>
                        <button role="menuitem" onClick={() => { setOpen(false); setStatus(item, row.status === 'applied' ? 'saved' : 'applied'); }}>
                            {row.status === 'applied' ? 'Move back to saved' : <>Mark as applied <IconCheck /></>}
                        </button>
                        <button role="menuitem" className="danger" onClick={() => { setOpen(false); remove(item); }}>Remove</button>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
}
