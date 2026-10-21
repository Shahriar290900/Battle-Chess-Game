// Replays every PGN in tests/games/ through the game controller headless (instant mode, no rendering)
// and asserts the final FEN equals chess.js's, that the presenter never desynced from the FEN, and
// that the whole set covers the required rules features.
import { Chess } from 'chess.js';
import { describe, expect, it } from 'vitest';
import { EventBus, ROLES, SYMBOL_ROLE, type MoveResult, type PromotionRole } from '../src/contracts';
import { createGameController } from '../src/core/game';
import { createHeadlessPresenter } from '../src/core/headlessPresenter';
import { createSettingsStore } from '../src/core/settings';
import { START_FEN } from '../src/core/rules';
import { createNullAi } from './helpers';

const corpus = import.meta.glob('./games/*.pgn', { query: '?raw', import: 'default', eager: true }) as Record<string, string>;
const files = Object.keys(corpus).sort();
const covered = new Set<string>();

describe('PGN corpus', () => {
  it('has games', () => { expect(files.length).toBeGreaterThan(0); });

  for (const file of files) {
    it(`replays ${file}`, async () => {
      const pgn = corpus[file];
      const ref = new Chess();
      ref.loadPgn(pgn);
      const moves = ref.history({ verbose: true });
      const startFen = moves.length ? moves[0].before : ref.fen();

      const bus = new EventBus();
      const presenter = createHeadlessPresenter(startFen);
      const ctl = createGameController({
        presenter, bus, settings: createSettingsStore({ storage: null }), ai: createNullAi(), instant: true,
      });
      const resolved: MoveResult[] = [];
      let over: unknown = null;
      bus.on('move:resolved', (m) => resolved.push(m));
      bus.on('game:over', (e) => { over = e; });

      await ctl.newGame({ kind: 'hotseat', playerSide: 'w', aiLevel: 'medium', fen: startFen === START_FEN ? undefined : startFen });
      for (const m of moves) {
        const promo = m.promotion ? (SYMBOL_ROLE[m.promotion] as PromotionRole) : undefined;
        expect(await ctl.playMove(m.from, m.to, promo), `${file}: ${m.san}`).toBe(true);
      }

      expect(ctl.rules.fen()).toBe(ref.fen());
      expect(presenter.desyncs).toEqual([]);
      expect(resolved.map((r) => r.san)).toEqual(moves.map((m) => m.san));
      expect(ctl.state).toBe(ref.isGameOver() ? 'gameOver' : 'awaitInput');
      if (ref.isCheckmate()) expect((over as { reason: string }).reason).toBe('checkmate');
      if (ref.isStalemate()) expect((over as { reason: string }).reason).toBe('stalemate');

      // Cross-check every MoveResult against chess.js and gather coverage.
      resolved.forEach((r, i) => {
        const m = moves[i];
        expect(r.from).toBe(m.from);
        expect(r.to).toBe(m.to);
        expect(r.fenAfter).toBe(m.after);
        expect(r.isEnPassant).toBe(m.isEnPassant());
        if (m.isEnPassant()) expect(r.capturedSquare).toBe(m.to[0] + m.from[1]);
        else if (m.captured) expect(r.capturedSquare).toBe(m.to);
        if (r.isCastle) { expect(r.rookFrom).toBeTruthy(); expect(r.rookTo).toBeTruthy(); }
        if (r.isCastle) covered.add(`castle:${r.side}:${m.isKingsideCastle() ? 'k' : 'q'}`);
        if (r.isEnPassant) covered.add('en-passant');
        if (r.promotion) covered.add(`promo:${r.promotion}`);
        if (r.captured) covered.add(`capture:${r.role}>${r.captured}`);
        if (r.mate) covered.add('mate');
        if (r.stalemate) covered.add('stalemate');
      });
    });
  }

  it('covers every required rules feature across the set', () => {
    const required = [
      'castle:w:k', 'castle:w:q', 'castle:b:k', 'castle:b:q', 'en-passant',
      'promo:rook', 'promo:bishop', 'promo:knight', 'promo:queen', 'mate', 'stalemate',
      // Every attacker x defender pair; a king can never be captured in legal chess.
      ...ROLES.flatMap((a) => ROLES.filter((d) => d !== 'king').map((d) => `capture:${a}>${d}`)),
    ];
    expect(required.filter((f) => !covered.has(f))).toEqual([]);
    expect(required.filter((f) => f.startsWith('capture:')).length).toBe(30);
  });
});
