// Small square-cap stroke icons, drawn for Radar (no icon library).
const base = { width: 16, height: 16, viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor',
    strokeWidth: 1.7, strokeLinecap: 'square', strokeLinejoin: 'miter', 'aria-hidden': true };

export const IconCalendar = p => <svg {...base} {...p}><path d="M3 6h18v15H3zM3 10h18M8 3v4M16 3v4" /></svg>;
export const IconPin = p => <svg {...base} {...p}><path d="M12 21s-7-6-7-11.5a7 7 0 0 1 14 0C19 15 12 21 12 21z" /><path d="M12 7v5" /></svg>;
export const IconPlus = p => <svg {...base} {...p}><path d="M12 5v14M5 12h14" /></svg>;
export const IconCheck = p => <svg {...base} {...p}><path d="M5 12.5l4.5 4.5L19 7.5" /></svg>;
export const IconChevron = p => <svg {...base} {...p}><path d="M6 9l6 6 6-6" /></svg>;
export const IconX = p => <svg {...base} {...p}><path d="M6 6l12 12M18 6L6 18" /></svg>;
export const IconOut = p => <svg {...base} {...p}><path d="M14 4h6v6M20 4l-9 9M19 14v6H4V5h6" /></svg>;
export const IconSearch = p => <svg {...base} {...p}><circle cx="11" cy="11" r="7" /><path d="M20 20l-4-4" /></svg>;
export const IconBack = p => <svg {...base} {...p}><path d="M15 5l-7 7 7 7" /></svg>;
export const IconPause = p => <svg {...base} {...p}><path d="M8 5v14M16 5v14" /></svg>;
export const IconPlay = p => <svg {...base} {...p}><path d="M7 4l13 8-13 8z" /></svg>;
export const IconGlobe = p => <svg {...base} {...p}><circle cx="12" cy="12" r="9" /><path d="M3 12h18M12 3c3 3 3 15 0 18M12 3c-3 3-3 15 0 18" /></svg>;

export function RadarMark({ size = 28 }) {
    return (
        <svg width={size} height={size} viewBox="0 0 40 40" aria-hidden="true" className="radar-mark">
            <circle cx="20" cy="20" r="18" fill="none" stroke="currentColor" strokeWidth="1.6" />
            <circle cx="20" cy="20" r="11" fill="none" stroke="currentColor" strokeOpacity=".5" strokeWidth="1.2" />
            <path d="M20 2v36M2 20h36" stroke="currentColor" strokeOpacity=".35" strokeWidth="1" />
            <path d="M20 20L32 8" stroke="var(--accent)" strokeWidth="2" strokeLinecap="square" />
            <rect x="26" y="25" width="3" height="3" fill="var(--accent)" />
        </svg>
    );
}
