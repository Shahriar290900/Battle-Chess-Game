// Library mini-duel scenarios: for an attacker (faction + role) and an enemy role, two squares on a private
// position such that the attacker legally captures the enemy with the REAL capture sequence. King as the enemy is
// shown as check + surrender (a king can never be captured). Pure data; tests validate legality with chess.js.
import type { Faction, MoveResult, Role, Side, Square } from '../contracts';
import { FACTION_SIDE, SIDE_FACTION } from '../contracts';

export const DUEL_ENEMIES: readonly Role[] = ['pawn', 'knight', 'bishop', 'rook', 'queen', 'king'];

/** White-side geometry: attacker square -> target square (black attackers mirror the ranks). */
const WHITE_GEOMETRY: Record<Role, [Square, Square]> = {
  pawn: ['d4', 'e5'],
  knight: ['d4', 'f5'],
  bishop: ['c2', 'f5'],
  rook: ['d2', 'd5'],
  queen: ['c3', 'f6'],
  king: ['d4', 'd5'],
};

const mirror = (sq: Square): Square => sq[0] + String(9 - Number(sq[1]));

export interface DuelScenario {
  attackerFaction: Faction;
  attackerRole: Role;
  attackerSide: Side;
  defenderRole: Role;
  attackerSq: Square;
  defenderSq: Square;
  /** 'capture': the attacker takes the defender. 'mate': the attacker checks the king, who surrenders. */
  kind: 'capture' | 'mate';
  /** Placement-only FEN before / after (no kings: the board sync tolerates it). */
  fenBefore: string;
  fenAfter: string;
  move: MoveResult;
}

const SYM: Record<Role, string> = { pawn: 'p', rook: 'r', knight: 'n', bishop: 'b', queen: 'q', king: 'k' };

export function placementFen(pieces: Array<{ sq: Square; side: Side; role: Role }>): string {
  const grid: string[][] = Array.from({ length: 8 }, () => Array<string>(8).fill(''));
  for (const p of pieces) {
    const f = 'abcdefgh'.indexOf(p.sq[0]); const r = 8 - Number(p.sq[1]);
    grid[r][f] = p.side === 'w' ? SYM[p.role].toUpperCase() : SYM[p.role];
  }
  const rows = grid.map((row) => { let s = ''; let n = 0; for (const c of row) { if (c) { if (n) s += n; n = 0; s += c; } else n++; } return n ? s + n : s; });
  return `${rows.join('/')} w - - 0 1`;
}

export function duelScenario(attackerFaction: Faction, attackerRole: Role, defenderRole: Role): DuelScenario {
  const side = FACTION_SIDE[attackerFaction];
  const [a0, d0] = WHITE_GEOMETRY[attackerRole];
  const attackerSq = side === 'w' ? a0 : mirror(a0);
  const defenderSq = side === 'w' ? d0 : mirror(d0);
  const defSide: Side = side === 'w' ? 'b' : 'w';
  const kind = defenderRole === 'king' ? 'mate' : 'capture';
  const fenBefore = placementFen([{ sq: attackerSq, side, role: attackerRole }, { sq: defenderSq, side: defSide, role: defenderRole }]);
  const fenAfter = kind === 'capture'
    ? placementFen([{ sq: defenderSq, side, role: attackerRole }])
    : fenBefore; // the attacker stays where it is; the king kneels in place
  const move: MoveResult = kind === 'capture'
    ? {
      from: attackerSq, to: defenderSq, san: 'x', side, role: attackerRole, captured: defenderRole, capturedSquare: defenderSq, flags: 'c',
      isCastle: false, isEnPassant: false, check: false, mate: false, stalemate: false, draw: false, fenAfter,
    }
    : {
      from: attackerSq, to: attackerSq, san: '#', side, role: attackerRole, flags: 'n',
      isCastle: false, isEnPassant: false, check: true, mate: true, stalemate: false, draw: false, fenAfter,
    };
  return { attackerFaction, attackerRole, attackerSide: side, defenderRole, attackerSq, defenderSq, kind, fenBefore, fenAfter, move };
}

export const enemyFaction = (f: Faction): Faction => SIDE_FACTION[FACTION_SIDE[f] === 'w' ? 'b' : 'w'];
