import { useState } from 'react';
import { initials } from '../api.js';

function Pattern({ item }) {
    const id = `p${item.id}`;
    const shift = (item.id * 37) % 60;
    return (
        <svg className="cover-gen" viewBox="0 0 270 270" preserveAspectRatio="xMidYMid slice" aria-hidden="true">
            <defs>
                {item.pillar === 'jobs' ? (
                    <pattern id={id} width="18" height="18" patternUnits="userSpaceOnUse">
                        <path d="M18 0H0V18" fill="none" stroke="currentColor" strokeOpacity=".22" />
                    </pattern>
                ) : (
                    <pattern id={id} width="270" height="9" patternUnits="userSpaceOnUse">
                        <path d="M0 4.5H270" stroke="currentColor" strokeOpacity=".14" />
                    </pattern>
                )}
            </defs>
            <rect width="270" height="270" fill={`url(#${id})`} />
            {item.pillar === 'events' && [40, 80, 120, 160].map(r => (
                <circle key={r} cx={200 - shift} cy={70 + shift} r={r} fill="none" stroke="var(--accent)" strokeOpacity=".35" />
            ))}
            <text x="22" y="246" className="cover-initials">{initials(item.organization || item.source)}</text>
        </svg>
    );
}

export default function Cover({ item, onDone, className = '' }) {
    const [failed, setFailed] = useState(false);
    const src = item.image || item.logo;
    if (!src || failed) return <div className={`cover ${className}`}><Pattern item={item} /></div>;
    return (
        <div className={`cover ${className}`}>
            <img src={src} alt="" loading="lazy" decoding="async" draggable="false"
                 onLoad={onDone}
                 onError={() => { setFailed(true); onDone?.(); }} />
        </div>
    );
}

export function Logo({ item, size = 64 }) {
    const [failed, setFailed] = useState(false);
    const src = item.logo || item.image;
    return (
        <div className="logo" style={{ width: size, height: size }}>
            {src && !failed
                ? <img src={src} alt="" loading="lazy" decoding="async" onError={() => setFailed(true)} />
                : <span>{initials(item.organization || item.source)}</span>}
        </div>
    );
}
