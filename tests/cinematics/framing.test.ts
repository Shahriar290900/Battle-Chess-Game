// Camera framing: at the moment of impact both fighters must be inside the frame and the camera above the board.
import { Vector3 } from 'three';
import { describe, expect, it } from 'vitest';
import { createSequencePlayer, drain, runUntil } from './harness';
import { captureCase, FACTIONS, ROLES } from './scenarios';

describe('framing at impact', () => {
  const cases = ROLES.flatMap((r) => FACTIONS.flatMap((f) => [16 / 9, 9 / 16].map((a) => [r, f, a] as const)));
  it.each(cases)('%s / %s / aspect %f: attacker and defender both in shot, camera above the board', async (role, faction, aspect) => {
    const c = captureCase(role, faction);
    c.rig.camera.camera.aspect = aspect;
    c.rig.camera.camera.updateProjectionMatrix();
    let seen = false;
    c.rig.bus.on('capture:impact', () => {
      seen = true;
      const cam = c.rig.camera.camera;
      cam.updateMatrixWorld(true);
      expect(cam.position.y).toBeGreaterThanOrEqual(0.6 - 1e-6);
      for (const a of [c.attacker, c.defender]) {
        for (const y of [0.25, 0.9]) { // base and torso
          const p = new Vector3(a.root.position.x, a.root.position.y + y, a.root.position.z).project(cam);
          expect(p.z).toBeLessThan(1);
          expect(Math.abs(p.x)).toBeLessThan(1.02);
          expect(Math.abs(p.y)).toBeLessThan(1.02);
        }
      }
    });
    await runUntil(createSequencePlayer().capture(c.rig.ctx));
    expect(seen).toBe(true);
    await drain();
  });
});
