import { Suspense, lazy, useEffect, useRef, useState } from 'react';
import { AnimatePresence, motion } from 'motion/react';
import { Toasts } from './components/Controls.jsx';
import DetailSheet from './components/DetailSheet.jsx';
import Bell from './components/Bell.jsx';
import Login from './components/Login.jsx';
import Palette from './components/Palette.jsx';
import { NavIcon, IconMenu, IconScan, IconSearch, IconSettings, RadarMark } from './components/Icons.jsx';
import { write } from './api.js';
import { useLive, useRadar } from './store.jsx';
import HomeView from './views/HomeView.jsx';
import SimpleView from './views/SimpleView.jsx';

const MapView = lazy(() => import('./views/MapView.jsx'));
const CalendarView = lazy(() => import('./views/CalendarView.jsx'));
const BoardView = lazy(() => import('./views/BoardView.jsx'));
const SettingsView = lazy(() => import('./views/SettingsView.jsx'));

export const ROUTES = [
    { id: 'home', label: 'Home', key: 'h' },
    { id: 'feed', label: 'Feed', key: 'f' },
    { id: 'map', label: 'Map', key: 'm' },
    { id: 'calendar', label: 'Calendar', key: 'c' },
    { id: 'board', label: 'Board', key: 'b' },
    { id: 'settings', label: 'Settings', key: 's' },
];

const routeFromHash = () => {
    const r = location.hash.slice(1);
    return ROUTES.some(x => x.id === r) ? r : 'home';
};

export default function App() {
    const { locked, scan, saved } = useRadar();
    const { stats } = useLive();
    const [route, setRoute] = useState(routeFromHash);
    const [filters, setFilters] = useState({ pillar: 'opps', sort: 'latest', q: '', loc: '' });

    const [chromeIn, setChromeIn] = useState(route !== 'home');
    const [paletteOpen, setPaletteOpen] = useState(false);

    const [pinned, setPinned] = useState(() => { try { return localStorage.getItem('radar_side') !== 'folded'; } catch { return true; } });
    const [roomy, setRoomy] = useState(() => innerWidth > 1020);
    const [peek, setPeek] = useState(false);
    const peekTimer = useRef(0);
    useEffect(() => {
        const onResize = () => setRoomy(innerWidth > 1020);
        addEventListener('resize', onResize);
        return () => removeEventListener('resize', onResize);
    }, []);
    const folded = !pinned || !roomy;
    const togglePin = () => {
        if (!roomy) { setPeek(p => !p); return; }
        const next = !pinned;
        setPinned(next);
        setPeek(false);
        write('radar_side', next ? null : 'folded');
    };
    const onSideEnter = () => { clearTimeout(peekTimer.current); if (folded) peekTimer.current = setTimeout(() => setPeek(true), 120); };
    const onSideLeave = () => { clearTimeout(peekTimer.current); setPeek(false); };
    const wordmarkRef = useRef(null);

    const go = (r, nextFilters) => {
        if (nextFilters) setFilters(f => ({ ...f, ...nextFilters }));
        if (r !== route) {
            history.pushState(null, '', `#${r}`);
            setRoute(r);
            scrollTo(0, 0);
        }
        if (r !== 'home') setChromeIn(true);
    };

    useEffect(() => {
        const onHash = () => setRoute(routeFromHash());
        let pendingG = 0;
        const onKey = e => {
            if (e.target.closest?.('input, textarea, select') || e.altKey) return;
            if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') { e.preventDefault(); setPaletteOpen(true); return; }
            if (e.ctrlKey || e.metaKey) return;
            if (e.key === '/') { e.preventDefault(); setPaletteOpen(true); return; }
            if (e.key === 'g') { pendingG = Date.now(); return; }
            if (Date.now() - pendingG < 900) {
                const r = ROUTES.find(x => x.key === e.key.toLowerCase());
                if (r) go(r.id);
                pendingG = 0;
            }
        };
        addEventListener('popstate', onHash);
        addEventListener('keydown', onKey);
        return () => { removeEventListener('popstate', onHash); removeEventListener('keydown', onKey); };
    });

    useEffect(() => {
        document.title = route === 'home' ? 'Radar' : `${ROUTES.find(r => r.id === route).label} | Radar`;
        document.body.dataset.view = route;
    }, [route]);

    if (locked) return <Login />;

    const boardCount = [...saved.values()].filter(r => r.status !== 'done').length;
    const counts = { feed: stats ? (stats.pillars?.jobs || 0) + (stats.pillars?.events || 0) : 0, board: boardCount };

    return (
        <div className={`shell ${folded ? 'is-folded' : ''}`}>
            <motion.aside className={`side ${folded && !peek ? 'is-narrow' : ''} ${folded && peek ? 'is-peek' : ''}`}
                          aria-label="Main navigation" onMouseEnter={onSideEnter} onMouseLeave={onSideLeave}
                          initial={false} animate={{ opacity: chromeIn ? 1 : 0 }}
                          transition={{ duration: 0.6, ease: [0.2, 0.8, 0.2, 1] }}>
                <div className="side-top">
                    <button className="side-toggle" onClick={togglePin} aria-label={folded ? 'Keep the menu open' : 'Fold the menu'}
                            aria-expanded={!folded} title={folded ? 'Keep the menu open' : 'Fold the menu'}><IconMenu /></button>
                    <a className="wordmark" href="#home" ref={wordmarkRef} onClick={e => { e.preventDefault(); go('home'); }}>
                        <RadarMark size={26} /><span>Radar</span>
                    </a>
                </div>
                <nav className="side-nav">
                    {ROUTES.map(r => (
                        <a key={r.id} href={`#${r.id}`} aria-current={route === r.id ? 'page' : undefined}
                           onClick={e => { e.preventDefault(); go(r.id); }} title={`${r.label} (g ${r.key})`}>
                            {route === r.id && <motion.span className="side-hl" layoutId="side-hl"
                                                            transition={{ type: 'spring', stiffness: 420, damping: 36 }} />}
                            <NavIcon id={r.id} /><span className="side-label">{r.label}</span>
                            {counts[r.id] ? <span className="side-count">{counts[r.id]}</span> : null}
                        </a>
                    ))}
                </nav>
                <div className="side-foot">
                    <div className={`scan-status ${stats?.scanning ? 'is-scanning' : ''}`}>
                        <RadarMark size={30} />
                        <div>
                            <strong>{stats?.scanning ? 'Scanning' : 'Radar idle'}</strong>
                            <span>{stats ? `${stats.sources_active} of ${stats.sources_total} sources live` : ' '}</span>
                        </div>
                    </div>
                    <button className="btn-outline" onClick={scan} disabled={stats?.scanning} aria-label="Scan now"><IconScan /><span className="side-label">Scan now</span></button>
                    <div className="legal"><a href="/terms.html">Terms</a><a href="/privacy.html">Privacy</a></div>
                </div>
            </motion.aside>

            <motion.header className="top" initial={false}
                           animate={{ opacity: chromeIn ? 1 : 0 }} transition={{ duration: 0.6 }}
                           aria-hidden={!chromeIn}>
                <a className="wordmark top-brand" href="#home" onClick={e => { e.preventDefault(); go('home'); }}>
                    <RadarMark size={26} /><span>Radar</span>
                </a>
                <h1 className="top-title">{route === 'home' ? '' : ROUTES.find(r => r.id === route).label}</h1>
                <button className="search-trigger" onClick={() => setPaletteOpen(true)} aria-label="Search and commands (Ctrl K)">
                    <IconSearch /><span>Search or jump to</span><kbd>Ctrl K</kbd>
                </button>
                <Bell />
                <button className={`icon-btn ${stats?.scanning ? 'is-on' : ''}`} onClick={scan} aria-label="Scan now"><IconScan /></button>
                <a className="icon-btn top-settings" href="#settings" aria-label="Settings" onClick={e => { e.preventDefault(); go('settings'); }}><IconSettings /></a>
            </motion.header>

            <main id="main" className={`main main-${route}`}>
                <AnimatePresence mode="wait">

                    <motion.div key={route} className="route"
                                initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                                transition={{ duration: 0.25 }}>
                        <Suspense fallback={<div className="view-loading">Loading</div>}>
                            {route === 'home' && <HomeView go={go} wordmarkRef={wordmarkRef} onHandoff={() => setChromeIn(true)} />}
                            {route === 'feed' && <SimpleView filters={filters} setFilters={setFilters} />}
                            {route === 'map' && <MapView filters={filters} setFilters={setFilters} />}
                            {route === 'calendar' && <CalendarView />}
                            {route === 'board' && <BoardView />}
                            {route === 'settings' && <SettingsView />}
                        </Suspense>
                    </motion.div>
                </AnimatePresence>
            </main>

            <nav className="tabbar" aria-label="Main navigation">
                {ROUTES.filter(r => r.id !== 'settings').map(r => (
                    <a key={r.id} href={`#${r.id}`} aria-current={route === r.id ? 'page' : undefined}
                       onClick={e => { e.preventDefault(); go(r.id); }}>
                        <NavIcon id={r.id} /><span>{r.label}</span>
                    </a>
                ))}
            </nav>

            <DetailSheet />
            <Palette open={paletteOpen} onClose={() => setPaletteOpen(false)} go={go} />
            <Toasts />
        </div>
    );
}
