import { describe, expect, it } from 'vitest';
import {
    SCENE_END, SCENE_START, SLOTS, dealStart, easeOutCubic, expansionEase,
    reelForSlot, reelPose, sceneAt, wrap,
} from './pose.js';

const close = (a, b, eps = 1e-6) => expect(Math.abs(a - b)).toBeLessThan(eps);

describe('wrap', () => {
    it('keeps angles in (-180, 180]', () => {
        expect(wrap(0)).toBe(0);
        expect(wrap(190)).toBe(-170);
        expect(wrap(-180)).toBe(180);
        expect(wrap(540)).toBe(180);
        expect(wrap(-370)).toBe(-10);
    });
});

describe('sceneAt', () => {
    it('matches the start and end scenes', () => {
        expect(sceneAt(0)).toEqual(SCENE_START);
        expect(sceneAt(1)).toEqual(SCENE_END);
    });
    it('interpolates every value halfway', () => {
        const s = sceneAt(0.5);
        close(s.radius, 1130);
        close(s.tilt, -11);
        close(s.roll, -10);
        close(s.perspective, 725);
        close(s.scale, 1.41);
    });
    it('clamps outside 0..1', () => {
        expect(sceneAt(-1)).toEqual(SCENE_START);
        expect(sceneAt(2)).toEqual(SCENE_END);
    });
});

describe('eases', () => {
    it('ease-out cubic runs 0 to 1 and front-loads', () => {
        expect(easeOutCubic(0)).toBe(0);
        expect(easeOutCubic(1)).toBe(1);
        expect(easeOutCubic(0.5)).toBeGreaterThan(0.5);
    });
    it('expansion ease is the .5,0,.15,1 curve', () => {
        expect(expansionEase(0)).toBe(0);
        expect(expansionEase(1)).toBe(1);
        expect(expansionEase(0.2)).toBeLessThan(0.2);
        expect(expansionEase(0.8)).toBeGreaterThan(0.9);
    });
});

describe('reelPose at full formation', () => {
    const scene = sceneAt(0);
    it('puts angle 0 at the far centre, facing the camera', () => {
        const p = reelPose(0, 1, scene);
        close(p.x, 0);
        close(p.z, -scene.radius);
        close(p.yaw, 0);
        expect(p.appear).toBe(1);
    });
    it('puts 180 nearest the camera', () => {
        const p = reelPose(180, 1, scene);
        close(p.x, 0, 1e-9);
        close(p.z, scene.radius);
        expect(Math.abs(p.yaw)).toBe(180);
    });
    it('uses x = -sin(a) r and z = -cos(a) r at +-90', () => {
        const right = reelPose(90, 1, scene);
        close(right.x, -scene.radius);
        close(right.z, 0);
        close(right.yaw, 90);
        const left = reelPose(-90, 1, scene);
        close(left.x, scene.radius);
        close(left.yaw, -90);
    });
    it('carries the scene scale', () => {
        expect(reelPose(30, 1, sceneAt(1)).scale).toBe(SCENE_END.scale);
    });
});

describe('formation', () => {
    const scene = sceneAt(0);
    it('stacks every card at the front, invisible, at formation 0', () => {
        for (let slot = 0; slot < SLOTS; slot++) {
            const p = reelPose(slot * 360 / SLOTS, 0, scene);
            close(Math.abs(p.yaw), 180, 1e-6);
            close(p.z, scene.radius, 1e-6);
            expect(p.appear).toBe(0);
        }
    });
    it('deals cards in angle order, round the ring from the front', () => {
        const order = Array.from({ length: SLOTS }, (_, s) => s * 360 / SLOTS)
            .sort((a, b) => dealStart(a) - dealStart(b));
        expect(order[0]).toBe(180);
        const fromFront = order.map(a => ((wrap(a) - 180) % 360 + 360) % 360);
        expect(fromFront).toEqual([...fromFront].sort((a, b) => a - b));
    });
    it('every card has landed by formation 1', () => {
        expect(Math.max(...Array.from({ length: SLOTS }, (_, s) => dealStart(s * 22.5)))).toBeLessThan(1);
    });
    it('a card fades in as it is dealt', () => {
        const a = 0;
        const start = dealStart(a);
        expect(reelPose(a, start, scene).appear).toBe(0);
        expect(reelPose(a, start + 0.05, scene).appear).toBeGreaterThan(0);
    });
});

describe('behindCamera', () => {
    it('is false for everything outside the small ring', () => {
        const scene = sceneAt(0);
        for (let a = -180; a <= 180; a += 15) expect(reelPose(a, 1, scene).behindCamera).toBe(false);
    });
    it('hides the near side once the camera is inside the big ring', () => {
        const scene = sceneAt(1);
        expect(reelPose(180, 1, scene).behindCamera).toBe(true);
        expect(reelPose(0, 1, scene).behindCamera).toBe(false);
        expect(reelPose(90, 1, scene).behindCamera).toBe(false);
    });
});

describe('reelForSlot', () => {
    it('shows slot n as reel n before any rotation', () => {
        for (let s = 0; s < SLOTS; s++) expect(reelForSlot(s, 0, 100)).toBe(s);
    });
    it('moves a slot on by 16 reels each time it passes the back', () => {
        expect(reelForSlot(4, 89, 100)).toBe(4);
        expect(reelForSlot(4, 91, 100)).toBe((4 - 16 + 100) % 100);
    });
    it('wraps round small feeds and handles empty ones', () => {
        expect(reelForSlot(10, 0, 4)).toBe(2);
        expect(reelForSlot(3, 0, 0)).toBe(-1);
    });
});
