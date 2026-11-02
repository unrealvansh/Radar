import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { AnimatePresence, animate, motion, useAnimationFrame, useMotionValue } from 'motion/react';
import { TYPE_LABEL, daysUntil, listItems, whenText, whereText } from '../api.js';
import { SLOTS, reelForSlot, reelPose, sceneAt, wrap } from '../aura/pose.js';
import { RollingCounter, Scramble } from '../aura/Loader.jsx';
import { FilterBar } from '../components/Controls.jsx';
import Cover from '../components/Cover.jsx';
import { IconPause, IconPlay, RadarMark } from '../components/Icons.jsx';
import SaveButton from '../components/SaveButton.jsx';
import { useRadar } from '../store.jsx';

// ?motion in the URL plays the full entrance even when the system asks for reduced motion (demos)
const REDUCED = matchMedia('(prefers-reduced-motion: reduce)').matches && !new URLSearchParams(location.search).has('motion');
const FORMATION_S = 2.6;
const EXPANSION_S = 1.9;
const EXPANSION_EASE = [0.5, 0, 0.15, 1];
const ASSET_TIMEOUT_MS = 7000;   // never wait on a slow image host forever
const AUTO_SPIN = 4;             // degrees per second: a slow, steady drift through the feed
const HOVER_LIFT = 110;          // px a hovered card comes toward the viewer
const DRAG_DEG_PER_PX = 0.075;
const STEP = 360 / SLOTS;

let entrancePlayed = false;  // the loader plays once per visit, not on every view switch

export default function AuraView({ filters, setFilters, wordmarkRef, onHandoff }) {
    const { home, openDetail, detail } = useRadar();
    const detailOpen = useRef(false);
    detailOpen.current = !!detail;
    const [items, setItems] = useState(null);
    const skipEntrance = REDUCED || entrancePlayed;

    // ---- the two values that drive everything ----
    const formation = useMotionValue(skipEntrance ? 1 : 0);
    const expansion = useMotionValue(skipEntrance ? 1 : 0);
    const [phase, setPhase] = useState(skipEntrance ? 'done' : 'loading');  // loading -> reveal -> done
    const phaseRef = useRef(phase);
    phaseRef.current = phase;
    const anims = useRef([]);

    useEffect(() => {
        listItems({ ...filters, limit: 96 }, home).then(setItems).catch(() => setItems([]));
    }, [filters, home]);

    // ---- real progress: covers of the reels the ring opens with ----
    const [loadedIds, setLoadedIds] = useState(() => new Set());
    const [timedOut, setTimedOut] = useState(false);
    const firstReels = useMemo(() => (items || []).slice(0, SLOTS), [items]);
    const needed = firstReels.filter(it => it.image || it.logo).length;
    const loaded = firstReels.filter(it => (it.image || it.logo) && loadedIds.has(it.id)).length;
    const assetsReady = items !== null && (loaded >= needed || timedOut);
    const progress = items === null ? 0 : needed ? (loaded / needed) * 100 : 100;
    const onCoverDone = useCallback(id => setLoadedIds(s => (s.has(id) ? s : new Set(s).add(id))), []);

    // ---- formation: starts as soon as there is something to deal ----
    const [formed, setFormed] = useState(skipEntrance);
    useEffect(() => {
        if (skipEntrance || items === null) return;
        const a = animate(formation, 1, { duration: FORMATION_S, ease: 'linear', onComplete: () => setFormed(true) });
        const t = setTimeout(() => setTimedOut(true), ASSET_TIMEOUT_MS);
        anims.current.push(a);
        return () => { a.stop(); clearTimeout(t); };
    }, [items === null]);  // eslint-disable-line react-hooks/exhaustive-deps

    // ---- expansion: after formation AND the assets, whichever is later ----
    const brandRef = useRef(null);
    useEffect(() => {
        if (phase !== 'loading' || !formed || !assetsReady) return;
        setPhase('reveal');
        entrancePlayed = true;
        const a = animate(expansion, 1, { duration: EXPANSION_S, ease: EXPANSION_EASE, onComplete: () => setPhase('done') });
        anims.current.push(a);
        // Overlap, don't queue: the header starts while the cards are still settling.
        // (A ref, not effect cleanup: setPhase above re-runs this effect straight away.)
        handoffTimer.current = setTimeout(onHandoff, EXPANSION_S * 1000 * 0.35);
        flyBrand(brandRef.current, wordmarkRef.current);
    }, [phase, formed, assetsReady]);  // eslint-disable-line react-hooks/exhaustive-deps
    const handoffTimer = useRef(0);
    useEffect(() => () => clearTimeout(handoffTimer.current), []);

    const skip = useCallback(() => {
        if (phaseRef.current === 'done') return;
        anims.current.forEach(a => a.stop());
        clearTimeout(handoffTimer.current);
        formation.set(1);
        expansion.set(1);
        entrancePlayed = true;
        setFormed(true);
        setPhase('done');
        onHandoff();
    }, [formation, expansion, onHandoff]);

    useEffect(() => {
        if (skipEntrance) onHandoff();
        const onKey = e => {
            if (phaseRef.current !== 'done' && (e.key === 'Escape' || e.key === 'Tab')) skip();
        };
        addEventListener('keydown', onKey);
        return () => removeEventListener('keydown', onKey);
    }, [skip]);  // eslint-disable-line react-hooks/exhaustive-deps

    // ---- the ring ----
    const stageRef = useRef(null);
    const ringRef = useRef(null);
    const slotEls = useRef([]);
    const lastStyle = useRef([]);
    const lastRing = useRef('');
    const angle = useRef(0), velocity = useRef(0), target = useRef(0);
    const dragState = useRef(null);
    const pointer = useRef(null);
    const hovered = useRef(null);
    const hoveredSlot = useRef(-1);
    const lift = useRef(new Array(SLOTS).fill(0));  // 0..1 per slot, eased toward the hovered card
    const spinGain = useRef(skipEntrance ? 1 : 0);  // eases the drift in and out instead of stopping dead
    const [paused, setPaused] = useState(false);
    const pausedRef = useRef(false);
    pausedRef.current = paused;
    const frame = useRef(0);
    const total = items?.length || 0;
    const [slotReel, setSlotReel] = useState(() => Array.from({ length: SLOTS }, (_, i) => i));
    const slotReelRef = useRef(slotReel);
    const [frontSlot, setFrontSlot] = useState(0);
    const frontRef = useRef(0);

    useAnimationFrame((time, delta) => {
        const dt = Math.min(delta, 50) / 1000;
        const f = formation.get();
        const e = expansion.get();
        const scene = sceneAt(e);

        // Target angle: a slow auto-spin forward through the feed. It eases to a stop while the
        // visitor holds the ring, hovers a card, opens one or presses pause, and eases back after.
        const spinning = phaseRef.current !== 'loading' && !dragState.current && hoveredSlot.current < 0
            && !pausedRef.current && !detailOpen.current;
        spinGain.current += ((spinning ? 1 : 0) - spinGain.current) * Math.min(1, dt * 2.5);
        target.current -= AUTO_SPIN * spinGain.current * dt;
        // Visible angle follows the target through a spring, so it never snaps
        const acc = 60 * (target.current - angle.current) - 14 * velocity.current;
        velocity.current += acc * dt;
        angle.current += velocity.current * dt;
        const rot = angle.current;

        // Shared ring values go on the ring as CSS variables, only when they change
        const fit = 1 + (Math.min(1, innerWidth / 1100) - 1) * (1 - e);  // keep the small ring on narrow screens
        const ringKey = `${scene.perspective.toFixed(1)}|${scene.tilt.toFixed(2)}|${scene.roll.toFixed(2)}|${fit.toFixed(3)}`;
        if (ringKey !== lastRing.current && stageRef.current && ringRef.current) {
            lastRing.current = ringKey;
            stageRef.current.style.setProperty('--persp', `${scene.perspective.toFixed(1)}px`);
            ringRef.current.style.setProperty('--tilt', `${scene.tilt.toFixed(2)}deg`);
            ringRef.current.style.setProperty('--roll', `${scene.roll.toFixed(2)}deg`);
            ringRef.current.style.setProperty('--fit', fit.toFixed(3));
        }

        let reelsChanged = false;
        let best = null, bestAbs = 999;
        const nextReels = slotReelRef.current.slice();
        for (let s = 0; s < SLOTS; s++) {
            const el = slotEls.current[s];
            if (!el) continue;
            const a = s * STEP + rot;
            const p = reelPose(a, f, scene);
            const visible = total > 0 && !p.behindCamera && p.appear > 0.001;
            // The hovered card glides toward the viewer along its own facing direction
            const l = lift.current;
            l[s] += ((s === hoveredSlot.current ? 1 : 0) - l[s]) * Math.min(1, dt * 9);
            if (l[s] < 0.001) l[s] = 0;
            const transform = visible
                ? `translate3d(${p.x.toFixed(1)}px,0,${p.z.toFixed(1)}px) rotateY(${p.yaw.toFixed(2)}deg) translateZ(${(l[s] * HOVER_LIFT).toFixed(1)}px) scale(${(p.scale * (1 + l[s] * 0.1)).toFixed(3)})`
                : 'none';
            const opacity = visible ? p.appear.toFixed(3) : '0';
            const last = lastStyle.current[s] || (lastStyle.current[s] = {});
            if (last.t !== transform) { el.style.transform = transform; last.t = transform; }
            if (last.o !== opacity) { el.style.opacity = opacity; last.o = opacity; }
            if (last.v !== visible) { el.style.visibility = visible ? 'visible' : 'hidden'; last.v = visible; }

            // Recycle: a slot that passed the back of the cylinder shows the next reel
            const reel = reelForSlot(s, rot, total);
            if (reel !== nextReels[s]) { nextReels[s] = reel; reelsChanged = true; }

            const abs = Math.abs(wrap(p.yaw));
            if (visible && abs < bestAbs) { bestAbs = abs; best = s; }
        }
        if (reelsChanged) { slotReelRef.current = nextReels; setSlotReel(nextReels); }
        if (best !== null && best !== frontRef.current) { frontRef.current = best; setFrontSlot(best); }

        // Hover hit-testing every third frame
        frame.current = (frame.current + 1) % 3;
        if (frame.current === 0 && phaseRef.current === 'done') {
            const hit = pointer.current && !dragState.current
                ? document.elementFromPoint(pointer.current.x, pointer.current.y)?.closest('.reel[data-slot]') || null
                : null;
            if (hit !== hovered.current) {
                hovered.current?.removeAttribute('data-hover');
                hit?.setAttribute('data-hover', '');
                hovered.current = hit;
                hoveredSlot.current = hit ? Number(hit.dataset.slot) : -1;
                stageRef.current?.classList.toggle('has-hover', !!hit);  // CSS blurs every other card
            }
        }
    });

    // ---- input: drag, swipe, wheel, keys ----
    const ready = phase === 'done';
    useEffect(() => {
        const stage = stageRef.current;
        if (!stage) return;
        const onWheel = e => {
            e.preventDefault();  // the page never scrolls here; during the entrance the wheel does nothing
            if (phaseRef.current !== 'done') return;
            target.current += (Math.abs(e.deltaX) > Math.abs(e.deltaY) ? e.deltaX : e.deltaY) * 0.045;
        };
        stage.addEventListener('wheel', onWheel, { passive: false });
        return () => stage.removeEventListener('wheel', onWheel);
    }, []);

    const onPointerDown = e => {
        if (!ready || e.button !== 0) return;
        dragState.current = { x: e.clientX, lastX: e.clientX, lastT: performance.now(), v: 0, moved: 0, start: target.current };
    };
    const onPointerMove = e => {
        pointer.current = { x: e.clientX, y: e.clientY };
        const d = dragState.current;
        if (!d) return;
        const now = performance.now();
        d.v = (e.clientX - d.lastX) / Math.max(1, now - d.lastT);
        d.lastX = e.clientX;
        d.lastT = now;
        d.moved = Math.max(d.moved, Math.abs(e.clientX - d.x));
        if (d.moved > 6 && !d.captured) { stageRef.current.setPointerCapture(e.pointerId); d.captured = true; }
        target.current = d.start - (e.clientX - d.x) * DRAG_DEG_PER_PX;
    };
    const endDrag = () => {
        const d = dragState.current;
        if (!d) return;
        target.current -= d.v * 260 * DRAG_DEG_PER_PX;  // a swipe keeps going a little
        dragState.current = null;
        if (d.moved > 6) suppressClickUntil.current = performance.now() + 300;  // the click that ends a drag
    };
    const suppressClickUntil = useRef(0);

    const bringToFront = s => {
        target.current = angle.current - wrap(s * STEP + angle.current);
    };
    const onRingKey = e => {
        if (!ready) return;
        if (e.key === 'ArrowLeft') { target.current += STEP; e.preventDefault(); }
        if (e.key === 'ArrowRight') { target.current -= STEP; e.preventDefault(); }
    };

    const frontItem = items?.[slotReel[frontSlot]];
    const showLoader = phase !== 'done';

    return (
        <section className={`aura phase-${phase}`} aria-label="Aura view">
            {/* White loader page under the cards; fades while the cards keep moving */}
            {!skipEntrance && (
                <motion.div className="aura-backdrop" aria-hidden="true"
                            initial={{ opacity: 1 }}
                            animate={{ opacity: phase === 'loading' ? 1 : 0 }}
                            transition={{ duration: phase === 'done' ? 0 : 1.2, ease: 'easeOut' }} />
            )}

            <div className="aura-stage" ref={stageRef}
                 onPointerDown={onPointerDown} onPointerMove={onPointerMove}
                 onPointerUp={endDrag} onPointerCancel={endDrag}
                 onPointerLeave={() => { pointer.current = null; }}
                 onKeyDown={onRingKey}>
                <div className="aura-ring" ref={ringRef}>
                    {Array.from({ length: SLOTS }, (_, s) => {
                        const it = items?.[slotReel[s]];
                        return (
                            <a key={s} className="reel" data-slot={s} ref={el => (slotEls.current[s] = el)}
                               href={it?.url || '#'} draggable="false"
                               aria-label={it ? `${it.title}${it.organization ? ', ' + it.organization : ''}. ${whenText(it)}` : undefined}
                               tabIndex={ready && it ? 0 : -1}
                               style={{ opacity: 0, visibility: 'hidden' }}
                               onFocus={() => ready && bringToFront(s)}
                               onClick={e => {
                                   if (e.metaKey || e.ctrlKey || e.button === 1) return;  // new tab works as a normal link
                                   e.preventDefault();
                                   if (performance.now() < suppressClickUntil.current) return;
                                   if (it && ready) openDetail(it);
                               }}>
                                {it && <ReelFace item={it} onCoverDone={() => onCoverDone(it.id)} />}
                                <div className="reel-back" aria-hidden="true"><RadarMark size={40} /></div>
                            </a>
                        );
                    })}
                </div>
            </div>

            {/* Loader chrome */}
            <AnimatePresence>
                {showLoader && !skipEntrance && (
                    <motion.div className="aura-loader" key="loader" exit={{ opacity: 0 }} transition={{ duration: 0.4 }}>
                        <div className="loader-brand" ref={brandRef}>Radar</div>
                        <motion.div className="loader-count"
                                    animate={{ opacity: phase === 'loading' ? 1 : 0, y: phase === 'loading' ? 0 : 20 }}
                                    transition={{ duration: 0.5 }}>
                            <Scramble text="Loading opportunities" />
                            <div className="loader-num" role="progressbar" aria-label="Loading opportunities"
                                 aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(progress)}>
                                <RollingCounter value={progress} />
                                <span className="loader-pct">%</span>
                            </div>
                            <div className="loader-detail">{needed ? `${loaded} of ${needed} covers` : 'Dealing the ring'}</div>
                        </motion.div>
                        <button className="skip" onClick={skip}>Skip intro</button>
                    </motion.div>
                )}
            </AnimatePresence>

            {/* Frame and headline arrive while the ring settles */}
            <motion.div className="aura-frame"
                        initial={false}
                        animate={phase === 'loading' ? { opacity: 0, y: 24 } : { opacity: 1, y: 0 }}
                        transition={{ duration: 0.7, delay: phase === 'reveal' ? 0.8 : 0, ease: [0.2, 0.8, 0.2, 1] }}
                        aria-hidden={phase === 'loading'}>
                <div className="aura-head">
                    <h1>{total ? `${total} opportunities on the ring` : items === null ? 'Loading' : 'Nothing matches these filters'}</h1>
                    <p>Drag, swipe or scroll to turn it. Select a card to open it.</p>
                </div>
                <div className="aura-filters">
                    <button className="chip spin-toggle" aria-pressed={paused} onClick={() => setPaused(p => !p)}
                            aria-label={paused ? 'Resume turning' : 'Pause turning'}>
                        {paused ? <IconPlay /> : <IconPause />}{paused ? 'Play' : 'Pause'}
                    </button>
                    <FilterBar filters={filters} setFilters={setFilters} hideSearch />
                </div>
                <AnimatePresence mode="wait">
                    {frontItem && (
                        <motion.div className="aura-focus" key={frontItem.id}
                                    initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }}
                                    transition={{ duration: 0.22 }}>
                            <div className="aura-focus-text">
                                <span className="aura-focus-when">{whenText(frontItem)}{whereText(frontItem) ? `, ${whereText(frontItem)}` : ''}</span>
                                <strong>{frontItem.title}</strong>
                            </div>
                            <button className="btn-outline" onClick={() => openDetail(frontItem)}>Details</button>
                            <SaveButton item={frontItem} />
                        </motion.div>
                    )}
                </AnimatePresence>
            </motion.div>
        </section>
    );
}

function ReelFace({ item, onCoverDone }) {
    const d = daysUntil(item.deadline);
    const urgent = d !== null && d >= 0 && d <= 3;
    return (
        <div className="reel-front">
            <Cover item={item} onDone={onCoverDone} className="reel-cover" />
            <div className="reel-info">
                <span className="reel-type">{TYPE_LABEL[item.pillar]} <em>{item.source}</em></span>
                <strong className="reel-title">{item.title}</strong>
                <span className="reel-org">{item.organization}</span>
                <span className={`reel-when ${urgent ? 'is-urgent' : ''}`}>
                    {d !== null && d >= 0 ? <><b>{d}</b>{d === 1 ? ' day left' : ' days left'}</> : whenText(item)}
                </span>
            </div>
        </div>
    );
}

/** The loader's brand word flies into the header wordmark's exact place and size. */
function flyBrand(from, wordmark) {
    const to = wordmark?.querySelector('span');
    if (!from || !to) return;
    const a = from.getBoundingClientRect();
    const b = to.getBoundingClientRect();
    animate(from, {
        x: b.left - a.left,
        y: b.top - a.top,
        scale: b.height / a.height,
        color: getComputedStyle(to).color,
    }, { duration: 1.05, ease: [0.65, 0, 0.2, 1] });
}
