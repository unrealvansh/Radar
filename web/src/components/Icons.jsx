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

export const IconBell = p => <svg {...base} {...p}><path d="M6 9a6 6 0 0 1 12 0c0 6 3 8 3 8H3s3-2 3-8M10 21h4" /></svg>;
export const IconScan = p => <svg {...base} {...p}><path d="M20 12a8 8 0 1 1-2.3-5.7" /><path d="M20 4v5h-5" /></svg>;
export const IconSettings = p => <svg {...base} {...p}><circle cx="12" cy="12" r="3" /><path d="M12 2v3M12 19v3M2 12h3M19 12h3M4.9 4.9l2.1 2.1M17 17l2.1 2.1M4.9 19.1L7 17M17 7l2.1-2.1" /></svg>;
export const IconLeft = p => <svg {...base} {...p}><path d="M15 5l-7 7 7 7" /></svg>;
export const IconRight = p => <svg {...base} {...p}><path d="M9 5l7 7-7 7" /></svg>;
export const IconCopy = p => <svg {...base} {...p}><path d="M8 8h12v12H8zM16 8V4H4v12h4" /></svg>;
export const IconLock = p => <svg {...base} {...p}><path d="M5 11h14v10H5zM8 11V7a4 4 0 0 1 8 0v4" /></svg>;
export const IconLocate = p => <svg {...base} {...p}><circle cx="12" cy="12" r="6" /><path d="M12 2v4M12 18v4M2 12h4M18 12h4" /></svg>;

const NAV_PATHS = {
    home: <><circle cx="12" cy="12" r="9" /><circle cx="12" cy="12" r="4.5" /><path d="M12 12l6-6" /></>,
    feed: <path d="M4 4h7v7H4zM13 4h7v7h-7zM4 13h7v7H4zM13 13h7v7h-7z" />,
    map: <><path d="M3 6l6-2 6 2 6-2v14l-6 2-6-2-6 2z" /><path d="M9 4v14M15 6v14" /></>,
    calendar: <path d="M3 6h18v15H3zM3 10h18M8 3v4M16 3v4" />,
    board: <path d="M4 4h4v16H4zM10 4h4v11h-4zM16 4h4v7h-4z" />,
    settings: <><circle cx="12" cy="12" r="3" /><path d="M12 2v3M12 19v3M2 12h3M19 12h3M4.9 4.9l2.1 2.1M17 17l2.1 2.1M4.9 19.1L7 17M17 7l2.1-2.1" /></>,
};
export const NavIcon = ({ id }) => <svg {...base} width={18} height={18}>{NAV_PATHS[id]}</svg>;

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
