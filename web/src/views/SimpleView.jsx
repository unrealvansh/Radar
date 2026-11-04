import { useCallback, useEffect, useRef, useState } from 'react';
import { motion, useScroll, useSpring } from 'motion/react';
import { listItems } from '../api.js';
import { FilterBar } from '../components/Controls.jsx';
import OppCard from '../components/OppCard.jsx';
import { useRadar } from '../store.jsx';

const PAGE = 24;

export default function SimpleView({ filters, setFilters }) {
    const { home } = useRadar();
    const [items, setItems] = useState(null);
    const [done, setDone] = useState(false);
    const loading = useRef(false);
    const sentinel = useRef(null);
    const { scrollYProgress } = useScroll();
    const progress = useSpring(scrollYProgress, { stiffness: 200, damping: 30 });

    const loadMore = useCallback(async (reset = false) => {
        if (loading.current) return;
        loading.current = true;
        try {
            const offset = reset ? 0 : (items?.length || 0);
            const page = await listItems({ ...filters, limit: PAGE, offset }, home);
            setItems(prev => (reset ? page : [...(prev || []), ...page]));
            setDone(page.length < PAGE);
        } catch {
            if (reset) setItems([]);
        } finally {
            loading.current = false;
        }
    }, [filters, home, items]);

    useEffect(() => { setItems(null); setDone(false); loadMore(true); }, [filters]);

    useEffect(() => {
        if (!sentinel.current || done) return;
        const io = new IntersectionObserver(([e]) => e.isIntersecting && items && loadMore(), { rootMargin: '600px' });
        io.observe(sentinel.current);
        return () => io.disconnect();
    }, [items, done, loadMore]);

    return (
        <>
            <motion.div className="scroll-progress" style={{ scaleX: progress }} aria-hidden="true" />
            <section className="simple">
                <div className="simple-head">
                    <h1>Opportunities for you</h1>
                    <p>{items ? `${items.length}${done ? '' : '+'} open right now` : 'Loading'}</p>
                </div>
                <FilterBar filters={filters} setFilters={setFilters} />
                {items === null ? (
                    <div className="oc-grid">{Array.from({ length: 8 }, (_, i) => <Skeleton key={i} />)}</div>
                ) : items.length === 0 ? (
                    <div className="empty">
                        <strong>Nothing matches these filters</strong>
                        <span>Clear a filter, or run a scan from the Radar app.</span>
                    </div>
                ) : (
                    <div className="oc-grid">
                        {items.map((it, i) => <OppCard key={it.id} item={it} index={i} />)}
                    </div>
                )}
                <div ref={sentinel} className="sentinel" />
                {done && items?.length > 0 && <p className="end">That's all {items.length}.</p>}
            </section>
        </>
    );
}

function Skeleton() {
    return (
        <div className="oc oc-skel" aria-hidden="true">
            <div className="oc-banner" />
            <div className="oc-logo"><div className="logo" /></div>
            <i style={{ width: '70%' }} /><i style={{ width: '45%' }} /><i style={{ width: '55%' }} />
            <i className="skel-btn" />
        </div>
    );
}
