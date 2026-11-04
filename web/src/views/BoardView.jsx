import { useState } from 'react';
import { AnimatePresence, motion } from 'motion/react';
import { daysUntil } from '../api.js';
import { Logo } from '../components/Cover.jsx';
import { IconLeft, IconRight } from '../components/Icons.jsx';
import { useRadar } from '../store.jsx';

const COLUMNS = [['saved', 'Saved'], ['applied', 'Applied'], ['done', 'Done']];

export default function BoardView() {
    const { saved, setStatus, openDetail } = useRadar();
    const [tab, setTab] = useState('saved');
    const [over, setOver] = useState(null);

    const rows = [...saved.values()].map(r => ({ ...r, savedId: r.id, id: r.item_id, deadline: r.deadline || r.item_deadline }));

    const drop = (e, status) => {
        e.preventDefault();
        setOver(null);
        const row = rows.find(r => r.id === Number(e.dataTransfer.getData('text/plain')));
        if (row && row.status !== status) setStatus(row, status);
    };

    return (
        <div className="page">
            <div className="board-tabs pillars" role="tablist" aria-label="Board columns">
                {COLUMNS.map(([id, label]) => (
                    <button key={id} role="tab" aria-selected={tab === id} aria-pressed={tab === id} onClick={() => setTab(id)}>
                        {tab === id && <motion.span className="pillar-hl" layoutId="board-hl" transition={{ type: 'spring', stiffness: 420, damping: 34 }} />}
                        <span>{label} {rows.filter(r => (r.status || 'saved') === id).length}</span>
                    </button>
                ))}
            </div>
            <div className="board">
                {COLUMNS.map(([status, label], idx) => {
                    const list = rows.filter(r => (r.status || 'saved') === status);
                    return (
                        <section key={status} className={`column panel ${tab === status ? 'is-active' : ''} ${over === status ? 'is-over' : ''}`}
                                 onDragOver={e => { e.preventDefault(); setOver(status); }} onDragLeave={() => setOver(null)}
                                 onDrop={e => drop(e, status)} aria-label={label}>
                            <header><h2><i className={`dot ${status}`} />{label}</h2><span className="count">{list.length}</span></header>
                            <motion.div className="column-list" layout>
                                <AnimatePresence>
                                    {list.map(r => {
                                        const d = daysUntil(r.deadline);
                                        return (
                                            <motion.article key={r.id} layout layoutId={`k-${r.id}`} className="kcard" draggable
                                                            initial={{ opacity: 0, scale: 0.96 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0, scale: 0.96 }}
                                                            onDragStart={e => e.dataTransfer.setData('text/plain', String(r.id))}
                                                            onClick={() => openDetail(r)}>
                                                <div className="kcard-top">
                                                    <Logo item={r} size={36} />
                                                    <div>
                                                        <strong>{r.title}</strong>
                                                        <span>{r.organization || r.source}</span>
                                                    </div>
                                                </div>
                                                <div className="kcard-foot">
                                                    {d !== null && (
                                                        <span className={`tag ${d < 0 ? '' : d <= 3 ? 'is-urgent' : ''}`}>
                                                            {d < 0 ? 'Closed' : d === 0 ? 'Due today' : `${d}d left`}
                                                        </span>
                                                    )}
                                                    <span className="spacer" />
                                                    {idx > 0 && (
                                                        <button className="icon-btn" aria-label={`Move to ${COLUMNS[idx - 1][1]}`}
                                                                onClick={e => { e.stopPropagation(); setStatus(r, COLUMNS[idx - 1][0]); }}><IconLeft /></button>
                                                    )}
                                                    {idx < 2 && (
                                                        <button className="icon-btn" aria-label={`Move to ${COLUMNS[idx + 1][1]}`}
                                                                onClick={e => { e.stopPropagation(); setStatus(r, COLUMNS[idx + 1][0]); }}><IconRight /></button>
                                                    )}
                                                </div>
                                            </motion.article>
                                        );
                                    })}
                                </AnimatePresence>
                                {list.length === 0 && (
                                    <p className="column-empty">
                                        {status === 'saved' ? 'Save opportunities from the feed and they land here.'
                                            : status === 'applied' ? 'Drag a card here once you have applied.' : 'Finished ones go here.'}
                                    </p>
                                )}
                            </motion.div>
                        </section>
                    );
                })}
            </div>
        </div>
    );
}
