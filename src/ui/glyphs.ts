// Display strings and small helpers shared by UI modules.
import type { AiLevel, Role, Side } from '../contracts';
import { FACTION_NAME, SIDE_FACTION } from '../contracts';
import type { GameOverReason, GameResult } from '../core/rules';

export const ROLE_VALUE: Record<Role, number> = { pawn: 1, knight: 3, bishop: 3, rook: 5, queen: 9, king: 0 };
export const ROLE_LABEL: Record<Role, string> = { pawn: 'Pawn', knight: 'Knight', bishop: 'Bishop', rook: 'Rook', queen: 'Queen', king: 'King' };
export const LEVEL_LABEL: Record<AiLevel, string> = { easy: 'Easy', medium: 'Medium', hard: 'Hard', master: 'Master' };
export const sideName = (s: Side) => FACTION_NAME[SIDE_FACTION[s]];

export const REASON_LABEL: Record<GameOverReason, string> = {
  checkmate: 'Checkmate', stalemate: 'Stalemate: no legal moves', draw: 'Drawn game', resign: 'Resignation',
  threefold: 'Threefold repetition', insufficient: 'Insufficient material', 'fifty-move': 'Fifty-move rule',
};

export function resultHeadline(result: GameResult, mode: { kind: string; playerSide: Side } | null): { title: string; sub: string } {
  if (result === '1/2-1/2') return { title: 'A Drawn Field', sub: 'Neither host yields.' };
  const winner: Side = result === '1-0' ? 'w' : 'b';
  if (mode?.kind === 'vs-ai') {
    return winner === mode.playerSide
      ? { title: 'Victory', sub: `${sideName(winner)} holds the field.` }
      : { title: 'Defeat', sub: `${sideName(winner)} prevails.` };
  }
  return { title: `${sideName(winner)} Triumphs`, sub: winner === 'w' ? 'The forges burn bright.' : 'The frost claims the field.' };
}
