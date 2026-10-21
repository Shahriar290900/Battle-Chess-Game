// Shared primitive types and board-space helpers. Lead-owned (contract v1).
import { Vector3 } from 'three';

export type Side = 'w' | 'b';
export type Faction = 'emberhold' | 'rime';
export type Role = 'pawn' | 'rook' | 'knight' | 'bishop' | 'queen' | 'king';
export type PieceSymbol = 'p' | 'r' | 'n' | 'b' | 'q' | 'k';
export type PromotionRole = 'queen' | 'rook' | 'bishop' | 'knight';
/** Algebraic square, e.g. "e4". */
export type Square = string;

export const FILES = 'abcdefgh';
export const SIDE_FACTION: Record<Side, Faction> = { w: 'emberhold', b: 'rime' };
export const FACTION_SIDE: Record<Faction, Side> = { emberhold: 'w', rime: 'b' };
export const SYMBOL_ROLE: Record<PieceSymbol, Role> = {
  p: 'pawn', r: 'rook', n: 'knight', b: 'bishop', q: 'queen', k: 'king',
};
export const ROLE_SYMBOL: Record<Role, PieceSymbol> = {
  pawn: 'p', rook: 'r', knight: 'n', bishop: 'b', queen: 'q', king: 'k',
};

/** Result of an accepted move, produced by the rules wrapper before any animation runs. */
export interface MoveResult {
  from: Square;
  to: Square;
  san: string;
  side: Side;
  role: Role;
  /** Role of the captured piece, if any. */
  captured?: Role;
  /** Square the captured piece stood on (differs from `to` for en passant). */
  capturedSquare?: Square;
  flags: string;
  isCastle: boolean;
  /** For castling: the rook's from/to squares. */
  rookFrom?: Square;
  rookTo?: Square;
  isEnPassant: boolean;
  promotion?: PromotionRole;
  check: boolean;
  mate: boolean;
  stalemate: boolean;
  draw: boolean;
  fenAfter: string;
}

// Coordinates (architecture §3): 1 unit = 1 square, board centred at origin, top at y = 0.
// x = fileIndex − 3.5, z = 3.5 − rankIndex. White (Emberhold) sits on +z looking toward −z.

export function squareToWorld(sq: Square, target = new Vector3()): Vector3 {
  const f = FILES.indexOf(sq[0]);
  const r = Number(sq[1]) - 1;
  return target.set(f - 3.5, 0, 3.5 - r);
}

export function worldToSquare(v: { x: number; z: number }): Square | null {
  const f = Math.round(v.x + 3.5);
  const r = Math.round(3.5 - v.z);
  if (f < 0 || f > 7 || r < 0 || r > 7) return null;
  return FILES[f] + String(r + 1);
}

export function squareIndices(sq: Square): { file: number; rank: number } {
  return { file: FILES.indexOf(sq[0]), rank: Number(sq[1]) - 1 };
}

export function isLightSquare(sq: Square): boolean {
  const { file, rank } = squareIndices(sq);
  return (file + rank) % 2 === 1;
}

/** Yaw (radians about +Y) that makes a piece whose front is +Z face from `from` toward `to`. */
export function yawToward(from: { x: number; z: number }, to: { x: number; z: number }): number {
  return Math.atan2(to.x - from.x, to.z - from.z);
}

/** Resting yaw for a side: Emberhold faces −z (toward Black) → π; Rime faces +z → 0. */
export function restYaw(side: Side): number {
  return side === 'w' ? Math.PI : 0;
}
