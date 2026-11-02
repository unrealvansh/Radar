import { useEffect, useRef, useState } from 'react';
import { AnimatePresence, motion } from 'motion/react';
import { TYPE_LABEL, daysUntil, fmtDate, whereText } from '../api.js';
import { useRadar } from '../store.jsx';
import Cover from './Cover.jsx';
import SaveButton from './SaveButton.jsx';
import { IconOut, IconX } from './Icons.jsx';

// Side panel on desktop, bottom sheet on phones. The card's cover morphs into it (layoutId).
export default function DetailSheet() {
    const { detail: it, openDetail } = useRadar();
    const close = () => openDetail(null);
    const panelRef = useRef(null);

    useEffect(() => {
        if (!it) return;
        const last = document.activeElement;
        panelRef.current?.focus();
        const onKey = e => { if (e.key === 'Escape') close(); };
        document.addEventListener('keydown', onKey);
        return () => { document.removeEventListener('keydown', onKey); last?.focus?.(); };
    }, [it?.id]);  // eslint-disable-line react-hooks/exhaustive-deps

    return (
        <AnimatePresence>
            {it && (
                <>
                    <motion.div key="scrim" className="scrim" onClick={close}
                                initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} />
                    <motion.aside key="sheet" className="sheet" role="dialog" aria-modal="true" aria-labelledby="sheet-title"
                                  ref={panelRef} tabIndex={-1}
                                  initial={{ opacity: 0, y: 40 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: 40 }}
                                  transition={{ type: 'spring', stiffness: 260, damping: 30 }}
                                  drag={matchMedia('(max-width: 640px)').matches ? 'y' : false} dragConstraints={{ top: 0, bottom: 0 }} dragElastic={{ top: 0, bottom: 0.6 }}
                                  onDragEnd={(e, info) => { if (info.offset.y > 120) close(); }}>
                        <div className="sheet-handle" aria-hidden="true" />
                        <motion.div className="sheet-cover" layoutId={`cover-${it.id}`}>
                            <Cover item={it} />
                        </motion.div>
                        <button className="icon-btn sheet-close" onClick={close} aria-label="Close details"><IconX /></button>
                        <div className="sheet-body">
                            <div className="oc-pills">
                                <span className="pill">{TYPE_LABEL[it.pillar]}</span>
                                <span className="pill">{it.source}</span>
                            </div>
                            <h2 id="sheet-title">{it.title}</h2>
                            {it.organization && <p className="sheet-org">{it.organization}</p>}
                            <dl className="facts">
                                {it.deadline && <Fact k="Deadline" v={`${fmtDate(it.deadline)}${daysLeft(it.deadline)}`} />}
                                {it.starts_at && <Fact k="Starts" v={fmtDate(it.starts_at)} />}
                                {whereText(it) && <Fact k="Where" v={whereText(it)} />}
                                {it.extra_info && <Fact k="Details" v={it.extra_info} />}
                                {it.posted_at && <Fact k="Posted" v={fmtDate(it.posted_at)} />}
                            </dl>
                            {it.pillar !== 'news' && <TrackBox item={it} />}
                        </div>
                        <div className="sheet-foot">
                            <a className="btn-primary" href={it.url} target="_blank" rel="noopener">
                                {it.pillar === 'jobs' ? 'Open and apply' : it.pillar === 'news' ? 'Read article' : 'Open event page'}
                                <IconOut />
                            </a>
                            <SaveButton item={it} />
                        </div>
                    </motion.aside>
                </>
            )}
        </AnimatePresence>
    );
}

function daysLeft(iso) {
    const d = daysUntil(iso);
    if (d === null) return '';
    return d < 0 ? ', closed' : d === 0 ? ', closes today' : `, ${d} day${d === 1 ? '' : 's'} left`;
}

const Fact = ({ k, v }) => <div className="fact"><dt>{k}</dt><dd>{v}</dd></div>;

function TrackBox({ item }) {
    const { saved, track } = useRadar();
    const row = saved.get(item.id);
    const [date, setDate] = useState(row?.deadline || item.deadline || '');
    return (
        <div className="track">
            <label htmlFor="track-date">Deadline reminder</label>
            <div className="track-row">
                <input id="track-date" type="date" value={date} onChange={e => setDate(e.target.value)} />
                <button className="btn-outline" onClick={() => track(item, date)}>{row?.deadline ? 'Update' : 'Track'}</button>
            </div>
            <p>A push notification arrives 2 days before and on the day.</p>
        </div>
    );
}
