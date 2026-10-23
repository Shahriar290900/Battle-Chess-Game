import { describe, expect, it } from 'vitest';
import { Chess } from 'chess.js';
import { FACTIONS, ROLES, DISPLAY_NAME, assetId } from '../../src/contracts';
import { parsePlacement } from '../../src/core/rules';
import { DUEL_ENEMIES, duelScenario } from '../../src/learn/duel';
import { ROLE_INFO, ROLE_ORDER, LORE, displayName, moveDiagram } from '../../src/learn/pieces';
import { TUTORIAL_POSITIONS, scriptMove } from '../../src/learn/script';

describe('duel scenarios', () => {
  for (const faction of FACTIONS) for (const role of ROLES) for (const enemy of DUEL_ENEMIES) {
    it(`${faction} ${role} vs ${enemy}`, () => {
      const sc = duelScenario(faction, role, enemy);
      // add both kings far from the action to validate with chess.js
      const placement = parsePlacement(sc.fenBefore);
      const kingSquares: Record<'w' | 'b', string> = sc.attackerSide === 'w' ? { w: 'h1', b: 'a8' } : { w: 'h1', b: 'a8' };
      const c = new Chess(undefined, { skipValidation: true } as never);
      c.clear();
      for (const [sq, p] of placement) c.put({ type: ({ pawn: 'p', rook: 'r', knight: 'n', bishop: 'b', queen: 'q', king: 'k' } as const)[p.role], color: p.side }, sq as never);
      if (enemy !== 'king' && role !== 'king') { c.put({ type: 'k', color: 'w' }, kingSquares.w as never); c.put({ type: 'k', color: 'b' }, kingSquares.b as never); }
      else {
        // king duels: place the missing king(s) far away
        const has = (col: 'w' | 'b') => placement.size && [...placement.values()].some((p) => p.role === 'king' && p.side === col);
        if (!has('w')) c.put({ type: 'k', color: 'w' }, 'h1' as never);
        if (!has('b')) c.put({ type: 'k', color: 'b' }, 'a8' as never);
      }
      if (sc.kind === 'capture') {
        const fen = c.fen().split(' '); fen[1] = sc.attackerSide; const test = new Chess(fen.join(' '));
        const m = test.moves({ verbose: true }).find((x) => x.from === sc.attackerSq && x.to === sc.defenderSq && x.isCapture());
        expect(m, 'attacker can capture').toBeTruthy();
        expect(sc.move.captured).toBe(enemy);
      } else {
        expect(c.attackers(sc.defenderSq as never, sc.attackerSide)).toContain(sc.attackerSq);
      }
      expect(parsePlacement(sc.fenAfter).size).toBe(sc.kind === 'capture' ? 1 : 2);
    });
  }
});

describe('piece library data', () => {
  it('names every piece and has lore + movement text', () => {
    for (const f of FACTIONS) for (const r of ROLES) {
      expect(displayName(f, r)).toBe(DISPLAY_NAME[assetId(f, r)]);
      expect(LORE[f][r].length).toBeGreaterThan(20);
    }
    for (const r of ROLE_ORDER) { expect(ROLE_INFO[r].moves.length).toBeGreaterThan(0); expect(ROLE_INFO[r].function.length).toBeGreaterThan(10); }
    expect(ROLE_ORDER.length).toBe(6);
  });
  it('mini diagrams have the right shapes', () => {
    expect(moveDiagram('knight').cells.length).toBe(8);
    expect(moveDiagram('king').cells.length).toBe(8);
    expect(moveDiagram('pawn').cells.map((c) => c.kind).sort()).toEqual(['capture', 'capture', 'first', 'move']);
    expect(moveDiagram('rook').cells.length).toBe(12);
    expect(moveDiagram('bishop').cells.length).toBe(12);
    expect(moveDiagram('queen').cells.length).toBe(24);
  });
});

describe('tutorial positions', () => {
  it('capture / check / mate scripts are legal and have the claimed flags', () => {
    const cap = scriptMove(TUTORIAL_POSITIONS.capture);
    const chk = scriptMove(TUTORIAL_POSITIONS.check);
    const mate = scriptMove(TUTORIAL_POSITIONS.mate);
    const run = (p: ReturnType<typeof scriptMove>) => { const c = new Chess(p.fen); return c.move({ from: p.from, to: p.to }); };
    expect(run(cap).isCapture()).toBe(true);
    expect(run(chk).san.endsWith('+')).toBe(true);
    expect(run(mate).san.endsWith('#')).toBe(true);
  });
});
