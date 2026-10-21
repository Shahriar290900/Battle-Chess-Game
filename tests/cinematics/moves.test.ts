import { Vector3 } from 'three';
import { describe, expect, it } from 'vitest';
import type { Faction, PromotionRole, Role, Side, Square } from '../../src/contracts';
import { restYaw, squareToWorld } from '../../src/contracts';
import { advance, createSequencePlayer, drain, gsap, runUntil } from './harness';
import { makeRig, mkMove, type MockActor } from './mocks';
import { addBystanders, FACTIONS, ROLES, yawEq } from './scenarios';

const MOVES: Record<Role, Record<Side, [Square, Square]>> = {
  pawn: { w: ['e2', 'e4'], b: ['d7', 'd5'] },
  rook: { w: ['a1', 'a4'], b: ['h8', 'h5'] },
  knight: { w: ['g1', 'f3'], b: ['b8', 'c6'] },
  bishop: { w: ['c1', 'f4'], b: ['f8', 'c5'] },
  queen: { w: ['d1', 'g4'], b: ['d8', 'g5'] },
  king: { w: ['e1', 'e2'], b: ['e8', 'e7'] },
};

function expectOnSquare(a: MockActor, sq: Square, side: Side) {
  const p = squareToWorld(sq, new Vector3());
  expect(a.root.position.x).toBeCloseTo(p.x, 5);
  expect(a.root.position.z).toBeCloseTo(p.z, 5);
  expect(a.root.position.y).toBeCloseTo(0, 5);
  expect(yawEq(a.getYaw(), restYaw(side))).toBe(true);
  expect(a.square).toBe(sq);
  expect(a.model.rotation.x).toBeCloseTo(0, 5);
  expect(gsap.getTweensOf([a.root.position, a.root.rotation, a.model.rotation]).length).toBe(0);
}

describe('plain moves', () => {
  const cases = ROLES.flatMap((r) => FACTIONS.map((f) => [r, f] as const));
  it.each(cases)('%s / %s walks, hops or leaps to the target square', async (role, faction: Faction) => {
    const side: Side = faction === 'emberhold' ? 'w' : 'b';
    const [from, to] = MOVES[role][side];
    let actor!: MockActor;
    const rig = makeRig(mkMove({ from, to, side, role }), (b) => { actor = b.add(faction, role, from); addBystanders(b, [from, to]); });
    const player = createSequencePlayer();
    const start = actor.root.position.clone();
    let maxY = 0; let turned = false;
    const sample = () => { maxY = Math.max(maxY, actor.root.position.y); if (!yawEq(actor.getYaw(), restYaw(side))) turned = true; };
    gsap.ticker.add(sample);
    const { settled } = await runUntil(player.move(rig.ctx), 20000);
    gsap.ticker.remove(sample);
    expect(settled).toBe(true);
    expectOnSquare(actor, to, side);
    expect(rig.board.actorAt(to)).toBe(actor);
    if (role === 'knight') expect(turned).toBe(true); // leaps along the L, not the rest facing
    expect(rig.camera.borrows).toBe(0); // moves never borrow the camera
    expect(rig.events.filter((e) => e.name === 'move:step').length).toBeGreaterThan(0);
    if (role === 'rook') expect(maxY).toBeGreaterThan(0.2);
    if (role === 'knight') expect(maxY).toBeGreaterThan(1.1);
    if (role === 'pawn' || role === 'queen') expect(maxY).toBe(0);
    expect(start.distanceTo(actor.root.position)).toBeGreaterThan(0.9);
    await drain();
  });

  it('rook hops once per square (0.25 s each)', async () => {
    let actor!: MockActor;
    const rig = makeRig(mkMove({ from: 'a1', to: 'a5', side: 'w', role: 'rook' }), (b) => { actor = b.add('emberhold', 'rook', 'a1'); });
    await runUntil(createSequencePlayer().move(rig.ctx));
    expect(rig.events.filter((e) => e.name === 'move:step').length).toBe(4);
    expect(actor.square).toBe('a5');
    await drain();
  });

  it('king walks slower than a pawn', async () => {
    const time = async (role: Role) => {
      const [from, to] = role === 'king' ? ['e1', 'e3'] : ['e2', 'e4'];
      const rig = makeRig(mkMove({ from, to, side: 'w', role }), (b) => { b.add('emberhold', role, from); });
      const { elapsed } = await runUntil(createSequencePlayer().move(rig.ctx));
      await drain();
      return elapsed;
    };
    expect(await time('king')).toBeGreaterThan((await time('pawn')) * 1.3);
  });

  it('animSpeed scales move time; skip() snaps to the final state', async () => {
    let actor!: MockActor;
    const rig = makeRig(mkMove({ from: 'd1', to: 'd7', side: 'w', role: 'queen' }), (b) => { actor = b.add('emberhold', 'queen', 'd1'); });
    const player = createSequencePlayer();
    const p = player.move(rig.ctx);
    await advance(500);
    player.skip();
    expect((await runUntil(p, 1000)).settled).toBe(true);
    expectOnSquare(actor, 'd7', 'w');
    expect(rig.board.syncCalls.length).toBe(1);
    await drain();
  });

  it('resolves even when the piece is missing', async () => {
    const rig = makeRig(mkMove({ from: 'd1', to: 'd7', side: 'w', role: 'queen' }), () => {});
    expect((await runUntil(createSequencePlayer().move(rig.ctx), 1000)).settled).toBe(true);
    expect(rig.board.syncCalls.length).toBe(1);
  });
});

describe('castling', () => {
  const cases: Array<[Faction, string, string, string, string]> = [
    ['emberhold', 'e1', 'g1', 'h1', 'f1'], ['emberhold', 'e1', 'c1', 'a1', 'd1'],
    ['rime', 'e8', 'g8', 'h8', 'f8'], ['rime', 'e8', 'c8', 'a8', 'd8'],
  ];
  it.each(cases)('%s king %s->%s with rook %s->%s', async (faction, kf, kt, rf, rt) => {
    const side: Side = faction === 'emberhold' ? 'w' : 'b';
    let king!: MockActor; let rook!: MockActor;
    const rig = makeRig(mkMove({ from: kf, to: kt, side, role: 'king', isCastle: true, rookFrom: rf, rookTo: rt }), (b) => {
      king = b.add(faction, 'king', kf); rook = b.add(faction, 'rook', rf); addBystanders(b, [kf, kt, rf, rt]);
    });
    let worst = Infinity; let sampled = 0;
    const sample = () => {
      sampled++;
      const h = Math.hypot(king.root.position.x - rook.root.position.x, king.root.position.z - rook.root.position.z);
      // pieces are ~0.8 wide: whenever they overlap horizontally the rook must be above the king (1.7 tall)
      if (h < 0.8) worst = Math.min(worst, rook.root.position.y);
    };
    gsap.ticker.add(sample);
    const { settled } = await runUntil(createSequencePlayer().castle(rig.ctx), 20000);
    gsap.ticker.remove(sample);
    expect(settled).toBe(true);
    expectOnSquare(king, kt, side);
    expectOnSquare(rook, rt, side);
    expect(rig.board.actorAt(kt)).toBe(king);
    expect(rig.board.actorAt(rt)).toBe(rook);
    expect(worst).toBeGreaterThanOrEqual(1.7); // the rook clears the king when they cross
    expect(rig.events.some((e) => e.name === 'castle')).toBe(true);
    expect(rig.camera.borrows).toBe(0);
    await drain();
  });
});

describe('promotion', () => {
  const roles: PromotionRole[] = ['queen', 'rook', 'bishop', 'knight'];
  const cases = FACTIONS.flatMap((f) => roles.map((r) => [f, r] as const));
  it.each(cases)('%s pawn promotes to %s', async (faction, role) => {
    const side: Side = faction === 'emberhold' ? 'w' : 'b';
    const sq = side === 'w' ? 'e8' : 'e1';
    let pawn!: MockActor;
    const rig = makeRig(mkMove({ from: side === 'w' ? 'e7' : 'e2', to: sq, side, role: 'pawn', promotion: role }), (b) => { pawn = b.add(faction, 'pawn', sq); });
    const { settled } = await runUntil(createSequencePlayer().promote(rig.ctx, role), 20000);
    expect(settled).toBe(true);
    expect(rig.board.removed).toContain(pawn);
    expect(rig.board.spawned.length).toBe(1);
    const np = rig.board.actorAt(sq)!;
    expect(np.role).toBe(role);
    expect(np.faction).toBe(faction);
    expect(yawEq(np.getYaw(), restYaw(side))).toBe(true);
    expect(rig.fx.count('column')).toBe(1);
    expect((np as MockActor).clipsPlayed).toContain('Victory');
    expect(rig.events.some((e) => e.name === 'promotion')).toBe(true);
    await drain();
  });

  it('skip() mid-column still reveals the promoted piece', async () => {
    let pawn!: MockActor;
    const rig = makeRig(mkMove({ from: 'e7', to: 'e8', side: 'w', role: 'pawn', promotion: 'queen' }), (b) => { pawn = b.add('emberhold', 'pawn', 'e8'); });
    const player = createSequencePlayer();
    const p = player.promote(rig.ctx, 'queen');
    await advance(200);
    player.skip();
    await runUntil(p, 1000);
    expect(rig.board.removed).toContain(pawn);
    expect(rig.board.actorAt('e8')!.role).toBe('queen');
    expect(rig.board.spawned.length).toBe(1);
    await drain();
  });

  it('capture-promotion: capture first, then promote (both resolve, one queen spawned)', async () => {
    let pawn!: MockActor; let victim!: MockActor;
    const mv = mkMove({ from: 'e7', to: 'd8', side: 'w', role: 'pawn', captured: 'queen', capturedSquare: 'd8', promotion: 'queen' });
    const rig = makeRig(mv, (b) => { pawn = b.add('emberhold', 'pawn', 'e7'); victim = b.add('rime', 'queen', 'd8'); });
    const player = createSequencePlayer();
    expect((await runUntil(player.capture(rig.ctx))).settled).toBe(true);
    expect(rig.board.removed).toContain(victim);
    expect(rig.board.actorAt('d8')).toBe(pawn);
    expect((await runUntil(player.promote(rig.ctx, 'queen'))).settled).toBe(true);
    expect(rig.board.actorAt('d8')!.role).toBe('queen');
    await drain();
  });
});

describe('check / checkmate / stalemate', () => {
  it.each(FACTIONS)('check by %s: glance, aura at the king head, tile tint cleared, no camera borrow', async (faction) => {
    const side: Side = faction === 'emberhold' ? 'w' : 'b';
    const kfac: Faction = faction === 'emberhold' ? 'rime' : 'emberhold';
    const ksq = side === 'w' ? 'e8' : 'e1';
    let checker!: MockActor; let king!: MockActor;
    const rig = makeRig(mkMove({ from: 'a1', to: side === 'w' ? 'a8' : 'a2', side, role: 'rook', check: true }), (b) => {
      checker = b.add(faction, 'rook', side === 'w' ? 'a8' : 'a2'); king = b.add(kfac, 'king', ksq);
    });
    let glanced = false;
    const sample = () => { if (!yawEq(checker.getYaw(), restYaw(side), 0.05)) glanced = true; };
    gsap.ticker.add(sample);
    const { settled } = await runUntil(createSequencePlayer().check(rig.ctx, ksq), 10000);
    gsap.ticker.remove(sample);
    expect(settled).toBe(true);
    expect(glanced).toBe(true);
    expect(rig.fx.count('aura')).toBeGreaterThan(0);
    expect(rig.fx.calls.find((c) => c.name === 'aura')!.args[1]).toBe(kfac);
    expect(rig.board.tints[0][0]).toBe(ksq);
    expect(rig.board.tints[0][1]).not.toBeNull();
    expect(rig.board.tints[rig.board.tints.length - 1]).toEqual([ksq, null]);
    expect(rig.camera.borrows).toBe(0);
    expect(yawEq(checker.getYaw(), restYaw(side))).toBe(true);
    expect(king.playing).toBe('Idle');
    await drain();
  });

  it.each(FACTIONS)('checkmate of the %s king: orbit, kneel, crumble in slow motion, winners celebrate', async (kfac) => {
    const wfac: Faction = kfac === 'emberhold' ? 'rime' : 'emberhold';
    const ksq = kfac === 'emberhold' ? 'e1' : 'e8';
    let king!: MockActor; let queen!: MockActor;
    const rig = makeRig(mkMove({ from: 'd1', to: 'd7', side: wfac === 'emberhold' ? 'w' : 'b', role: 'queen', mate: true }), (b) => {
      king = b.add(kfac, 'king', ksq); queen = b.add(wfac, 'queen', 'd7'); b.add(wfac, 'rook', 'a7'); addBystanders(b, [ksq, 'd7', 'a7']);
    }, {}, { seatZ: kfac === 'emberhold' ? -1 : 1 });
    const positions: number[] = [];
    let minScale = 1;
    const sample = () => { minScale = Math.min(minScale, gsap.globalTimeline.timeScale()); };
    gsap.ticker.add(sample);
    rig.camera.poses = positions as any;
    const { settled, elapsed } = await runUntil(createSequencePlayer().checkmate(rig.ctx, ksq), 30000);
    gsap.ticker.remove(sample);
    expect(settled).toBe(true);
    expect(elapsed).toBeGreaterThan(4000);
    expect(minScale).toBeLessThan(0.5);
    expect(gsap.globalTimeline.timeScale()).toBe(1);
    expect(rig.board.removed).toContain(king);
    expect(rig.camera.borrows).toBe(1);
    expect(rig.camera.state).toBe('seat');
    expect(rig.fx.count('shatter')).toBe(1);
    expect(rig.fx.count('sweep')).toBe(1);
    expect(queen.clipsPlayed).toContain('Victory');
    // the orbit goes a full circle around the king
    const angles = (rig.camera.poses as any[]).map((p) => Math.atan2(p.position.x - king.root.position.x, p.position.z - king.root.position.z));
    let total = 0;
    for (let i = 1; i < angles.length; i++) total += Math.atan2(Math.sin(angles[i] - angles[i - 1]), Math.cos(angles[i] - angles[i - 1]));
    expect(Math.abs(total)).toBeGreaterThan(Math.PI * 1.4);
    await drain();
    expect(rig.registry.outstanding.size).toBe(0);
  });

  it('checkmate resolves with hanging fx and when skipped', async () => {
    for (const hang of [true, false]) {
      let king!: MockActor;
      const rig = makeRig(mkMove({ from: 'd1', to: 'd7', side: 'w', role: 'queen', mate: true }), (b) => { king = b.add('rime', 'king', 'e8'); b.add('emberhold', 'queen', 'd7'); }, {}, { hang });
      const player = createSequencePlayer();
      const p = player.checkmate(rig.ctx, 'e8');
      if (!hang) { await advance(1500); player.skip(); }
      expect((await runUntil(p, 30000)).settled).toBe(true);
      expect(rig.board.removed).toContain(king);
      expect(gsap.globalTimeline.timeScale()).toBe(1);
      await drain(12000);
    }
  });

  it('stalemate: kings face each other, mist rolls in, then they return to rest yaw', async () => {
    let wk!: MockActor; let bk!: MockActor;
    const rig = makeRig(mkMove({ from: 'a1', to: 'a2', side: 'w', role: 'queen', stalemate: true }), (b) => { wk = b.add('emberhold', 'king', 'e1'); bk = b.add('rime', 'king', 'e8'); });
    let faced = false;
    const sample = () => { if (Math.abs(wk.getYaw() - restYaw('w')) > 0.5) faced = true; };
    gsap.ticker.add(sample);
    expect((await runUntil(createSequencePlayer().stalemate(rig.ctx), 20000)).settled).toBe(true);
    gsap.ticker.remove(sample);
    expect(rig.fx.count('mist')).toBe(1);
    expect(faced).toBe(true);
    expect(yawEq(wk.getYaw(), restYaw('w'))).toBe(true);
    expect(yawEq(bk.getYaw(), restYaw('b'))).toBe(true);
    expect(rig.camera.borrows).toBe(0);
    await drain();
  });
});
