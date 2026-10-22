import { describe, expect, it } from 'vitest';
import type { Faction } from '../../src/contracts';
import { advance, createSequencePlayer, drain, gsap, runUntil } from './harness';
import { makeRig, mkMove, type MockActor } from './mocks';
import { addBystanders } from './scenarios';

function mateRig(kfac: Faction, extra: Parameters<typeof makeRig>[3] = {}) {
  const wfac: Faction = kfac === 'emberhold' ? 'rime' : 'emberhold';
  const ksq = kfac === 'emberhold' ? 'e1' : 'e8';
  let king!: MockActor; let queen!: MockActor;
  const rig = makeRig(mkMove({ from: 'd1', to: 'd7', side: wfac === 'emberhold' ? 'w' : 'b', role: 'queen', mate: true }), (b) => {
    king = b.add(kfac, 'king', ksq); queen = b.add(wfac, 'queen', 'd7'); b.add(wfac, 'rook', 'a7');
    addBystanders(b, [ksq, 'd7', 'a7']); // pawn rows of both sides: the losing side's pawns also surrender
  }, {}, { seatZ: kfac === 'emberhold' ? -1 : 1, ...extra });
  const losers = rig.board.allActors().filter((a) => a.faction === kfac && a !== king);
  const winners = rig.board.allActors().filter((a) => a.faction === wfac);
  return { rig, king, queen, ksq, losers, winners };
}

describe('checkmate: the king surrenders, the losing side drops its weapons', () => {
  const cases = (['emberhold', 'rime'] as Faction[]).flatMap((f) => [true, false].map((clip) => [f, clip] as const));
  it.each(cases)('%s king (Surrender clip: %s)', async (kfac, clip) => {
    const { rig, king, ksq, losers, winners } = mateRig(kfac, { kinematics: true, actorOpts: { noSurrender: !clip } });
    const positions = new Map([king, ...losers].map((a) => [a, a.root.position.clone()]));
    let minScale = 1; const dropTimes: number[] = []; let t = 0;
    rig.bus.on('weapon:drop', () => dropTimes.push(t));
    const sample = (_x: number, dt: number) => { t += dt; minScale = Math.min(minScale, gsap.globalTimeline.timeScale()); };
    gsap.ticker.add(sample);
    const { settled, elapsed } = await runUntil(createSequencePlayer().checkmate(rig.ctx, ksq), 30000);
    gsap.ticker.remove(sample);
    expect(settled).toBe(true);
    expect(elapsed).toBeGreaterThan(4000);
    expect(minScale).toBeLessThan(0.7);
    await drain();
    // nothing shattered or removed
    expect(rig.board.removed).not.toContain(king);
    expect(rig.board.actorAt(ksq)).toBe(king);
    expect(rig.fx.count('shatter')).toBe(0);
    expect(rig.registry.acquires).toBe(0);
    // the king and every remaining losing piece surrendered (one weapon:drop each) + one surrender event
    expect(rig.events.filter((e) => e.name === 'surrender').length).toBe(1);
    expect(rig.events.find((e) => e.name === 'surrender')!.payload.side).toBe(king.side);
    const drops = rig.events.filter((e) => e.name === 'weapon:drop');
    expect(drops.length).toBe(1 + losers.length);
    expect(drops.every((d) => d.payload.faction === kfac)).toBe(true);
    // staggered: drops are spread out in time
    expect(dropTimes[dropTimes.length - 1] - dropTimes[0]).toBeGreaterThan(0.8);
    // final held pose
    for (const a of [king, ...losers]) {
      if (clip) {
        expect(a.playing).toBe('Surrender');
        expect(a.scrubs.some(([c]) => c === 'Surrender')).toBe(true);
        expect(a.scrubs[a.scrubs.length - 1][1]).toBeCloseTo(a.clipDuration('Surrender'), 1);
      } else {
        expect(a.model.position.y).toBeLessThan(-0.1);
        expect(a.model.rotation.x).toBeGreaterThan(0.2);
      }
      expect(a.root.position.distanceTo(positions.get(a)!)).toBeLessThan(1e-6);
    }
    expect(king.model.position.y <= (clip ? 0 : -0.3)).toBe(true);
    // winners raised their weapons (Victory) and looked at the king, released afterwards
    expect(winners.some((w) => w.clipsPlayed.includes('Victory'))).toBe(true);
    expect(rig.kin!.lookCalls).toBeGreaterThan(0);
    expect(rig.kin!.active.length).toBe(0);
    // camera: borrowed once, a full orbit around the king, restored
    expect(rig.camera.borrows).toBe(1);
    expect(rig.camera.state).toBe('seat');
    const angles = rig.camera.poses.map((p) => Math.atan2(p.position.x - king.root.position.x, p.position.z - king.root.position.z));
    let total = 0;
    for (let i = 1; i < angles.length; i++) total += Math.atan2(Math.sin(angles[i] - angles[i - 1]), Math.cos(angles[i] - angles[i - 1]));
    expect(Math.abs(total)).toBeGreaterThan(Math.PI * 1.4);
    expect(rig.board.scene.children.some((o) => o.name === 'cinematic_light_rig')).toBe(false);
    expect(gsap.globalTimeline.timeScale()).toBe(1);
    for (const b of rig.board.allActors()) expect(b.fade).toBe(1);
  });

  it('skip() mid-sequence still leaves everyone surrendered; hanging fx still resolves', async () => {
    for (const hang of [false, true]) {
      const { rig, king, ksq, losers } = mateRig('rime', { hang, actorOpts: { noSurrender: true } });
      const player = createSequencePlayer();
      const p = player.checkmate(rig.ctx, ksq);
      if (!hang) { await advance(1200); player.skip(); }
      expect((await runUntil(p, 30000)).settled).toBe(true);
      for (const a of [king, ...losers]) {
        expect(a.model.position.y).toBeLessThan(-0.1 + 1e-9);
      }
      expect(rig.board.removed).not.toContain(king);
      if (!hang) expect(rig.camera.state).toBe('seat');
      expect(gsap.globalTimeline.timeScale()).toBe(1);
      await drain(12000);
    }
  });
});
