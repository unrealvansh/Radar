// Geometry for the Aura ring. Pure functions only: everything the entrance and the
// carousel draw comes from reelPose() + sceneAt(), so they carry the whole animation.
//
// Angles are in degrees. 0 is the far centre of the ring, +-180 is the card nearest
// the camera. Cards sit on the inside of the cylinder and face its centre.

export const SLOTS = 16;
export const DEAL_SPAN = 0.32; // share of the formation each card takes to swing out

export const SCENE_START = { radius: 460, tilt: -22, roll: -20, perspective: 1000, scale: 0.52 };
export const SCENE_END = { radius: 1800, tilt: 0, roll: 0, perspective: 450, scale: 2.3 };

const lerp = (a, b, t) => a + (b - a) * t;
const clamp01 = t => Math.min(1, Math.max(0, t));
const rad = deg => (deg * Math.PI) / 180;

/** Wrap any angle into (-180, 180]. */
export function wrap(deg) {
    const w = ((((deg + 180) % 360) + 360) % 360) - 180;
    return w === -180 ? 180 : w;
}

/** Ease-out cubic: fast start, gentle landing. */
export const easeOutCubic = t => 1 - Math.pow(1 - clamp01(t), 3);

/** CSS cubic-bezier(x1, y1, x2, y2) as a function of progress t. */
export function cubicBezier(x1, y1, x2, y2) {
    const bx = s => 3 * x1 * s * (1 - s) ** 2 + 3 * x2 * s * s * (1 - s) + s ** 3;
    const by = s => 3 * y1 * s * (1 - s) ** 2 + 3 * y2 * s * s * (1 - s) + s ** 3;
    return t => {
        if (t <= 0) return 0;
        if (t >= 1) return 1;
        let lo = 0, hi = 1, s = t;
        for (let i = 0; i < 30; i++) {  // bisection: x(s) is monotonic for valid curves
            s = (lo + hi) / 2;
            if (bx(s) < t) lo = s; else hi = s;
        }
        return by(s);
    };
}

export const expansionEase = cubicBezier(0.5, 0, 0.15, 1);

/** The camera and ring for an (already eased) expansion value 0..1. */
export function sceneAt(expansion) {
    const t = clamp01(expansion);
    const s = {};
    for (const key of Object.keys(SCENE_START)) s[key] = lerp(SCENE_START[key], SCENE_END[key], t);
    return s;
}

/**
 * Where the deal for a card at `angle` starts, 0..1 of the formation.
 * Cards are dealt in angle order, travelling round the ring from the front.
 */
export function dealStart(angle) {
    const fromFront = ((wrap(angle) - 180) % 360 + 360) % 360;  // 0 at the front, rising round the ring
    return (fromFront / 360) * (1 - DEAL_SPAN);
}

/**
 * Pose of one card.
 * @param angle      the card's resting angle, ring rotation included
 * @param formation  0..1, the loader deal (0 = every card stacked at the front)
 * @param scene      output of sceneAt()
 * @returns {{x, y, z, yaw, scale, appear, behindCamera}}
 */
export function reelPose(angle, formation, scene) {
    const target = wrap(angle);
    const start = dealStart(target);
    const local = easeOutCubic((formation - start) / DEAL_SPAN);

    // Swing from the front (180) round to the resting angle, always in the deal direction
    const travel = ((target - 180) % 360 + 360) % 360;
    const a = wrap(180 + travel * local);

    const x = -Math.sin(rad(a)) * scene.radius;
    const z = -Math.cos(rad(a)) * scene.radius;
    // A card is unseeable once it is level with or behind the viewer (CSS perspective puts
    // the eye `perspective` px in front of the ring's centre plane).
    const behindCamera = z > scene.perspective * 0.92;

    return {
        x,
        y: 0,
        z,
        yaw: a,
        scale: scene.scale,
        appear: clamp01((formation - start) / (DEAL_SPAN * 0.35)),
        behindCamera,
    };
}

/**
 * Which reel a slot shows. Slots wrap at the back of the ring (+-180); every full lap a
 * slot passes, it moves on by SLOTS reels, so 16 DOM cards can show any number of reels.
 */
export function reelForSlot(slot, rotation, total) {
    if (total <= 0) return -1;
    // Laps completed past +180 (the back); resting angles count from (-180, 180]
    const lap = Math.ceil((wrap(slot * (360 / SLOTS)) + rotation - 180) / 360);
    return (((slot - lap * SLOTS) % total) + total) % total;
}
