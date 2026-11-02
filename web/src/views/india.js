// A simplified outline of India (mainland, clockwise from Kutch), [lon, lat].
// Only used to decide which dots of the dot-matrix map are "land"; it is a drawing aid,
// not a survey-grade boundary.
export const INDIA = [
    [68.2, 23.7], [68.9, 24.3], [70.0, 24.2], [71.0, 24.4], [70.6, 25.7], [70.1, 26.6], [69.5, 27.0],
    [70.4, 28.0], [71.9, 27.9], [72.9, 29.0], [73.4, 29.9], [74.5, 30.9], [74.6, 31.9], [75.3, 32.3],
    [74.6, 32.8], [74.0, 33.4], [73.8, 34.3], [74.3, 34.8], [75.7, 35.0], [76.8, 35.6], [77.8, 35.5],
    [78.9, 34.3], [78.7, 33.1], [79.4, 32.5], [78.5, 32.0], [78.9, 31.1], [79.9, 30.9], [81.1, 30.2],
    [80.1, 28.8], [81.3, 28.2], [82.9, 27.5], [84.2, 27.4], [85.6, 26.8], [87.0, 26.4], [88.1, 26.6],
    [88.2, 27.2], [88.8, 27.3], [88.9, 26.9], [89.8, 26.7], [91.6, 26.8], [92.1, 26.9], [92.0, 27.5],
    [91.6, 27.8], [92.5, 27.9], [93.8, 28.2], [95.4, 29.0], [96.1, 29.4], [97.4, 28.3], [96.9, 27.4],
    [95.8, 27.0], [95.2, 26.6], [94.6, 25.3], [94.2, 23.9], [93.4, 23.6], [93.2, 22.2], [92.6, 21.9],
    [92.3, 23.3], [91.8, 22.9], [91.2, 23.6], [91.9, 24.3], [92.4, 24.3], [92.2, 25.1], [90.4, 25.2],
    [89.8, 25.3], [89.9, 26.0], [88.4, 26.3], [88.1, 25.6], [88.1, 24.9], [88.7, 24.2], [88.6, 23.2],
    [89.0, 22.2], [89.1, 21.6], [88.2, 21.6], [87.0, 21.5], [86.6, 20.6], [85.1, 19.5], [84.1, 18.3],
    [82.3, 17.0], [81.2, 16.0], [80.3, 15.6], [80.1, 13.5], [79.9, 12.0], [79.8, 10.3], [79.2, 9.3],
    [78.2, 8.9], [77.5, 8.1], [76.6, 8.9], [76.2, 10.0], [75.8, 11.5], [75.0, 12.8], [74.5, 14.0],
    [73.9, 15.4], [73.4, 16.6], [72.9, 18.5], [72.8, 19.5], [72.6, 21.3], [72.6, 22.2], [72.2, 21.8],
    [71.1, 20.8], [70.0, 21.1], [69.0, 22.3], [69.6, 22.6], [70.4, 23.0], [69.2, 22.8], [68.4, 23.3],
];

export const BOUNDS = { west: 67.5, east: 98, south: 6.5, north: 36.2 };
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

/** Ray-casting point-in-polygon. */
export function inIndia(lon, lat) {
    let inside = false;
    for (let i = 0, j = INDIA.length - 1; i < INDIA.length; j = i++) {
        const [xi, yi] = INDIA[i], [xj, yj] = INDIA[j];
        if ((yi > lat) !== (yj > lat) && lon < ((xj - xi) * (lat - yi)) / (yj - yi) + xi) inside = !inside;
    }
    return inside;
}
