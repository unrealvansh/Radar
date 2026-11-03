import { STATES } from './states.js';

// Map geometry for the dot-matrix India. Outlines come from Datameet's state boundaries
// (states.js); the dots are the points of a grid that fall inside any state.
export const BOUNDS = { west: 67.5, east: 98, south: 6.2, north: 37.4 };
const LON_SCALE = Math.cos((22 * Math.PI) / 180);  // equirectangular, corrected at India's middle latitude

/** Plane size for a given width, keeping India's proportions. */
export function planeSize(width) {
    const w = (BOUNDS.east - BOUNDS.west) * LON_SCALE;
    const h = BOUNDS.north - BOUNDS.south;
    return { w: width, h: Math.round((width * h) / w) };
}

export function project(lon, lat, size) {
    return {
        x: ((lon - BOUNDS.west) / (BOUNDS.east - BOUNDS.west)) * size.w,
        y: ((BOUNDS.north - lat) / (BOUNDS.north - BOUNDS.south)) * size.h,
    };
}

// Every outline ring with its bounding box, so a point only tests the rings it could be in
const RINGS = STATES.flatMap(s => s.r.map(r => {
    let minX = 999, minY = 999, maxX = -999, maxY = -999;
    for (let i = 0; i < r.length; i += 2) {
        minX = Math.min(minX, r[i]); maxX = Math.max(maxX, r[i]);
        minY = Math.min(minY, r[i + 1]); maxY = Math.max(maxY, r[i + 1]);
    }
    return { r, minX, minY, maxX, maxY };
}));

function inRing(lon, lat, r) {
    let inside = false;
    for (let i = 0, j = r.length - 2; i < r.length; j = i, i += 2) {
        const xi = r[i], yi = r[i + 1], xj = r[j], yj = r[j + 1];
        if ((yi > lat) !== (yj > lat) && lon < ((xj - xi) * (lat - yi)) / (yj - yi) + xi) inside = !inside;
    }
    return inside;
}

/** Is this point on Indian land (inside any state)? */
export function inIndia(lon, lat) {
    for (const g of RINGS) {
        if (lon < g.minX || lon > g.maxX || lat < g.minY || lat > g.maxY) continue;
        if (inRing(lon, lat, g.r)) return true;
    }
    return false;
}

/** State outlines projected onto the plane, as arrays of [x, y] points. */
export function statePaths(size) {
    return RINGS.map(({ r }) => {
        const pts = [];
        for (let i = 0; i < r.length; i += 2) {
            const p = project(r[i], r[i + 1], size);
            pts.push(p.x, p.y);
        }
        return pts;
    });
}
