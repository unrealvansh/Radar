import { useEffect, useMemo, useRef, useState } from 'react';
import { AnimatePresence, motion, useMotionValue, useMotionValueEvent, useSpring, useTransform } from 'motion/react';
import { daysUntil, listItems } from '../api.js';
import { FilterBar } from '../components/Controls.jsx';
import OppCard from '../components/OppCard.jsx';
import { useRadar } from '../store.jsx';
import { BOUNDS, inIndia, planeSize, project, statePaths } from './india.js';

// A dark dot-matrix India on a tilted plane: one dot per ~0.3 degrees, land dots brighter,
// dots near places with opportunities lit blue. City beacons stand up off the plane.
const PLANE = planeSize(1000);
const STEP = 0.3;                // degrees between dots
const TILT_OVERVIEW = 50;
const TILT_FOCUS = 34;
const SPRING = { stiffness: 70, damping: 20, mass: 1 };

// The grid and the state outlines never change: work them out once per visit
let GRID = null;
function grid() {
    if (GRID) return GRID;
    const dots = [];
    for (let lat = BOUNDS.north - 0.2; lat > BOUNDS.south + 0.1; lat -= STEP) {
        for (let lon = BOUNDS.west + 0.1; lon < BOUNDS.east; lon += STEP) {
            const p = project(lon, lat, PLANE);
            dots.push({ x: p.x, y: p.y, land: inIndia(lon, lat), r: Math.hypot(p.x - PLANE.w / 2, p.y - PLANE.h / 2) });
        }
    }
    GRID = { dots, borders: statePaths(PLANE) };
    return GRID;
}

export default function MapView({ filters, setFilters }) {
    const { home } = useRadar();
    const [items, setItems] = useState(null);
    const [selected, setSelected] = useState(null);   // city name, or 'online'
    const [hoverCity, setHoverCity] = useState(null);
    const viewRef = useRef(null);
    const planeRef = useRef(null);
    const canvasRef = useRef(null);

    useEffect(() => {
        // News has no place, so the map shows all opportunities instead
        const pillar = filters.pillar === 'news' ? 'opps' : filters.pillar;
        // "Online only" would leave the map empty, so the map always shows places
        const loc = filters.loc === 'online' ? '' : filters.loc;
        listItems({ ...filters, pillar, loc, limit: 600 }, home).then(setItems).catch(() => setItems([]));
    }, [filters, home]);

    const { cities, online } = useMemo(() => {
        const byCity = new Map();
        const online = [];
        for (const it of items || []) {
            if (it.mode === 'online' || it.mode === 'remote' || it.lat === null || it.lat === undefined) {
                if (it.mode === 'online' || it.mode === 'remote') online.push(it);
                continue;
            }
            const c = byCity.get(it.city) || { name: it.city, lat: it.lat, lon: it.lon, items: [], urgent: false };
            c.items.push(it);
            const d = daysUntil(it.deadline);
            if (d !== null && d >= 0 && d <= 3) c.urgent = true;
            byCity.set(it.city, c);
        }
        const list = [...byCity.values()].sort((a, b) => b.items.length - a.items.length);
        const soonest = it => it.deadline || it.starts_at || '9999';
        list.forEach(c => {
            Object.assign(c, project(c.lon, c.lat, PLANE));
            c.items.sort((a, b) => soonest(a).localeCompare(soonest(b)));
            c.lead = c.items[0];  // the beacon is labelled with this one
        });
        return { cities: list, online };
    }, [items]);

    // ---- camera: four springs ----
    const fitScale = () => {
        const el = viewRef.current;
        if (!el || !el.clientWidth || !el.clientHeight) return 0.6;
        // the tilted plane's near edge is enlarged by perspective, so leave room
        if (el.clientWidth < 700) return el.clientWidth / (PLANE.w * 0.8);  // phones: India fills the width (the plane's sea margins may crop)
        return Math.min(el.clientWidth / (PLANE.w * 1.15), el.clientHeight / (PLANE.h * 1.0));
    };
    const tiltT = useMotionValue(78), zoomT = useMotionValue(0.4), xT = useMotionValue(0), yT = useMotionValue(0);
    const tilt = useSpring(tiltT, SPRING), zoom = useSpring(zoomT, SPRING), x = useSpring(xT, SPRING), y = useSpring(yT, SPRING);
    const transform = useTransform([x, y, tilt, zoom], ([px, py, t, s]) =>
        `translate3d(${px}px, ${py}px, 0) rotateX(${t}deg) scale(${s})`);
    useMotionValueEvent(tilt, 'change', v => planeRef.current?.style.setProperty('--tilt', `${v}deg`));
    useMotionValueEvent(zoom, 'change', v => planeRef.current?.style.setProperty('--z', v.toFixed(3)));

    const overview = () => {
        const phone = (viewRef.current?.clientWidth || innerWidth) < 700;
        tiltT.set(phone ? 34 : TILT_OVERVIEW); zoomT.set(fitScale()); xT.set(0); yT.set(phone ? 10 : -fitScale() * 30);
    };
    const focus = c => {
        const s = Math.min(fitScale() * 2.6, 2.4);
        const t = TILT_FOCUS;
        tiltT.set(t); zoomT.set(s);
        xT.set(-(c.x - PLANE.w / 2) * s);
        yT.set(-(c.y - PLANE.h / 2) * s * Math.cos((t * Math.PI) / 180));
    };

    // Entrance: the plane swings down from steep to the overview while the dots are drawn
    const selectedRef = useRef(null);
    selectedRef.current = selected;
    useEffect(() => {
        overview();
        // Re-fit whenever the map's box changes size (first layout, window resize, rotation)
        const ro = new ResizeObserver(() => { if (!selectedRef.current) overview(); });
        ro.observe(viewRef.current);
        return () => ro.disconnect();
    }, []);  // eslint-disable-line react-hooks/exhaustive-deps

    const pick = name => {
        setSelected(name);
        const c = cities.find(x => x.name === name);
        if (c) focus(c); else overview();
    };
    const reset = () => { setSelected(null); overview(); };

    // ---- dots, redrawn when the cities change; revealed outward from the centre ----
    useEffect(() => {
        const canvas = canvasRef.current;
        const dpr = Math.min(2, devicePixelRatio || 1);
        canvas.width = PLANE.w * dpr;
        canvas.height = PLANE.h * dpr;
        const ctx = canvas.getContext('2d');
        ctx.scale(dpr, dpr);

        const { borders } = grid();
        // Dots near places with opportunities glow blue
        const dots = grid().dots.map(d => {
            let heat = 0;
            if (d.land) {
                for (const c of cities) {
                    const dist = Math.hypot(c.x - d.x, c.y - d.y);
                    const reach = 26 + Math.sqrt(c.items.length) * 14;
                    if (dist < reach) heat = Math.max(heat, 1 - dist / reach);
                }
            }
            return { ...d, heat };
        });
        const maxR = Math.hypot(PLANE.w / 2, PLANE.h / 2);
        const reduce = document.documentElement.classList.contains('reduce-motion');
        const strokeBorders = (alpha, glow) => {
            ctx.save();
            ctx.lineJoin = 'round';
            ctx.strokeStyle = `rgba(235, 240, 255, ${0.6 * alpha})`;
            ctx.lineWidth = 1.1;
            if (glow) { ctx.shadowColor = 'rgba(255, 255, 255, 0.85)'; ctx.shadowBlur = 7; }
            for (const pts of borders) {
                ctx.beginPath();
                ctx.moveTo(pts[0], pts[1]);
                for (let i = 2; i < pts.length; i += 2) ctx.lineTo(pts[i], pts[i + 1]);
                ctx.closePath();
                ctx.stroke();
            }
            ctx.restore();
        };
        const start = performance.now();
        let raf = 0;
        const draw = now => {
            const reveal = reduce ? 1 : Math.min(1, (now - start) / 1100);
            ctx.clearRect(0, 0, PLANE.w, PLANE.h);
            for (const d of dots) {
                if (d.r > reveal * maxR * 1.05) continue;
                if (!d.land) {
                    ctx.fillStyle = 'rgba(150, 160, 190, 0.06)';
                    ctx.fillRect(d.x - 0.7, d.y - 0.7, 1.4, 1.4);
                } else if (d.heat > 0) {
                    ctx.fillStyle = `rgba(70, 150, 255, ${0.3 + d.heat * 0.7})`;
                    const s = 2 + d.heat * 1.6;
                    ctx.fillRect(d.x - s / 2, d.y - s / 2, s, s);
                } else {
                    ctx.fillStyle = 'rgba(190, 198, 225, 0.32)';
                    ctx.fillRect(d.x - 1, d.y - 1, 2, 2);
                }
            }
            // State borders fade in with the dots; the glow (costly) is drawn once, on the last frame
            strokeBorders(reveal, reveal >= 1);
            if (reveal < 1) raf = requestAnimationFrame(draw);
        };
        raf = requestAnimationFrame(draw);
        return () => cancelAnimationFrame(raf);
    }, [cities]);

    // ---- drag to pan, wheel or pinch-free zoom ----
    const drag = useRef(null);
    const onPointerDown = e => {
        if (e.target.closest('.dm-pin')) return;
        drag.current = { x: e.clientX, y: e.clientY, sx: xT.get(), sy: yT.get(), moved: false };
    };
    const onPointerMove = e => {
        const d = drag.current;
        if (!d) return;
        if (Math.abs(e.clientX - d.x) + Math.abs(e.clientY - d.y) > 4) {
            d.moved = true;
            viewRef.current.setPointerCapture?.(e.pointerId);
        }
        xT.set(d.sx + (e.clientX - d.x));
        yT.set(d.sy + (e.clientY - d.y));
        x.jump(xT.get()); y.jump(yT.get());  // follow the finger exactly, springs only for flights
    };
    const onPointerUp = () => { drag.current = null; };
    useEffect(() => {
        const el = viewRef.current;
        const onWheel = e => {
            e.preventDefault();
            const s = Math.min(4, Math.max(fitScale() * 0.8, zoomT.get() * Math.exp(-e.deltaY * 0.0015)));
            const k = s / zoomT.get();
            zoomT.set(s); xT.set(xT.get() * k); yT.set(yT.get() * k);
        };
        el.addEventListener('wheel', onWheel, { passive: false });
        return () => el.removeEventListener('wheel', onWheel);
    }, []);  // eslint-disable-line react-hooks/exhaustive-deps

    useEffect(() => {
        const onKey = e => { if (e.key === 'Escape' && selected) reset(); };
        addEventListener('keydown', onKey);
        return () => removeEventListener('keydown', onKey);
    });

    const narrow = typeof innerWidth === 'number' && innerWidth < 760;  // fewer labels on phones
    const homePt = home ? project(home.lon, home.lat, PLANE) : null;
    const homeR = home ? (home.radius / 111 / (36.2 - 6.5)) * PLANE.h : 0;
    const max = Math.max(1, ...cities.map(c => c.items.length));
    const list = selected === 'online' ? online : cities.find(c => c.name === selected)?.items || [];

    return (
        <section className="mapview">
            <div className="dm-view" ref={viewRef}
                 onPointerDown={onPointerDown} onPointerMove={onPointerMove} onPointerUp={onPointerUp} onPointerCancel={onPointerUp}
                 aria-label="Map of India with opportunities by city">
                <motion.div className="dm-plane" ref={planeRef}
                            style={{ width: PLANE.w, height: PLANE.h, marginLeft: -PLANE.w / 2, marginTop: -PLANE.h / 2, transform,
                                     '--plane-h': `${PLANE.h}px` }}>
                    <canvas ref={canvasRef} className="dm-dots" style={{ width: PLANE.w, height: PLANE.h }} />
                    <div className="dm-frame" aria-hidden="true" />
                    <div className="dm-sweep" aria-hidden="true" />
                    {homePt && (
                        <div className="dm-home" aria-hidden="true"
                             style={{ left: homePt.x, top: homePt.y, width: homeR * 2, height: homeR * 2 }} />
                    )}
                    {cities.map((c, i) => {
                        const size = 8 + 14 * Math.sqrt(c.items.length / max);
                        const show = selected === c.name || hoverCity === c.name || i < (narrow ? 2 : 5);
                        const title = c.lead.title.length > 34 ? c.lead.title.slice(0, 32).trimEnd() + '...' : c.lead.title;
                        return (
                            <button key={c.name} className={`dm-pin ${c.urgent ? 'is-urgent' : ''} ${selected === c.name ? 'is-on' : ''}`}
                                    style={{ left: c.x, top: c.y, '--s': `${size}px`, '--h': `${18 + 50 * Math.sqrt(c.items.length / max)}px`,
                                             '--d': `${(i % 8) * 0.25}s` }}
                                    aria-label={`${c.lead.title} in ${c.name}${c.items.length > 1 ? `, and ${c.items.length - 1} more there` : ''}`}
                                    onPointerEnter={() => setHoverCity(c.name)} onPointerLeave={() => setHoverCity(null)}
                                    onFocus={() => setHoverCity(c.name)} onBlur={() => setHoverCity(null)}
                                    onClick={() => pick(c.name)}>
                                <span className="dm-base" />
                                <span className="dm-stand">
                                    <span className="dm-beam" />
                                    <span className={`dm-chip ${show ? 'is-shown' : ''}`}>
                                        <i />{title}{c.items.length > 1 && <b>+{c.items.length - 1}</b>}
                                        <em>{c.name}</em>
                                    </span>
                                </span>
                            </button>
                        );
                    })}
                </motion.div>
            </div>

            <a className="map-credit" href="https://github.com/datameet/maps" target="_blank" rel="noopener">
                Boundaries: Datameet, CC BY 4.0
            </a>
            <div className="map-top">
                <FilterBar filters={filters} setFilters={setFilters} hideSearch noNews />
            </div>

            <motion.div className="map-cities" initial={{ opacity: 0, x: -16 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.3 }}>
                <h1>{items === null ? 'Loading map' : `${cities.length} cities`}</h1>
                <ul>
                    {online.length > 0 && (
                        <li><button aria-pressed={selected === 'online'} onClick={() => pick('online')}>
                            <span>Online and remote</span><b>{online.length}</b></button></li>
                    )}
                    {cities.slice(0, 14).map(c => (
                        <li key={c.name}>
                            <button aria-pressed={selected === c.name} onClick={() => pick(c.name)}
                                    onPointerEnter={() => setHoverCity(c.name)} onPointerLeave={() => setHoverCity(null)}>
                                <span>{c.name}{c.urgent && <i className="dot-urgent" title="Something closes within 3 days" />}</span>
                                <b>{c.items.length}</b>
                            </button>
                        </li>
                    ))}
                </ul>
            </motion.div>

            <AnimatePresence>
                {selected && (
                    <motion.aside className="map-panel" key={selected}
                                  initial={{ opacity: 0, x: 40 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: 40 }}
                                  transition={{ type: 'spring', stiffness: 260, damping: 30 }}>
                        <div className="map-panel-head">
                            <h2>{selected === 'online' ? 'Online and remote' : selected}</h2>
                            <span>{list.length} open</span>
                            <button className="btn-outline" onClick={reset}>Show all of India</button>
                        </div>
                        <div className="map-panel-list">
                            {list.map((it, i) => <OppCard key={it.id} item={it} index={i} compact />)}
                        </div>
                    </motion.aside>
                )}
            </AnimatePresence>
        </section>
    );
}
