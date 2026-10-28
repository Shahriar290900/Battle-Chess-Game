// Audio cue emission (contract v1.4): move:slide is balanced (every start has a stop, also under skip),
// and fights carry shield / armour / land beats at the right moments.
import { describe, expect, it } from 'vitest';
import { createSequencePlayer, drain, runUntil, advance } from './harness';
import { captureCase, FACTIONS, ROLES } from './scenarios';
import { makeRig, mkMove, type Rig } from './mocks';
import type { CaptureMode, Faction, Role, Side } from '../../src/contracts';

/** Track the open slide loops: key -> open count; returns problems. */
function slideBalance(rig: Rig): { open: number; starts: number; stops: number; badStop: number } {
  const open = new Map<string, number>();
  let starts = 0; let stops = 0; let badStop = 0;
  for (const e of rig.events) {
    if (e.name !== 'move:slide') continue;
    const k = `${e.payload.faction}:${e.payload.role}`;
    if (e.payload.phase === 'start') { starts++; open.set(k, (open.get(k) ?? 0) + 1); expect(e.payload.speed).toBeGreaterThan(0); }
    else { stops++; if (!open.get(k)) badStop++; open.set(k, 0); }
  }
  return { open: [...open.values()].filter((n) => n > 0).length, starts, stops, badStop };
}
const names = (rig: Rig) => rig.events.map((e) => e.name);

describe('move:slide balance', () => {
  const MODES: CaptureMode[] = ['full', 'quick', 'off'];
  const cases = ROLES.flatMap((r) => FACTIONS.flatMap((f) => MODES.map((m) => [r, f, m] as const)));
  it.each(cases)('%s / %s / %s capture leaves no slide loop open', async (role, faction, mode) => {
    const c = captureCase(role, faction, { captureMode: mode });
    const { settled } = await runUntil(createSequencePlayer().capture(c.rig.ctx));
    expect(settled).toBe(true);
    await drain();
    const b = slideBalance(c.rig);
    expect(b.open).toBe(0);
    expect(b.badStop).toBe(0);
  });

  it.each(ROLES.flatMap((r) => FACTIONS.map((f) => [r, f] as const)))('%s / %s skipped mid-capture stops every slide', async (role, faction) => {
    const c = captureCase(role, faction, { captureMode: 'full' });
    const player = createSequencePlayer();
    const p = player.capture(c.rig.ctx);
    await advance(700);
    player.skip();
    const { settled } = await runUntil(p);
    expect(settled).toBe(true);
    await drain();
    expect(slideBalance(c.rig).open).toBe(0);
  });

  it.each(ROLES)('plain %s move glides (or hops/leaps) and ends silent', async (role) => {
    const faction: Faction = 'emberhold';
    const side: Side = 'w';
    const [from, to] = role === 'knight' ? ['b1', 'c3'] : role === 'rook' ? ['a1', 'a4'] : role === 'bishop' ? ['c1', 'f4'] : role === 'queen' ? ['d1', 'd4'] : role === 'king' ? ['e1', 'e2'] : ['e2', 'e4'];
    const rig = makeRig(mkMove({ from, to, side, role }), (b) => { b.add(faction, role, from); });
    const { settled } = await runUntil(createSequencePlayer().move(rig.ctx));
    expect(settled).toBe(true);
    const b = slideBalance(rig);
    expect(b.open).toBe(0);
    if (role === 'knight') { expect(b.starts).toBe(0); expect(names(rig)).toContain('land'); }
    else if (role === 'rook') { expect(b.starts).toBe(0); expect(rig.events.filter((e) => e.name === 'land').length).toBe(3); }
    else { expect(b.starts).toBe(1); expect(b.stops).toBe(1); }
    await drain();
  });

  it('a skipped plain move stops its slide', async () => {
    const rig = makeRig(mkMove({ from: 'e2', to: 'e5', side: 'w', role: 'queen' }), (b) => { b.add('emberhold', 'queen', 'e2'); });
    const player = createSequencePlayer();
    const p = player.move(rig.ctx);
    await advance(400);
    expect(rig.events.some((e) => e.name === 'move:slide' && e.payload.phase === 'start')).toBe(true);
    player.skip();
    await runUntil(p);
    expect(slideBalance(rig).open).toBe(0);
    await drain();
  });

  it('castling slides the king and lands the rook', async () => {
    const rig = makeRig(mkMove({ from: 'e1', to: 'g1', side: 'w', role: 'king', isCastle: true, rookFrom: 'h1', rookTo: 'f1' }), (b) => { b.add('emberhold', 'king', 'e1'); b.add('emberhold', 'rook', 'h1'); });
    await runUntil(createSequencePlayer().castle(rig.ctx), 20000);
    expect(slideBalance(rig).open).toBe(0);
    expect(slideBalance(rig).starts).toBeGreaterThan(0);
    expect(rig.events.some((e) => e.name === 'land' && e.payload.role === 'rook')).toBe(true);
    await drain();
  });
});

describe('fight beats', () => {
  it.each(FACTIONS)('%s pawn defender: shield flash before the hit, shield break at the shatter', async (def) => {
    const attackerFaction: Faction = def === 'emberhold' ? 'rime' : 'emberhold';
    const c = captureCase('knight', attackerFaction, { captureMode: 'full' }, {}, 'pawn');
    await runUntil(createSequencePlayer().capture(c.rig.ctx));
    const n = names(c.rig);
    const flash = n.indexOf('shield:flash'); const brk = n.indexOf('shield:break');
    expect(flash).toBeGreaterThanOrEqual(0);
    expect(flash).toBeLessThan(n.indexOf('capture:impact'));
    expect(brk).toBeGreaterThan(n.indexOf('capture:impact'));
    expect(c.rig.events.find((e) => e.name === 'shield:break')!.payload.faction).toBe(def);
    await drain();
  });

  it('a non-shield defender never flashes or breaks a shield', async () => {
    const c = captureCase('rook', 'emberhold', { captureMode: 'full' }, {}, 'queen');
    await runUntil(createSequencePlayer().capture(c.rig.ctx));
    expect(names(c.rig)).not.toContain('shield:break');
    expect(names(c.rig)).not.toContain('shield:flash');
    await drain();
  });

  it('off mode still announces the shield for a pawn defender', async () => {
    const c = captureCase('rook', 'rime', { captureMode: 'off' }, {}, 'pawn');
    await runUntil(createSequencePlayer().capture(c.rig.ctx));
    expect(names(c.rig)).toContain('shield:flash');
    expect(names(c.rig)).toContain('shield:break');
    await drain();
  });

  const BEATS: Array<[Role, Faction, string]> = [
    ['rook', 'emberhold', 'land'], ['rook', 'rime', 'armour:hit'], ['knight', 'emberhold', 'land'], ['knight', 'rime', 'armour:hit'],
    ['queen', 'emberhold', 'land'], ['queen', 'rime', 'armour:hit'], ['king', 'rime', 'armour:hit'], ['bishop', 'emberhold', 'armour:hit'],
    ['bishop', 'rime', 'armour:hit'], ['pawn', 'emberhold', 'armour:hit'],
  ];
  it.each(BEATS)('%s / %s fight carries %s', async (role, faction, ev) => {
    const c = captureCase(role, faction, { captureMode: 'full' });
    await runUntil(createSequencePlayer().capture(c.rig.ctx));
    expect(names(c.rig)).toContain(ev);
    await drain();
  });
});
