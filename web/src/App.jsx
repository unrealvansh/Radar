import { Suspense, lazy, useEffect, useRef, useState } from 'react';
import { AnimatePresence, motion } from 'motion/react';
import { Toasts, VIEWS, ViewSwitch } from './components/Controls.jsx';
import DetailSheet from './components/DetailSheet.jsx';
import { IconBack, RadarMark } from './components/Icons.jsx';
import SimpleView from './views/SimpleView.jsx';

// Aura and Map are only downloaded when opened
const AuraView = lazy(() => import('./views/AuraView.jsx'));
const MapView = lazy(() => import('./views/MapView.jsx'));

const viewFromHash = () => {
    const v = location.hash.slice(1);
    return VIEWS.some(x => x.id === v) ? v : 'simple';
};

export default function App() {
    const [view, setView] = useState(viewFromHash);
    const [filters, setFilters] = useState({ pillar: 'opps', sort: 'latest', q: '', loc: '' });
    // Aura hides the header until its entrance hands over; other views show it at once
    const [chromeIn, setChromeIn] = useState(view !== 'aura');
    const wordmarkRef = useRef(null);

    const go = v => {
        if (v === view) return;
        history.replaceState(null, '', `#${v}`);
        if (v !== 'aura') setChromeIn(true);
        setView(v);
    };

    useEffect(() => {
        const onHash = () => setView(viewFromHash());
        const onKey = e => {
            if (e.target.closest?.('input, textarea, select') || e.metaKey || e.ctrlKey || e.altKey) return;
            const v = VIEWS.find(x => x.key === e.key);
            if (v) go(v.id);
        };
        addEventListener('hashchange', onHash);
        addEventListener('keydown', onKey);
        return () => { removeEventListener('hashchange', onHash); removeEventListener('keydown', onKey); };
    });

    useEffect(() => {
        document.title = `${VIEWS.find(v => v.id === view).label} view | Radar`;
        document.body.dataset.view = view;
    }, [view]);

    return (
        <>
            <motion.header className="top"
                           initial={false}
                           animate={{ opacity: chromeIn ? 1 : 0 }}
                           transition={{ duration: 0.6, ease: [0.2, 0.8, 0.2, 1] }}
                           aria-hidden={!chromeIn}>
                <a className="back" href="/" aria-label="Back to the Radar app"><IconBack /></a>
                <a className="wordmark" href="#simple" ref={wordmarkRef} onClick={e => { e.preventDefault(); go('simple'); }}>
                    <RadarMark size={26} /><span>Radar</span>
                </a>
                <nav className="sitenav" aria-label="Radar">
                    {[['dashboard', 'Dashboard'], ['calendar', 'Calendar'], ['board', 'Board'], ['settings', 'Settings']].map(([id, label]) => (
                        <a key={id} href={`/#${id}`}>{label}</a>
                    ))}
                </nav>
                <ViewSwitch view={view} onChange={go} />
            </motion.header>

            <main id="main">
                <AnimatePresence mode="wait">
                    <motion.div key={view} className={`view view-${view}`}
                                initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                                transition={{ duration: 0.25 }}>
                        <Suspense fallback={<div className="view-loading">Loading</div>}>
                            {view === 'simple' && (
                                <SimpleView filters={filters} setFilters={setFilters} />
                            )}
                            {view === 'aura' && (
                                <AuraView filters={filters} setFilters={setFilters} wordmarkRef={wordmarkRef}
                                          onHandoff={() => setChromeIn(true)} />
                            )}
                            {view === 'map' && (
                                <MapView filters={filters} setFilters={setFilters} />
                            )}
                        </Suspense>
                    </motion.div>
                </AnimatePresence>
            </main>

            <DetailSheet />
            <Toasts />
        </>
    );
}
