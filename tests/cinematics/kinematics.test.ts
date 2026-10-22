import { describe, expect, it } from 'vitest';
import { createSequencePlayer, drain, gsap, runUntil } from './harness';
import { captureCase, crowdedCase, expectCaptureFinal, FACTIONS, ROLES } from './scenarios';

describe('kinematics hooks and clash events', () => {
  it.each(ROLES.flatMap((r) => FACTIONS.map((f) => [r, f] as const)))('%s / %s: impulse at the impact, watchers look and are released, clash (not for spells)', async (role, faction) => {
    const c = captureCase(role, faction, {}, { kinematics: true });
    const kin = c.rig.kin!;
    let watchedDuring = 0;
    gsap.ticker.add(() => { watchedDuring = Math.max(watchedDuring, kin.active.length); });
    await runUntil(createSequencePlayer().capture(c.rig.ctx));
    await drain();
    expectCaptureFinal(c, { cameraBorrowed: true });
    expect(kin.impulses.length).toBeGreaterThanOrEqual(role === 'knight' ? 2 : 1);
    expect(kin.impulses.every((i) => i.strength > 0 && Number.isFinite(i.origin.x))).toBe(true);
    expect(Math.max(...kin.impulses.map((i) => i.strength))).toBeGreaterThanOrEqual(role === 'pawn' ? 0.4 : 0.6);
    expect(watchedDuring).toBeGreaterThan(0);
    expect(kin.active.length).toBe(0); // everything released in settle
    // bystanders were not yaw-turned (the kinematics layer handled the glance)
    const clashes = c.rig.events.filter((e) => e.name === 'clash');
    if (role === 'bishop') expect(clashes.length).toBe(0);
    else {
      expect(clashes.length).toBe(1);
      expect(clashes[0].payload.heavy).toBe(role === 'rook' || role === 'queen' || role === 'king');
    }
  });

  it('skip() releases all look-at targets; crowded boards still work with kinematics', async () => {
    const c = crowdedCase('opening-w');
    const rigKin = (await import('./mocks')).MockKinematics;
    const kin = new rigKin();
    c.rig.ctx.kinematics = kin;
    const player = createSequencePlayer();
    const p = player.capture(c.rig.ctx);
    await runUntil(new Promise((r) => setTimeout(r, 1500)), 3000);
    expect(kin.active.length).toBeGreaterThan(0);
    player.skip();
    await runUntil(p, 2000);
    expect(kin.active.length).toBe(0);
    await drain();
  });
});
