import { forwardRef, useEffect, useImperativeHandle, useRef, useState } from 'react';

export const Odometer = forwardRef(function Odometer({ digits = 3 }, ref) {
    const cols = useRef([]);
    useImperativeHandle(ref, () => ({
        set(value) {
            const v = Math.max(0, Math.min(100, value));
            for (let i = 0; i < digits; i++) {
                const place = 10 ** (digits - 1 - i);
                const whole = Math.floor(v / place);
                const below = v - whole * place;
                const carry = Math.max(0, below - (place - 1));
                const pos = (whole % 10) + carry;
                const el = cols.current[i];
                if (!el) continue;
                el.style.transform = `translate3d(0, ${(-pos / 11) * 100}%, 0)`;
                el.parentElement.classList.toggle('is-lead', i < digits - 1 && v < place);
            }
        },
    }), [digits]);
    return (
        <span className="roll" aria-hidden="true">
            {Array.from({ length: digits }, (_, i) => (
                <span key={i} className={`roll-col ${i < digits - 1 ? 'is-lead' : ''}`}>
                    <span className="roll-strip" ref={el => (cols.current[i] = el)}>
                        {'01234567890'.split('').map((d, k) => <span key={k}>{d}</span>)}
                    </span>
                </span>
            ))}
        </span>
    );
});

const GLYPHS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789/#*+';

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
                    return resolved === text.length && Math.random() < 0.03 ? GLYPHS[(Math.random() * GLYPHS.length) | 0] : ch;
                }
                return GLYPHS[(Math.random() * GLYPHS.length) | 0];
            }).join(''));
        }, 45);
        return () => clearInterval(id);
    }, [text]);
    return <span className="scramble" aria-label={text}>{out}</span>;
}
