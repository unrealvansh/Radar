import { useEffect, useState } from 'react';
import { motion } from 'motion/react';
import { listItems } from '../api.js';
import OppCard from '../components/OppCard.jsx';
import { useLive, useRadar } from '../store.jsx';
import AuraView from './AuraView.jsx';

export default function HomeView({ go, wordmarkRef, onHandoff }) {
    const { home, settings, version } = useRadar();
    const { stats } = useLive();
    const [rows, setRows] = useState({ closing: null, near: null, picks: null, latest: null });

    useEffect(() => {
        const q = (params, limit) => listItems({ pillar: 'opps', limit, ...params }, home).catch(() => []);
        Promise.all([
            q({ sort: 'closing' }, 10),
            home ? q({ loc: 'near' }, 10) : Promise.resolve(null),
            q({ sort: 'picks' }, 6),
            q({ sort: 'latest' }, 6),
        ]).then(([closing, near, picks, latest]) => setRows({ closing, near, picks, latest }));
    }, [home, version]);

    const hour = new Date().getHours();
    const part = hour < 12 ? 'Good morning' : hour < 17 ? 'Good afternoon' : 'Good evening';
    const name = settings?.display_name;

    return (
        <div className="home">
            <AuraView wordmarkRef={wordmarkRef} onHandoff={onHandoff} go={go} />

            <div className="home-body">
                <Reveal className="home-greet">
                    <div>
                        <span className="home-date">{new Date().toLocaleDateString('en-IN', { weekday: 'long', day: 'numeric', month: 'long' })}</span>
                        <h2>{name ? `${part}, ${name}` : part}</h2>
                    </div>
                    <div className="readout">
                        <Stat n={stats?.new_today} label="new today" onClick={() => go('feed', { sort: 'latest' })} accent />
                        <Stat n={stats?.closing_week} label="saved, due this week" onClick={() => go('board')} />
                        <Stat n={stats?.tracked} label="tracked with reminders" onClick={() => go('calendar')} />
                        <Stat n={stats?.applied} label="applied" onClick={() => go('board')} />
                    </div>
                </Reveal>

                <Section title="Closing soon" action={() => go('feed', { sort: 'closing' })} items={rows.closing} rail
                         empty="Nothing with a known deadline yet." />
                {home ? (
                    <Section title={`Near ${home.city}`} sub={`within ${home.radius} km`} action={() => go('feed', { loc: 'near' })}
                             items={rows.near} rail empty={`Nothing within ${home.radius} km yet. Try a bigger radius in Settings.`} />
                ) : (
                    <Reveal className="home-nudge">
                        <strong>See what's happening near you</strong>
                        <span>Set your city once and Radar shows nearby hackathons, events and jobs first.</span>
                        <button className="btn-outline" onClick={() => go('settings')}>Set my city</button>
                    </Reveal>
                )}
                <Section title="Picks for you" sub="ranked by your interests" action={() => go('feed', { sort: 'picks' })} items={rows.picks}
                         empty="Add interests in Settings to get ranked picks." />
                <Section title="Just in" action={() => go('feed', { sort: 'latest' })} items={rows.latest} empty="Run a scan to fetch opportunities." />
                {stats && (
                    <p className="coverage-line">
                        Watching <b>{stats.sources_active}</b> of <b>{stats.sources_total}</b> sources right now:
                        {' '}<b>{stats.pillars?.events || 0}</b> events, <b>{stats.pillars?.jobs || 0}</b> jobs and <b>{stats.pillars?.news || 0}</b> news stories.
                    </p>
                )}
            </div>
        </div>
    );
}

function Reveal({ children, className }) {
    return (
        <motion.div className={className} initial={{ opacity: 0, y: 30 }} whileInView={{ opacity: 1, y: 0 }}
                    viewport={{ once: true, margin: '0px 0px -60px 0px' }} transition={{ duration: 0.6, ease: [0.2, 0.8, 0.2, 1] }}>
            {children}
        </motion.div>
    );
}

function Stat({ n, label, onClick, accent }) {
    return (
        <button className={accent ? 'is-accent' : ''} onClick={onClick}>
            <b>{n ?? 0}</b>{label}
        </button>
    );
}

function Section({ title, sub, action, items, rail, empty }) {
    return (
        <section className="home-section">
            <Reveal className="home-section-head">
                <h2>{title}{sub && <small>{sub}</small>}</h2>
                <button className="link-btn" onClick={action}>View all</button>
            </Reveal>
            {items === null ? (
                <div className={rail ? 'rail' : 'oc-grid'}>{[0, 1, 2].map(i => <div key={i} className="oc oc-skel" />)}</div>
            ) : items.length === 0 ? (
                <div className="empty"><span>{empty}</span></div>
            ) : (
                <div className={rail ? 'rail' : 'oc-grid'}>
                    {items.map((it, i) => <OppCard key={it.id} item={it} index={i} />)}
                </div>
            )}
        </section>
    );
}
