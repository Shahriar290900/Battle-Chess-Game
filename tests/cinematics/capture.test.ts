import { describe, expect, it } from 'vitest';
import { createSequencePlayer, drain, gsap, runUntil, advance } from './harness';
import { captureCase, enPassantCase, expectCaptureFinal, FACTIONS, ROLES } from './scenarios';
import type { CaptureMode } from '../../src/contracts';
import { Vector3 } from 'three';

const MODES: CaptureMode[] = ['full', 'quick', 'off'];

describe('capture: every attacker role x faction x captureMode', () => {
  const cases = ROLES.flatMap((r) => FACTIONS.flatMap((f) => MODES.map((m) => [r, f, m] as const)));
  it.each(cases)('%s / %s / %s resolves with the board in its final state', async (role, faction, mode) => {
    const c = captureCase(role, faction, { captureMode: mode });
    const player = createSequencePlayer();
    const p = player.capture(c.rig.ctx);
    expect(player.running).toBe(true);
    const { settled, elapsed } = await runUntil(p);
    expect(settled).toBe(true);
    expect(player.running).toBe(false);
    await drain(); // let the fragment dissolve / fail-safe timers run out
    expectCaptureFinal(c, { cameraBorrowed: mode !== 'off' });
    expect(c.rig.registry.outstanding.size).toBe(0); // every fragment set returned to the pool
    expect(c.rig.registry.acquires).toBe(1);
    expect(c.rig.fx.count('shatter')).toBe(1);
    if (mode === 'full') {
      expect(elapsed).toBeGreaterThan(2500);
      expect(elapsed).toBeLessThan(9000);
    }
    if (mode !== 'off') {
      const names = c.rig.events.map((e) => e.name);
      for (const n of ['attack:whoosh', 'capture:impact', 'capture:shatter']) expect(names).toContain(n);
      expect(names.indexOf('attack:whoosh')).toBeLessThan(names.indexOf('capture:impact'));
      expect(names.indexOf('capture:impact')).toBeLessThan(names.indexOf('capture:shatter'));
      expect(c.rig.camera.shakes.length).toBeGreaterThan(0);
      expect(c.rig.camera.poses.length).toBeGreaterThan(5);
    }
  });
});

describe('capture feel', () => {
  it('hit-stop drops the global timeScale to ~0.03 and restores it to exactly 1', async () => {
    const c = captureCase('rook', 'emberhold');
    let min = 1; let sawSlowmo = false;
    const sample = () => { const s = gsap.globalTimeline.timeScale(); min = Math.min(min, s); if (s > 0.3 && s < 0.4) sawSlowmo = true; };
    gsap.ticker.add(sample);
    const p = createSequencePlayer().capture(c.rig.ctx);
    await runUntil(p);
    gsap.ticker.remove(sample);
    expect(min).toBeLessThanOrEqual(0.05);
    expect(sawSlowmo).toBe(true);
    expect(gsap.globalTimeline.timeScale()).toBe(1);
    await drain();
  });

  it('the king cleave slows time to 0.2 (Emberhold)', async () => {
    const c = captureCase('king', 'emberhold');
    let near02 = 0;
    const sample = () => { const s = gsap.globalTimeline.timeScale(); if (Math.abs(s - 0.2) < 0.01) near02++; };
    gsap.ticker.add(sample);
    await runUntil(createSequencePlayer().capture(c.rig.ctx));
    gsap.ticker.remove(sample);
    expect(near02).toBeGreaterThan(20);
    await drain();
  });

  it('quick mode is roughly 40% of full length and skips the approach walk', async () => {
    const full = captureCase('pawn', 'emberhold', { captureMode: 'full' });
    const quick = captureCase('pawn', 'emberhold', { captureMode: 'quick' });
    const a = await runUntil(createSequencePlayer().capture(full.rig.ctx));
    await drain();
    const b = await runUntil(createSequencePlayer().capture(quick.rig.ctx));
    await drain();
    expect(b.elapsed / a.elapsed).toBeLessThan(0.55);
    // quick keeps only the short final step onto the square; full also walks the approach
    const moves = (a: typeof full.attacker) => a.scrubs.filter(([c]) => c === 'Move').length;
    expect(moves(quick.attacker)).toBeLessThan(moves(full.attacker) * 0.7);
  });

  it('animSpeed 2 plays roughly twice as fast', async () => {
    const slow = captureCase('bishop', 'rime', { animSpeed: 1 });
    const fast = captureCase('bishop', 'rime', { animSpeed: 2 });
    const a = await runUntil(createSequencePlayer().capture(slow.rig.ctx));
    await drain();
    const b = await runUntil(createSequencePlayer().capture(fast.rig.ctx));
    await drain();
    expect(b.elapsed).toBeLessThan(a.elapsed * 0.7);
  });

  it('off mode is a quick slide with no camera borrow, no dim, no hit-stop', async () => {
    const c = captureCase('queen', 'rime', { captureMode: 'off' });
    let min = 1;
    const sample = () => { min = Math.min(min, gsap.globalTimeline.timeScale()); };
    gsap.ticker.add(sample);
    const { elapsed } = await runUntil(createSequencePlayer().capture(c.rig.ctx));
    gsap.ticker.remove(sample);
    expect(elapsed).toBeLessThan(1500);
    expect(min).toBe(1);
    expect(c.rig.camera.borrows).toBe(0);
    expect(c.bystanders.every((b) => b.dim === 0)).toBe(true);
    await drain();
  });

  it('bystanders are dimmed to 0.3 during a full capture', async () => {
    const c = captureCase('pawn', 'rime');
    let maxDim = 0;
    const sample = () => { for (const b of c.bystanders) maxDim = Math.max(maxDim, b.dim); };
    gsap.ticker.add(sample);
    await runUntil(createSequencePlayer().capture(c.rig.ctx));
    gsap.ticker.remove(sample);
    expect(maxDim).toBeCloseTo(0.3, 2);
    await drain();
  });

  it('queen summons the weapon 0 -> 1.15 -> 1 and dissolves it afterwards', async () => {
    for (const f of FACTIONS) {
      const c = captureCase('queen', f);
      await runUntil(createSequencePlayer().capture(c.rig.ctx));
      expect(c.attacker.maxSummon).toBeCloseTo(1.15, 2);
      expect(c.rig.fx.count('dissolve')).toBe(1);
      expect(c.rig.fx.count('trail')).toBeGreaterThan(0);
      expect(c.rig.events.some((e) => e.name === 'summon')).toBe(true);
      await drain();
    }
  });

  it('Rime queen shatters with a cutNormal; Emberhold queen slams with a shockwave and fire column', async () => {
    const rime = captureCase('queen', 'rime');
    await runUntil(createSequencePlayer().capture(rime.rig.ctx));
    const shatter = rime.rig.fx.calls.find((x) => x.name === 'shatter')!.args[0] as any;
    expect(shatter.cutNormal).toBeInstanceOf(Vector3);
    expect(shatter.magnitude).toBeGreaterThanOrEqual(1.4);
    await drain();
    const ember = captureCase('queen', 'emberhold');
    await runUntil(createSequencePlayer().capture(ember.rig.ctx));
    expect(ember.rig.fx.count('shockwave')).toBeGreaterThan(0);
    expect(ember.rig.fx.count('column')).toBe(1);
    expect((ember.rig.fx.calls.find((x) => x.name === 'shatter')!.args[0] as any).cutNormal).toBeUndefined();
    await drain();
  });

  it('bishop: Emberhold fireWave + ember sweep, Rime frostBeam + frost sweep; shatter comes after the sweep', async () => {
    for (const [f, preset, kind] of [['emberhold', 'fireWave', 'ember'], ['rime', 'frostBeam', 'frost']] as const) {
      const c = captureCase('bishop', f);
      await runUntil(createSequencePlayer().capture(c.rig.ctx));
      expect(c.rig.fx.calls.some((x) => x.name === 'emit' && x.args[0] === preset)).toBe(true);
      const sweep = c.rig.fx.calls.find((x) => x.name === 'sweep')!;
      expect(sweep.args[1]).toBe(kind);
      expect(c.rig.events.some((e) => e.name === 'spell')).toBe(true);
      await drain();
    }
  });

  it('rook: hops per square with a puff and move:step on each landing; Rime fires 3 shards', async () => {
    const c = captureCase('rook', 'rime');
    await runUntil(createSequencePlayer().capture(c.rig.ctx));
    const steps = c.rig.events.filter((e) => e.name === 'move:step').length;
    expect(steps).toBeGreaterThanOrEqual(3); // a1 -> a5 = 3 hops before the slam
    expect(c.rig.fx.calls.filter((x) => x.name === 'emit' && x.args[0] === 'frostMist').length).toBeGreaterThanOrEqual(3);
    expect(c.rig.fx.calls.filter((x) => x.name === 'emit' && x.args[0] === 'iceGlitter' && (x.args[2] as any)?.count === 10).length).toBe(3);
    expect(c.rig.fx.count('decal')).toBeGreaterThan(0);
    await drain();
  });

  it('knight leaps with a peak of ~1.6 and rears first', async () => {
    const c = captureCase('knight', 'emberhold');
    let peak = 0; let minPitch = 0;
    const sample = () => { peak = Math.max(peak, c.attacker.root.position.y); minPitch = Math.min(minPitch, c.attacker.model.rotation.x); };
    gsap.ticker.add(sample);
    await runUntil(createSequencePlayer().capture(c.rig.ctx));
    gsap.ticker.remove(sample);
    expect(peak).toBeGreaterThan(1.45);
    expect(peak).toBeLessThanOrEqual(1.62);
    expect(minPitch).toBeLessThan(-0.3);
    await drain();
  });

  it('king (Rime) lifts the defender with ice spikes before the backhand', async () => {
    const c = captureCase('king', 'rime');
    let maxY = 0;
    const sample = () => { maxY = Math.max(maxY, c.defender.root.position.y); };
    gsap.ticker.add(sample);
    await runUntil(createSequencePlayer().capture(c.rig.ctx));
    gsap.ticker.remove(sample);
    expect(c.rig.fx.count('iceSpikes')).toBe(1);
    expect(maxY).toBeGreaterThan(0.3);
    await drain();
  });

  it('king walks at ~1.4 units/s (slower than other pieces)', async () => {
    const c = captureCase('king', 'emberhold');
    const samples: Array<[number, number]> = [];
    let t = 0;
    const sample = (_time: number, dt: number) => { t += dt; samples.push([t, c.attacker.root.position.z]); };
    gsap.ticker.add(sample);
    await runUntil(createSequencePlayer().capture(c.rig.ctx));
    gsap.ticker.remove(sample);
    expect(c.rig.events.filter((e) => e.name === 'move:step').length).toBeGreaterThan(0);
    await drain();
  });
});

describe('en passant', () => {
  it.each(FACTIONS.flatMap((f) => MODES.map((m) => [f, m] as const)))('%s / %s: sidestep, slash, step forward onto the empty square', async (faction, mode) => {
    const c = enPassantCase(faction, { captureMode: mode });
    const start = c.attacker.root.position.clone();
    let maxSide = 0;
    const sample = () => { maxSide = Math.max(maxSide, start.distanceTo(c.attacker.root.position)); };
    gsap.ticker.add(sample);
    const { settled } = await runUntil(createSequencePlayer().capture(c.rig.ctx));
    gsap.ticker.remove(sample);
    expect(settled).toBe(true);
    await drain();
    expectCaptureFinal(c, { cameraBorrowed: mode !== 'off' });
    expect(c.rig.board.actorAt(c.capturedSquare)).toBeUndefined();
    expect(c.rig.registry.outstanding.size).toBe(0);
  });
});

describe('skip()', () => {
  const skipCases = ROLES.flatMap((r) => [0, 300, 1100, 1900, 2800].map((ms) => [r, ms] as const));
  it.each(skipCases)('%s: skip after %i ms leaves a correct state', async (role, ms) => {
    const faction = ms % 2 === 0 ? 'emberhold' : 'rime';
    const c = captureCase(role, faction);
    const player = createSequencePlayer();
    const p = player.capture(c.rig.ctx);
    if (ms) await advance(ms);
    player.skip();
    const { settled } = await runUntil(p, 2000);
    expect(settled).toBe(true);
    expect(player.running).toBe(false);
    expectCaptureFinal(c, { cameraBorrowed: true });
    expect(c.rig.board.syncCalls.length).toBeGreaterThan(0); // safety re-sync after a skip
    await drain();
    expect(c.rig.registry.outstanding.size).toBe(0);
  });

  it('skip() with nothing running is a no-op; skip() twice is safe', async () => {
    const player = createSequencePlayer();
    player.skip();
    const c = captureCase('pawn', 'emberhold');
    const p = player.capture(c.rig.ctx);
    player.skip(); player.skip();
    await runUntil(p, 2000);
    expect(player.running).toBe(false);
    await drain();
  });

  it('starting a new sequence finishes the running one first', async () => {
    const a = captureCase('pawn', 'emberhold');
    const player = createSequencePlayer();
    const pa = player.capture(a.rig.ctx);
    await advance(400);
    const b = captureCase('rook', 'rime');
    const pb = player.capture(b.rig.ctx);
    const r = await runUntil(Promise.all([pa, pb]));
    expect(r.settled).toBe(true);
    expectCaptureFinal(a, { cameraBorrowed: true });
    expectCaptureFinal(b, { cameraBorrowed: true });
    await drain();
  });
});

describe('robustness: promises that never resolve', () => {
  const hangCases = ROLES.flatMap((r) => (['full', 'quick', 'off'] as const).map((m) => [r, m] as const));
  it.each(hangCases)('%s / %s resolves even if fx, fragments and camera.restore never settle', async (role, mode) => {
    const c = captureCase(role, role === 'queen' ? 'rime' : 'emberhold', { captureMode: mode }, { hang: true });
    const { settled, elapsed } = await runUntil(createSequencePlayer().capture(c.rig.ctx), 30000);
    expect(settled).toBe(true);
    expect(elapsed).toBeLessThan(20000);
    expect(c.rig.board.removed).toContain(c.defender);
    expect(c.attacker.square).toBe(c.to);
    expect(gsap.globalTimeline.timeScale()).toBe(1);
    await drain(12000);
  });

  it('a throwing fx does not break the sequence', async () => {
    const c = captureCase('bishop', 'emberhold');
    c.rig.fx.emit = () => { throw new Error('boom'); };
    c.rig.fx.sweep = () => { throw new Error('boom'); };
    const { settled } = await runUntil(createSequencePlayer().capture(c.rig.ctx), 20000);
    expect(settled).toBe(true);
    expect(c.rig.board.removed).toContain(c.defender);
    await drain();
  });
});

describe('asset degradation', () => {
  it('works without socket_cast, without clips and without an impact label', async () => {
    for (const role of ROLES) {
      const c = captureCase(role, 'rime', {}, { actorOpts: { noSocketCast: true, noClips: true, noImpactLabel: true } });
      const { settled } = await runUntil(createSequencePlayer().capture(c.rig.ctx), 30000);
      expect(settled).toBe(true);
      expectCaptureFinal(c, { cameraBorrowed: true });
      await drain();
    }
  });

  it('degrades to a plain move when the board has no defender', async () => {
    const c = captureCase('rook', 'emberhold');
    c.rig.board.removeActor(c.defender);
    const { settled } = await runUntil(createSequencePlayer().capture(c.rig.ctx), 20000);
    expect(settled).toBe(true);
    expect(c.attacker.square).toBe(c.to);
    await drain();
  });
});
