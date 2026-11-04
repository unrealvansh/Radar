import { useEffect, useMemo, useState } from 'react';
import { AnimatePresence, motion } from 'motion/react';
import { TYPE_LABEL, api, whenText } from '../api.js';
import { IconLeft, IconRight } from '../components/Icons.jsx';
import { useRadar } from '../store.jsx';

const iso = d => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;

export default function CalendarView() {
    const { openDetail, saved } = useRadar();
    const today = iso(new Date());
    const [month, setMonth] = useState(() => { const d = new Date(); return new Date(d.getFullYear(), d.getMonth(), 1); });
    const [entries, setEntries] = useState(null);
    const [selected, setSelected] = useState(today);
    const [dir, setDir] = useState(0);
    const key = `${month.getFullYear()}-${String(month.getMonth() + 1).padStart(2, '0')}`;

    useEffect(() => {
        setEntries(null);
        api('/api/calendar?month=' + key).then(r => setEntries(r.entries || [])).catch(() => setEntries([]));
    }, [key, saved]);

    const byDay = useMemo(() => {
        const m = {};
        (entries || []).forEach(e => (m[e.date?.slice(0, 10)] ||= []).push(e));
        return m;
    }, [entries]);

    const move = n => { setDir(n); setMonth(m => new Date(m.getFullYear(), m.getMonth() + n, 1)); };
    const offset = (month.getDay() + 6) % 7;
    const days = new Date(month.getFullYear(), month.getMonth() + 1, 0).getDate();
    const cells = [...Array(offset).fill(null), ...Array.from({ length: days }, (_, i) => new Date(month.getFullYear(), month.getMonth(), i + 1))];
    const list = byDay[selected] || [];

    return (
        <div className="page cal-page">
            <div className="cal panel">
                <div className="cal-head">
                    <AnimatePresence mode="wait" initial={false}>
                        <motion.h2 key={key} initial={{ opacity: 0, x: dir * 16 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: dir * -16 }}
                                   transition={{ duration: 0.2 }}>
                            {month.toLocaleDateString('en-IN', { month: 'long', year: 'numeric' })}
                        </motion.h2>
                    </AnimatePresence>
                    <button className="btn-outline" onClick={() => { setMonth(new Date(new Date().getFullYear(), new Date().getMonth(), 1)); setSelected(today); }}>Today</button>
                    <button className="icon-btn" onClick={() => move(-1)} aria-label="Previous month"><IconLeft /></button>
                    <button className="icon-btn" onClick={() => move(1)} aria-label="Next month"><IconRight /></button>
                </div>
                <div className="cal-grid" role="grid" aria-label="Month">
                    {['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'].map(d => <div key={d} className="cal-dow" aria-hidden="true">{d}</div>)}
                    {cells.map((d, i) => {
                        if (!d) return <div key={`x${i}`} className="cal-day out" aria-hidden="true" />;
                        const k = iso(d);
                        const dayList = byDay[k] || [];
                        const tracked = dayList.filter(e => e.kind === 'tracked');
                        const lead = tracked[0] || dayList[0];
                        return (
                            <button key={k} className={`cal-day ${k === today ? 'is-today' : ''}`} aria-pressed={k === selected}
                                    onClick={() => setSelected(k)}
                                    aria-label={`${d.toLocaleDateString('en-IN', { day: 'numeric', month: 'long' })}: ${dayList.length} item${dayList.length === 1 ? '' : 's'}`}>
                                <span className="cal-num">{d.getDate()}</span>
                                <span className="cal-marks">
                                    {dayList.slice(0, 4).map((e, j) => <i key={j} className={e.kind} />)}
                                    {dayList.length > 4 && <small>+{dayList.length - 4}</small>}
                                </span>
                                {lead && <span className="cal-label">{lead.title}</span>}
                            </button>
                        );
                    })}
                </div>
                <div className="legend"><span><i className="tracked" />Your tracked deadlines</span><span><i />Upcoming events</span></div>
            </div>

            <aside className="cal-side panel">
                <h2>{new Date(selected + 'T00:00:00').toLocaleDateString('en-IN', { weekday: 'long', day: 'numeric', month: 'long' })}</h2>
                {entries === null ? <p className="muted">Loading</p> : list.length === 0 ? (
                    <p className="muted">Nothing on this day.</p>
                ) : (
                    <ul className="cal-list">
                        {list.map((e, i) => (
                            <motion.li key={`${e.id}-${e.kind}`} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.04 }}>
                                <button onClick={() => openDetail(e)}>
                                    <span className={`cal-kind ${e.kind}`}>{e.kind === 'tracked' ? 'Deadline' : TYPE_LABEL[e.pillar]}</span>
                                    <strong>{e.title}</strong>
                                    <span className="muted">{[e.organization, whenText(e)].filter(Boolean).join(', ')}</span>
                                </button>
                            </motion.li>
                        ))}
                    </ul>
                )}
            </aside>
        </div>
    );
}
