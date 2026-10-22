import { Vector3 } from 'three';
import { expect } from 'vitest';
import type { Faction, Role, Side, Square } from '../../src/contracts';
import { restYaw, squareToWorld, SIDE_FACTION } from '../../src/contracts';
import { gsap } from './harness';
import { makeRig, mkMove, type MockActor, type MockBoard, type Rig } from './mocks';
import type { Settings } from '../../src/contracts';

export const ROLES: Role[] = ['pawn', 'rook', 'knight', 'bishop', 'queen', 'king'];
export const FACTIONS: Faction[] = ['emberhold', 'rime'];

/** Capture geometry per role and side (from -> to). */
export const CAPTURE_SQUARES: Record<Role, Record<Side, [Square, Square]>> = {
  pawn: { w: ['e4', 'd5'], b: ['d5', 'e4'] },
  rook: { w: ['a1', 'a5'], b: ['h8', 'h4'] },
  knight: { w: ['e4', 'f6'], b: ['e5', 'd3'] },
  bishop: { w: ['c1', 'g5'], b: ['f8', 'b4'] },
  queen: { w: ['d1', 'h5'], b: ['d8', 'h4'] },
  king: { w: ['e1', 'e2'], b: ['e8', 'e7'] },
};

const sideOf = (f: Faction): Side => (f === 'emberhold' ? 'w' : 'b');

/** Add a few bystander pieces (pawn rows) that are not on the given squares. */
export function addBystanders(board: MockBoard, used: Square[]) {
  for (const f of 'abcdefgh') {
    for (const [rank, fac] of [['2', 'emberhold'], ['7', 'rime']] as const) {
      const sq = f + rank;
      if (!used.includes(sq) && !board.actorAt(sq)) board.add(fac, 'pawn', sq);
    }
  }
}

export interface CaptureCase {
  rig: Rig; attacker: MockActor; defender: MockActor; from: Square; to: Square; capturedSquare: Square;
  bystanders: MockActor[]; startYaws: Map<MockActor, number>;
}

export function captureCase(role: Role, faction: Faction, over: Partial<Settings> = {}, extra: Parameters<typeof makeRig>[3] = {}, defenderRole: Role = 'knight'): CaptureCase {
  const side = sideOf(faction);
  const [from, to] = CAPTURE_SQUARES[role][side];
  const defFaction: Faction = SIDE_FACTION[side === 'w' ? 'b' : 'w'];
  let attacker!: MockActor; let defender!: MockActor;
  const rig = makeRig(
    mkMove({ from, to, side, role, captured: defenderRole, capturedSquare: to }),
    (board) => {
      attacker = board.add(faction, role, from);
      defender = board.add(defFaction, defenderRole, to);
      addBystanders(board, [from, to]);
    }, over, { seatZ: side === 'w' ? 1 : -1, ...extra },
  );
  const bystanders = rig.board.allActors().filter((a) => a !== attacker && a !== defender);
  return { rig, attacker, defender, from, to, capturedSquare: to, bystanders, startYaws: new Map(bystanders.map((a) => [a, a.getYaw()])) };
}

export function enPassantCase(faction: Faction, over: Partial<Settings> = {}): CaptureCase {
  // white e5 x d5 e.p. -> d6 ; black d4 x e4 e.p. -> e3
  const white = faction === 'emberhold';
  const from = white ? 'e5' : 'd4';
  const to = white ? 'd6' : 'e3';
  const capturedSquare = white ? 'd5' : 'e4';
  let attacker!: MockActor; let defender!: MockActor;
  const rig = makeRig(
    mkMove({ from, to, side: sideOf(faction), role: 'pawn', captured: 'pawn', capturedSquare, isEnPassant: true }),
    (board) => {
      attacker = board.add(faction, 'pawn', from);
      defender = board.add(white ? 'rime' : 'emberhold', 'pawn', capturedSquare);
      addBystanders(board, [from, to, capturedSquare]);
    }, over, { seatZ: white ? 1 : -1 },
  );
  const bystanders = rig.board.allActors().filter((a) => a !== attacker && a !== defender);
  return { rig, attacker, defender, from, to, capturedSquare, bystanders, startYaws: new Map(bystanders.map((a) => [a, a.getYaw()])) };
}

export const yawEq = (a: number, b: number, eps = 1e-3) => {
  const d = Math.atan2(Math.sin(a - b), Math.cos(a - b));
  return Math.abs(d) < eps;
};

/** The resolve guarantees from the choreography spec. */
export function expectCaptureFinal(c: CaptureCase, opts: { cameraBorrowed: boolean }) {
  const { rig, attacker, defender } = c;
  const target = squareToWorld(c.to, new Vector3());
  expect(attacker.root.position.x).toBeCloseTo(target.x, 5);
  expect(attacker.root.position.z).toBeCloseTo(target.z, 5);
  expect(attacker.root.position.y).toBeCloseTo(0, 5);
  expect(yawEq(attacker.getYaw(), restYaw(attacker.side))).toBe(true);
  expect(attacker.model.rotation.x).toBeCloseTo(0, 5);
  expect(rig.board.actorAt(c.to)).toBe(attacker);
  expect(attacker.square).toBe(c.to);
  expect(rig.board.removed).toContain(defender);
  expect(rig.board.actorAt(c.capturedSquare) === defender).toBe(false);
  expect(attacker.summon).toBe(0);
  expect(gsap.globalTimeline.timeScale()).toBe(1);
  // camera is back at the seat
  if (opts.cameraBorrowed) {
    expect(rig.camera.borrows).toBe(1);
    expect(rig.camera.state).toBe('seat');
  } else {
    expect(rig.camera.borrows).toBe(0);
  }
  // no tweens remain on actors
  for (const a of [attacker, defender, ...c.bystanders]) {
    expect(gsap.getTweensOf([a.root.position, a.root.rotation, a.model.rotation]).length).toBe(0);
  }
  // bystanders un-dimmed and facing as before
  for (const b of c.bystanders) {
    expect(b.dim).toBe(0);
    expect(b.fade).toBe(1);
    expect(yawEq(b.getYaw(), c.startYaws.get(b)!)).toBe(true);
  }
  // events: exactly one begin/end
  const names = rig.events.map((e) => e.name);
  expect(names.filter((n) => n === 'capture:begin').length).toBe(1);
  expect(names.filter((n) => n === 'capture:end').length).toBe(1);
  expect(names.filter((n) => n === 'capture:shatter').length).toBeLessThanOrEqual(1);
  expect(names[0]).toBe('capture:begin');
  expect(names[names.length - 1] === 'capture:end' || names.slice(names.indexOf('capture:end')).every((n) => n === 'capture:end')).toBe(true);
  expect(rig.fx.trailsOpen).toBe(0);
  expect(rig.board.scene.children.some((o) => o.name === 'cinematic_light_rig')).toBe(false);
  // camera poses sane
  for (const p of rig.camera.poses) {
    expect(Number.isFinite(p.position.x + p.position.y + p.position.z)).toBe(true);
    expect(p.position.y).toBeGreaterThanOrEqual(0.6 - 1e-6);
  }
}

const BACK: Role[] = ['rook', 'knight', 'bishop', 'queen', 'king', 'bishop', 'knight', 'rook'];

/** Full 32-piece board with a capture in the middle of the crowd or on the back rank. */
export function crowdedCase(name: 'opening-w' | 'opening-b' | 'backrank-w' | 'backrank-b', over: Partial<Settings> = {}): CaptureCase {
  const rm = new Set<string>(); const extra: Array<[Faction, Role, Square]> = [];
  let from = ''; let to = ''; let side: Side = 'w';
  if (name === 'opening-w') { rm.add('e2'); rm.add('d7'); extra.push(['emberhold', 'pawn', 'e4'], ['rime', 'pawn', 'd5']); from = 'e4'; to = 'd5'; }
  if (name === 'opening-b') { rm.add('e2'); rm.add('d7'); rm.add('g1'); extra.push(['emberhold', 'pawn', 'e4'], ['emberhold', 'knight', 'f3'], ['rime', 'pawn', 'd5']); from = 'd5'; to = 'e4'; side = 'b'; }
  if (name === 'backrank-w') { rm.add('d2'); rm.add('d7'); from = 'd1'; to = 'd8'; }
  if (name === 'backrank-b') { rm.add('d2'); rm.add('d7'); from = 'd8'; to = 'd1'; side = 'b'; }
  let attacker!: MockActor; let defender!: MockActor;
  const rig = makeRig(mkMove({ from, to, side, role: 'pawn', captured: 'pawn', capturedSquare: to }), (b) => {
    for (let f = 0; f < 8; f++) {
      for (const [rank, fac, r] of [['1', 'emberhold', BACK[f]], ['2', 'emberhold', 'pawn'], ['7', 'rime', 'pawn'], ['8', 'rime', BACK[f]]] as Array<[string, Faction, Role]>) {
        const sq = 'abcdefgh'[f] + rank;
        if (!rm.has(sq)) b.add(fac, r, sq);
      }
    }
    for (const [fac, r, sq] of extra) b.add(fac, r, sq);
    attacker = b.actorAt(from)!; defender = b.actorAt(to)!;
  }, over, { seatZ: side === 'w' ? 1 : -1 });
  rig.ctx.move.role = attacker.role;
  rig.ctx.move.captured = defender.role;
  const bystanders = rig.board.allActors().filter((a) => a !== attacker && a !== defender);
  return { rig, attacker, defender, from, to, capturedSquare: to, bystanders, startYaws: new Map(bystanders.map((a) => [a, a.getYaw()])) };
}
