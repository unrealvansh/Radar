import { useEffect, useState } from 'react';

/** Mono counter where each digit is its own column that rolls vertically. */
export function RollingCounter({ value, digits = 3 }) {
    const text = String(Math.max(0, Math.round(value))).padStart(digits, '0');
    const firstReal = text.search(/[1-9]/);
    return (
        <span className="roll" aria-hidden="true">
            {[...text].map((ch, i) => (
                <span key={i} className={`roll-col ${i < (firstReal === -1 ? digits - 1 : firstReal) ? 'is-lead' : ''}`}>
                    <span className="roll-strip" style={{ transform: `translateY(${-Number(ch) * 10}%)` }}>
                        {'0123456789'.split('').map(d => <span key={d}>{d}</span>)}
                    </span>
                </span>
            ))}
        </span>
    );
}

const GLYPHS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789/#*+';

/** Text that resolves from random glyphs, then keeps a faint flicker while it stays up. */
export function Scramble({ text }) {
    const [out, setOut] = useState(text.replace(/\S/g, ' '));
    useEffect(() => {
        let tick = 0;
        const id = setInterval(() => {
            tick++;
            const resolved = Math.min(text.length, Math.floor(tick / 1.6));
            setOut([...text].map((ch, i) => {
                if (ch === ' ') return ' ';
                if (i < resolved) {
                    // after resolving, an occasional letter flickers
                    return resolved === text.length && Math.random() < 0.03 ? GLYPHS[(Math.random() * GLYPHS.length) | 0] : ch;
                }
                return GLYPHS[(Math.random() * GLYPHS.length) | 0];
            }).join(''));
        }, 45);
        return () => clearInterval(id);
    }, [text]);
    return <span className="scramble" aria-label={text}>{out}</span>;
}
