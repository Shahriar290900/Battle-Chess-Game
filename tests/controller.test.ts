import { describe, expect, it } from 'vitest';
import { EventBus, type GameEvents } from '../src/contracts';
import { createGameController } from '../src/core/game';
import { createHeadlessPresenter } from '../src/core/headlessPresenter';
import { createSettingsStore } from '../src/core/settings';
import { createNullAi, createScriptedAi } from './helpers';

function setup(ai = createNullAi()) {
  const bus = new EventBus();
  const presenter = createHeadlessPresenter();
  const events: string[] = [];
  const names: Array<keyof GameEvents> = ['game:start', 'turn:start', 'move:resolved', 'castle', 'promotion', 'check', 'game:over', 'ai:thinking'];
  for (const n of names) bus.on(n, () => events.push(n));
  const ctl = createGameController({ presenter, bus, ai, settings: createSettingsStore({ storage: null }), instant: true });
  return { ctl, presenter, events, bus };
}

describe('controller (hot-seat)', () => {
  it('rejects illegal and out-of-turn moves', async () => {
    const { ctl } = setup();
    await ctl.newGame({ kind: 'hotseat', playerSide: 'w', aiLevel: 'easy' });
    expect(ctl.state).toBe('awaitInput');
    expect(await ctl.attemptMove('e2', 'e5')).toBe(false);
    expect(await ctl.attemptMove('e7', 'e5')).toBe(false);
    expect(await ctl.playMove('e2', 'e4')).toBe(true);
    expect(ctl.rules.turn()).toBe('b');
  });

  it('plays move then promote for promotions, and asks the picker when no role is given', async () => {
    const { ctl, presenter } = setup();
    await ctl.newGame({ kind: 'hotseat', playerSide: 'w', aiLevel: 'easy', fen: '7k/P7/8/8/8/8/8/K7 w - - 0 1' });
    presenter.promotionChoice = 'knight';
    expect(await ctl.playMove('a7', 'a8')).toBe(true);
    const calls = presenter.calls.join(',');
    expect(calls).toMatch(/choosePromotion.*move.*promote.*sync/);
    expect(ctl.rules.pieceAt('a8')).toEqual({ side: 'w', role: 'knight' });
    expect(presenter.desyncs).toEqual([]);
  });

  it('dismissing the picker cancels the move', async () => {
    const { ctl, presenter } = setup();
    await ctl.newGame({ kind: 'hotseat', playerSide: 'w', aiLevel: 'easy', fen: '7k/P7/8/8/8/8/8/K7 w - - 0 1' });
    presenter.promotionChoice = null;
    expect(await ctl.attemptMove('a7', 'a8')).toBe(false);
    expect(ctl.state).toBe('awaitInput');
  });

  it('undo takes back one ply; resign ends the game', async () => {
    const { ctl, events } = setup();
    await ctl.newGame({ kind: 'hotseat', playerSide: 'w', aiLevel: 'easy' });
    await ctl.playMove('e2', 'e4');
    expect(await ctl.undo()).toBe(true);
    expect(ctl.rules.fen().startsWith('rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w')).toBe(true);
    expect(ctl.state).toBe('awaitInput');
    await ctl.resign();
    expect(ctl.state).toBe('gameOver');
    expect(ctl.snapshot().result).toEqual({ result: '0-1', reason: 'resign' });
    expect(events.at(-1)).toBe('game:over');
  });
});

describe('controller (vs AI)', () => {
  it('AI replies after the human move and input is blocked meanwhile', async () => {
    const ai = createScriptedAi([{ from: 'e7', to: 'e5' }], { delayMs: 5 });
    const { ctl, events } = setup(ai);
    await ctl.newGame({ kind: 'vs-ai', playerSide: 'w', aiLevel: 'easy' });
    const done = ctl.settled();
    expect(await ctl.attemptMove('e2', 'e4')).toBe(true);
    await new Promise((r) => setTimeout(r, 1));
    expect(ctl.state).toBe('aiThinking');
    expect(await ctl.attemptMove('d2', 'd4')).toBe(false);
    await done;
    expect(ctl.rules.history().map((m) => m.san)).toEqual(['e4', 'e5']);
    expect(events.filter((e) => e === 'ai:thinking').length).toBe(2);
  });

  it('plays first when the human is Black; undo removes a full exchange', async () => {
    const ai = createScriptedAi([{ from: 'e2', to: 'e4' }, { from: 'g1', to: 'f3' }], { delayMs: 1 });
    const { ctl } = setup(ai);
    await ctl.newGame({ kind: 'vs-ai', playerSide: 'b', aiLevel: 'easy' });
    await ctl.settled();
    expect(ctl.rules.history().length).toBe(1);
    expect(ctl.canUndo()).toBe(false);
    await ctl.playMove('e7', 'e5');
    expect(ctl.rules.history().map((m) => m.san)).toEqual(['e4', 'e5', 'Nf3']);
    expect(ctl.canUndo()).toBe(true);
    await ctl.undo();
    expect(ctl.rules.turn()).toBe('b');
    expect(ctl.rules.history().length).toBe(1);
  });

  it('cancels a pending AI search on undo/new game', async () => {
    const ai = createScriptedAi([{ from: 'e7', to: 'e5' }, { from: 'd7', to: 'd5' }], { delayMs: 50 });
    const { ctl } = setup(ai);
    await ctl.newGame({ kind: 'vs-ai', playerSide: 'w', aiLevel: 'easy' });
    void ctl.attemptMove('e2', 'e4');
    await new Promise((r) => setTimeout(r, 5));
    expect(ctl.state).toBe('aiThinking');
    expect(await ctl.undo()).toBe(true);
    expect(ctl.rules.plyCount()).toBe(0);
    expect(ctl.state).toBe('awaitInput');
    await new Promise((r) => setTimeout(r, 80));
    expect(ctl.rules.plyCount()).toBe(0);
  });

  it('falls back to a legal move when the AI returns garbage', async () => {
    const ai = createScriptedAi([{ from: 'a1', to: 'h8' }], { delayMs: 1 });
    const { ctl } = setup(ai);
    await ctl.newGame({ kind: 'vs-ai', playerSide: 'w', aiLevel: 'easy' });
    await ctl.playMove('e2', 'e4');
    expect(ctl.rules.plyCount()).toBe(2);
  });
});
