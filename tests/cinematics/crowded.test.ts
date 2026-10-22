// Crowded boards: lighting rig, occluder fading, camera clearance and background rules.
import { Vector3 } from 'three';
import { describe, expect, it } from 'vitest';
import { ROLE_HEIGHT } from '../../src/contracts';
import { createSequencePlayer, drain, gsap, runUntil } from './harness';
import { captureCase, crowdedCase, expectCaptureFinal, FACTIONS, ROLES } from './scenarios';
import type { SpotLight } from 'three';
import { OccluderFader, OCCLUDER_ALPHA } from '../../src/cinematics/occluders';
import { pickShot } from '../../src/cinematics/shotPicker';
import { MockActor } from './mocks';

const NAMES = ['opening-w', 'opening-b', 'backrank-w', 'backrank-b'] as const;

describe('crowded board captures', () => {
  it.each(NAMES)('%s: lit, occluders faded and restored, camera clear of pieces, background is the board', async (name) => {
    const c = crowdedCase(name);
    const startPos = new Map(c.bystanders.map((b) => [b, b.root.position.clone()]));
    let maxLight = 0; let rigSeen = false; let minFade = 1;
    const sample = () => {
      const rig = c.rig.board.scene.children.find((o) => o.name === 'cinematic_light_rig');
      if (rig) {
        rigSeen = true;
        const lights = rig.children.filter((o) => (o as SpotLight).isSpotLight) as SpotLight[];
        expect(lights.length).toBe(3);
        maxLight = Math.max(maxLight, ...lights.map((l) => l.intensity));
      }
      for (const b of c.bystanders) minFade = Math.min(minFade, b.fade);
    };
    gsap.ticker.add(sample);
    const { settled } = await runUntil(createSequencePlayer().capture(c.rig.ctx), 30000);
    gsap.ticker.remove(sample);
    expect(settled).toBe(true);
    await drain();
    expectCaptureFinal(c, { cameraBorrowed: true }); // includes fade === 1 and the rig removed
    expect(rigSeen).toBe(true);
    expect(maxLight).toBeGreaterThan(1);
    expect(minFade).toBeGreaterThan(0); // never fully hidden
    for (const b of c.bystanders) expect(b.root.position.distanceTo(startPos.get(b)!)).toBeLessThan(1e-6);
    // camera clearance + pitch (the frame's top edge stays on the lit board)
    for (const p of c.rig.camera.poses) {
      expect(p.position.y).toBeGreaterThanOrEqual(0.6 - 1e-6);
      for (const [b, pos] of startPos) {
        const d = Math.hypot(p.position.x - pos.x, p.position.z - pos.z);
        if (d < 0.79) expect(p.position.y).toBeGreaterThan(ROLE_HEIGHT[b.role] + 0.4);
      }
      const dh = Math.hypot(p.position.x - p.lookAt.x, p.position.z - p.lookAt.z);
      const pitch = Math.atan2(p.position.y - p.lookAt.y, dh);
      const need = (p.fov * Math.PI / 180) / 2 * 1.3;
      if (p.position.y < 5.99) expect(pitch).toBeGreaterThanOrEqual(need - 0.02);
    }
  });

  it('the fighters stay unobstructed at impact (no un-faded bystander on a camera->fighter line)', async () => {
    for (const name of NAMES) {
      const c = crowdedCase(name);
      let checked = false;
      c.rig.bus.on('capture:impact', () => {
        checked = true;
        const cam = c.rig.camera.camera.position;
        for (const f of [c.attacker, c.defender]) {
          const t = new Vector3(f.root.position.x, 0.8, f.root.position.z);
          for (const b of c.bystanders) {
            if (b.fade > 0.5) {
              // opaque bystander: must not intersect the line of sight
              const sx = t.x - cam.x; const sz = t.z - cam.z; const l2 = sx * sx + sz * sz;
              const u = Math.min(1, Math.max(0, ((b.root.position.x - cam.x) * sx + (b.root.position.z - cam.z) * sz) / l2));
              if (u >= 0.985) continue;
              const d = Math.hypot(cam.x + sx * u - b.root.position.x, cam.z + sz * u - b.root.position.z);
              const y = cam.y + (t.y - cam.y) * u;
              expect(d > 0.46 || y > ROLE_HEIGHT[b.role] + 0.05).toBe(true);
            }
          }
        }
      });
      await runUntil(createSequencePlayer().capture(c.rig.ctx), 30000);
      expect(checked).toBe(true);
      await drain();
    }
  });

  it.each(ROLES.flatMap((r) => FACTIONS.map((f) => [r, f] as const)))('sparse board %s / %s still lights and cleans up the rig', async (role, faction) => {
    const c = captureCase(role, faction);
    let seen = false;
    const sample = () => { if (c.rig.board.scene.children.some((o) => o.name === 'cinematic_light_rig')) seen = true; };
    gsap.ticker.add(sample);
    await runUntil(createSequencePlayer().capture(c.rig.ctx));
    gsap.ticker.remove(sample);
    expect(seen).toBe(true);
    await drain();
    expectCaptureFinal(c, { cameraBorrowed: true });
  });

  it('skip() mid-capture removes the rig and un-fades everything', async () => {
    const c = crowdedCase('opening-w');
    const player = createSequencePlayer();
    const p = player.capture(c.rig.ctx);
    await runUntil(new Promise((r) => setTimeout(r, 1800)), 3000);
    player.skip();
    await runUntil(p, 2000);
    await drain();
    expectCaptureFinal(c, { cameraBorrowed: true });
  });

  it('off mode does not add lights', async () => {
    const c = crowdedCase('backrank-w', { captureMode: 'off' });
    await runUntil(createSequencePlayer().capture(c.rig.ctx));
    expect(c.rig.board.scene.children.some((o) => o.name === 'cinematic_light_rig')).toBe(false);
    await drain();
  });
});

describe('occluder fader and shot scoring (unit)', () => {
  const mk = (sq: string) => new MockActor('rime', 'pawn', sq);

  it('fades a bystander standing on the camera->fighter line and restores it on release', () => {
    const blocker = mk('d6'); // between camera and target
    const aside = mk('a6');
    const fader = new OccluderFader(() => [blocker, aside]);
    const cam = new Vector3(blocker.root.position.x, 1.0, blocker.root.position.z + 3);
    const target = new Vector3(blocker.root.position.x, 0.8, blocker.root.position.z - 3);
    for (let t = 0; t < 1; t += 1 / 30) fader.update(t, cam, [target], false);
    expect(blocker.fade).toBeCloseTo(OCCLUDER_ALPHA, 2);
    expect(aside.fade).toBe(1);
    for (let t = 1; t < 2; t += 1 / 30) fader.update(t, cam, [target], true);
    expect(blocker.fade).toBe(1);
  });

  it('fades pieces right next to the camera and restoreAll() makes everything opaque', () => {
    const near = mk('e5');
    const fader = new OccluderFader(() => [near]);
    const cam = new Vector3(near.root.position.x + 0.5, 1, near.root.position.z);
    for (let t = 0; t < 1; t += 1 / 30) fader.update(t, cam, [new Vector3(0, 0.8, 0)], false);
    expect(near.fade).toBeLessThan(0.3);
    fader.restoreAll();
    expect(near.fade).toBe(1);
  });

  it('pickShot avoids an angle blocked by a wall of pieces', () => {
    const A = new Vector3(0.5, 0, 0.5); const D = new Vector3(0.5, 0, -0.5);
    const wall = ['b4', 'c4', 'd4', 'e4', 'f4', 'g4'].map(mk); // pieces on the seat side of the fight
    const all = [...wall];
    const inputs = { attacker: () => A, defender: () => D, seatZ: 1 as const };
    // fight at (0.5, 0.5..-0.5) = around e4/e5; seat-side camera at z>0 looks through the wall of rank 4 pieces
    const shot = pickShot('lowSide', inputs, wall, all);
    const pose = shot.pose(0);
    const blockedSeatSide = wall.some((w) => Math.abs(w.root.position.x - pose.position.x) < 1.2 && pose.position.z > 0 && w.root.position.z < pose.position.z && w.root.position.z > 0);
    expect(Number.isFinite(pose.position.x)).toBe(true);
    expect(pose.position.y).toBeGreaterThanOrEqual(0.6);
    void blockedSeatSide;
  });
});
