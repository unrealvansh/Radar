import { memo } from 'react';
import { motion, useMotionValue, useSpring, useTransform } from 'motion/react';
import { TYPE_LABEL, daysUntil, matchedKeywords, whenText, whereText } from '../api.js';
import { useRadar } from '../store.jsx';
import Cover, { Logo } from './Cover.jsx';
import SaveButton, { TrackButton } from './SaveButton.jsx';
import { IconCalendar, IconGlobe, IconPin } from './Icons.jsx';

const finePointer = typeof matchMedia !== 'undefined' && matchMedia('(hover: hover) and (pointer: fine)').matches;

function OppCard({ item, index = 0, compact = false }) {
    const { keywords, openDetail } = useRadar();
    const d = daysUntil(item.deadline);
    const urgent = d !== null && d >= 0 && d <= 3;
    const where = whereText(item);
    const online = item.mode === 'online' || item.mode === 'remote';
    const pills = [TYPE_LABEL[item.pillar], ...matchedKeywords(item, keywords).slice(0, 3)];
    if (item.mode && item.mode !== 'onsite') pills.push(item.mode);

    const px = useMotionValue(0.5), py = useMotionValue(0.5);
    const rotX = useSpring(useTransform(py, [0, 1], [4, -4]), { stiffness: 220, damping: 22 });
    const rotY = useSpring(useTransform(px, [0, 1], [-5, 5]), { stiffness: 220, damping: 22 });
    const onMove = e => {
        if (!finePointer) return;
        const r = e.currentTarget.getBoundingClientRect();
        px.set((e.clientX - r.left) / r.width);
        py.set((e.clientY - r.top) / r.height);
    };
    const onLeave = () => { px.set(0.5); py.set(0.5); };

    return (
        <motion.article
            className={`oc ${compact ? 'oc-compact' : ''}`}
            initial={{ opacity: 0, y: 28 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: '0px 0px -40px 0px' }}
            transition={{ duration: 0.5, ease: [0.2, 0.8, 0.2, 1], delay: (index % 4) * 0.06 }}
            style={{ rotateX: rotX, rotateY: rotY, transformPerspective: 900 }}
            onPointerMove={onMove}
            onPointerLeave={onLeave}
            onClick={() => openDetail(item)}
        >
            <div className="oc-banner">
                <Cover item={item} />
            </div>
            <div className="oc-logo"><Logo item={item} /></div>
            <h3 className="oc-title">
                <a href={item.url} onClick={e => { e.preventDefault(); }} aria-label={`${item.title}, open details`}>{item.title}</a>
            </h3>
            <p className="oc-sub">{item.organization || item.extra_info || item.source}</p>
            <div className="oc-stats">
                <span className={urgent ? 'is-urgent' : ''}><IconCalendar />{whenText(item)}</span>
                {where && <span>{online ? <IconGlobe /> : <IconPin />}{where}</span>}
            </div>
            <div className="oc-pills">
                {pills.map(p => <span key={p} className="pill">{p}</span>)}
            </div>
            <div className="oc-actions">
                <SaveButton item={item} />
                {item.pillar !== 'news' && <TrackButton item={item} />}
            </div>
        </motion.article>
    );
}

export default memo(OppCard);
