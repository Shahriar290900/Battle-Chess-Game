import { describe, expect, it } from 'vitest';
import type { Faction, Role, Side } from '../../src/contracts';
import { restYaw } from '../../src/contracts';
import { createSequencePlayer, drain, gsap, runUntil } from './harness';
import { makeRig, mkMove, type MockActor } from './mocks';
import { ROLES, yawEq } from './scenarios';
import type { CaptureMode } from '../../src/contracts';
import { addBystanders } from './scenarios';

// checker square -> king square (king is on e8 for Emberhold checkers, e1 for Rime checkers)
const CHECKERS: Record<Role, [string, string]> = {
  pawn: ['d7', 'e8'], rook: ['e4', 'e8'], knight: ['d6', 'e8'], bishop: ['h5', 'e8'], queen: ['e5', 'e8'], king: ['e7', 'e8'],
};

function checkRig(role: Role, faction: Faction, mode: CaptureMode, extra: Parameters<typeof makeRig>[3] = {}) {
  const side: Side = faction === 'emberhold' ? 'w' : 'b';
  const [from, ksqW] = CHECKERS[role];
  // mirror for Rime checkers
  const mirror = (sq: string) => (side === 'w' ? sq : sq[0] + String(9 - Number(sq[1])));
  const cSq = mirror(from); const kSq = mirror(ksqW);
  let checker!: MockActor; let king!: MockActor;
  const rig = makeRig(mkMove({ from: cSq, to: cSq, side, role, check: true }), (b) => {
    checker = b.add(faction, role, cSq); king = b.add(faction === 'emberhold' ? 'rime' : 'emberhold', 'king', kSq);
    addBystanders(b, [cSq, kSq]);
  }, { captureMode: mode }, { seatZ: side === 'w' ? 1 : -1, ...extra });
  return { rig, checker, king, kSq, side };
}

describe('check provoke', () => {
  const cases = ROLES.flatMap((r) => (['emberhold', 'rime'] as Faction[]).flatMap((f) => [true, false].map((taunt) => [r, f, taunt] as const)));
  it.each(cases)('%s / %s (Taunt clip: %s): provokes, king looks back and recoils, everything released', async (role, faction, taunt) => {
    const { rig, checker, king, kSq, side } = checkRig(role, faction, 'full', { kinematics: true, actorOpts: { noTaunt: !taunt } });
    let faced = false; let kingLooked = false;
    const sample = () => {
      if (!yawEq(checker.getYaw(), restYaw(side), 0.2)) faced = true;
      if (rig.kin!.looks.get(king)) kingLooked = true;
    };
    gsap.ticker.add(sample);
    const { settled, elapsed } = await runUntil(createSequencePlayer().check(rig.ctx, kSq), 15000);
    gsap.ticker.remove(sample);
    expect(settled).toBe(true);
    expect(elapsed).toBeGreaterThan(1200); // a real beat, not a blink
    expect(elapsed).toBeLessThan(4500);
    await drain();
    expect(kingLooked).toBe(true);
    expect(rig.kin!.active.length).toBe(0); // look-at released
    expect(faced || role === 'rook' || role === 'queen' || role === 'king' || role === 'pawn').toBe(true);
    if (taunt) expect(checker.clipsPlayed).toContain('Taunt');
    else expect(checker.clipsPlayed).not.toContain('Taunt');
    expect(rig.events.some((e) => e.name === 'taunt' && e.payload.role === role)).toBe(true);
    expect(rig.fx.count('aura')).toBeGreaterThanOrEqual(2);
    expect(rig.fx.calls.find((c) => c.name === 'aura')!.args[1]).toBe(king.faction);
    expect(rig.board.tints[0][1]).not.toBeNull();
    expect(rig.board.tints[rig.board.tints.length - 1]).toEqual([kSq, null]);
    expect(rig.camera.borrows).toBe(1);
    expect(rig.camera.state).toBe('seat');
    expect(rig.camera.poses.every((p) => p.position.y >= 0.6 - 1e-6)).toBe(true);
    expect(yawEq(checker.getYaw(), restYaw(side))).toBe(true);
    expect(yawEq(king.getYaw(), restYaw(side === 'w' ? 'b' : 'w'))).toBe(true);
    expect(checker.model.rotation.x).toBeCloseTo(0, 5);
    expect(king.model.rotation.x).toBeCloseTo(0, 5);
    expect(checker.summon).toBe(0);
    expect(checker.fade).toBe(1);
    expect(rig.board.scene.children.some((o) => o.name === 'cinematic_light_rig')).toBe(false);
    expect(gsap.globalTimeline.timeScale()).toBe(1);
    expect(gsap.getTweensOf([checker.root.position, checker.model.rotation, king.model.rotation]).length).toBe(0);
  });

  it('works without kinematics (yaw fallback) and quick mode is shorter', async () => {
    const full = checkRig('knight', 'emberhold', 'full');
    const quick = checkRig('knight', 'emberhold', 'quick');
    const a = await runUntil(createSequencePlayer().check(full.rig.ctx, full.kSq));
    await drain();
    const b = await runUntil(createSequencePlayer().check(quick.rig.ctx, quick.kSq));
    await drain();
    expect(b.elapsed).toBeLessThan(a.elapsed * 0.7);
    expect(quick.rig.camera.borrows).toBe(1);
    expect(yawEq(full.king.getYaw(), restYaw('b'))).toBe(true);
  });

  it('off mode: aura and tile glow only, no camera borrow', async () => {
    const { rig, kSq } = checkRig('bishop', 'rime', 'off');
    const { settled, elapsed } = await runUntil(createSequencePlayer().check(rig.ctx, kSq));
    expect(settled).toBe(true);
    expect(elapsed).toBeLessThan(1500);
    expect(rig.camera.borrows).toBe(0);
    expect(rig.fx.count('aura')).toBe(1);
    expect(rig.board.tints[rig.board.tints.length - 1]).toEqual([kSq, null]);
    await drain();
  });

  it('skip() mid-provoke snaps the camera back and releases the look-at', async () => {
    const { rig, kSq, king } = checkRig('queen', 'emberhold', 'full', { kinematics: true });
    const player = createSequencePlayer();
    const p = player.check(rig.ctx, kSq);
    await runUntil(new Promise((r) => setTimeout(r, 700)), 2000);
    player.skip();
    expect((await runUntil(p, 2000)).settled).toBe(true);
    expect(rig.camera.state).toBe('seat');
    expect(rig.kin!.looks.get(king)).toBeNull();
    expect(rig.board.tints[rig.board.tints.length - 1]).toEqual([kSq, null]);
    await drain();
  });

  it('resolves with hanging fx / camera', async () => {
    const { rig, kSq } = checkRig('rook', 'rime', 'full', { hang: true });
    expect((await runUntil(createSequencePlayer().check(rig.ctx, kSq), 20000)).settled).toBe(true);
    await drain(12000);
  });
});
