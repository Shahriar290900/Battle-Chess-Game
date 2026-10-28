// Game controller / state machine (architecture §4).
//
//   Boot → Loading → Menu → TurnStart → AwaitInput | AiThinking → (Promotion) → Resolving
//        → Sequence (move | capture | castle | promotion) → PostMove (check | mate | draw)
//        → TurnEnd → TurnStart …                                        GameOver on mate/draw/resign
//
// The rules engine accepts a move before any animation starts, so visuals can never desync from the
// position. The controller is decoupled from three.js: all visuals go through a GamePresenter.
import type { AiMove, AiPlayer, EventBus, GameModeConfig, MoveResult, PromotionRole, Role, SettingsStore, Side, Square } from '../contracts';
import { toElo } from './ai/strength';
import type { GamePresenter } from './presenter';
import { Rules, START_FEN, type GameEnd } from './rules';

export type GameState =
  | 'boot' | 'loading' | 'menu' | 'turnStart' | 'awaitInput' | 'aiThinking' | 'promotion'
  | 'resolving' | 'sequence' | 'postMove' | 'turnEnd' | 'gameOver';

export interface NewGameConfig extends GameModeConfig {
  /** Optional custom start position (tests, puzzles). */
  fen?: string;
  /** Computer strength in Elo for vs-ai. Supplying it makes the game a rated game; without it the legacy `aiLevel` sets the strength and the game is unrated (tutorial duels, tests). */
  aiElo?: number;
}

export interface GameSnapshot {
  state: GameState;
  mode: GameModeConfig | null;
  turn: Side;
  fen: string;
  /** Moves played so far, oldest first. */
  moves: MoveResult[];
  /** Roles captured BY each side. */
  captured: Record<Side, Role[]>;
  /** King square when the side to move is in check. */
  check: Square | null;
  thinking: boolean;
  /** True while a move is being animated. */
  busy: boolean;
  humanTurn: boolean;
  canUndo: boolean;
  result: GameEnd | null;
}

export interface ControllerDeps {
  presenter: GamePresenter;
  ai: AiPlayer;
  bus: EventBus;
  settings: SettingsStore;
  rules?: Rules;
  /** Instant mode: no artificial delays (tests, headless replay). */
  instant?: boolean;
  /** Minimum "thinking" time so AI replies do not flash by. */
  aiMinDelayMs?: number;
}

interface Intent { from: Square; to: Square; promotion?: PromotionRole }

const sleep = (ms: number) => new Promise<void>((r) => setTimeout(r, ms));

export class GameController {
  readonly rules: Rules;
  readonly bus: EventBus;
  private presenter: GamePresenter;
  private ai: AiPlayer;
  private settings: SettingsStore;
  private instant: boolean;
  private aiMinDelay: number;

  private _state: GameState = 'boot';
  private mode: GameModeConfig | null = null;
  private result: GameEnd | null = null;
  private _aiElo: number | null = null;
  private _rated = false;
  private _tookBack = false;
  private epoch = 0;
  private loopDone: Promise<void> = Promise.resolve();
  private pending: ((i: Intent | null) => void) | null = null;
  private skipRequested = false;
  private firstTurn = true;
  private aiReady: Promise<void> = Promise.resolve();
  private listeners = new Set<(s: GameSnapshot) => void>();
  private settleWaiters: Array<() => void> = [];
  private cache: { fen: string; ply: number; moves: MoveResult[]; captured: Record<Side, Role[]> } | null = null;

  constructor(deps: ControllerDeps) {
    this.rules = deps.rules ?? new Rules();
    this.bus = deps.bus;
    this.presenter = deps.presenter;
    this.ai = deps.ai;
    this.settings = deps.settings;
    this.instant = !!deps.instant;
    this.aiMinDelay = deps.aiMinDelayMs ?? 550;
  }

  get state(): GameState { return this._state; }
  get gameMode(): GameModeConfig | null { return this.mode; }
  /** Computer strength of the current vs-ai game in Elo (null in hot-seat). */
  get opponentElo(): number | null { return this._aiElo; }
  /** Elo of a rated vs-ai game (started with an explicit `aiElo`); null otherwise. */
  get ratedElo(): number | null { return this._rated ? this._aiElo : null; }
  /** True once Undo was used in the current game. */
  get tookBack(): boolean { return this._tookBack; }

  // ------------------------------------------------------------------ observation

  subscribe(fn: (s: GameSnapshot) => void): () => void {
    this.listeners.add(fn);
    return () => { this.listeners.delete(fn); };
  }

  snapshot(): GameSnapshot {
    const fen = this.rules.fen();
    const ply = this.rules.plyCount();
    if (!this.cache || this.cache.fen !== fen || this.cache.ply !== ply) {
      this.cache = { fen, ply, moves: this.rules.history(), captured: this.rules.captured() };
    }
    const turn = this.rules.turn();
    return {
      state: this._state, mode: this.mode, turn, fen,
      moves: this.cache.moves, captured: this.cache.captured,
      check: this.rules.inCheck() ? this.rules.kingSquare(turn) : null,
      thinking: this._state === 'aiThinking',
      busy: this._state === 'resolving' || this._state === 'sequence' || this._state === 'postMove',
      humanTurn: !this.isAiTurn(),
      canUndo: this.canUndo(),
      result: this.result,
    };
  }

  private notify(): void {
    if (this.listeners.size === 0) return;
    const s = this.snapshot();
    this.listeners.forEach((fn) => { try { fn(s); } catch (e) { console.error('[game] subscriber failed', e); } });
  }

  private setState(s: GameState): void {
    this._state = s;
    this.notify();
    if (s === 'awaitInput' || s === 'gameOver' || s === 'menu') {
      const w = this.settleWaiters;
      this.settleWaiters = [];
      w.forEach((fn) => fn());
    }
  }

  /** Lifecycle hooks used by main (boot/loading screens). */
  setPhase(phase: 'boot' | 'loading' | 'menu'): void { this.setState(phase); }

  isAiTurn(): boolean {
    return !!this.mode && this.mode.kind === 'vs-ai' && this.rules.turn() !== this.mode.playerSide && !this.result;
  }

  /** True when a human may select and move this piece right now. */
  canSelect(sq: Square): boolean {
    if (this._state !== 'awaitInput' || !this.pending) return false;
    const p = this.rules.pieceAt(sq);
    return !!p && p.side === this.rules.turn();
  }

  legalMovesFrom(sq: Square) { return this.canSelect(sq) ? this.rules.legalMovesFrom(sq) : []; }

  /** Resolves the next time the machine parks (awaiting input, game over or menu). */
  settled(): Promise<void> {
    return new Promise<void>((r) => this.settleWaiters.push(r));
  }

  // ------------------------------------------------------------------ commands

  async newGame(config: NewGameConfig): Promise<void> {
    await this.interrupt();
    const fen = config.fen ?? START_FEN;
    this.rules.reset(config.fen);
    this.cache = null;
    this.result = null;
    this.mode = { kind: config.kind, playerSide: config.playerSide, aiLevel: config.aiLevel };
    this._aiElo = config.kind === 'vs-ai' ? toElo(config.aiElo ?? config.aiLevel) : null;
    this._rated = config.kind === 'vs-ai' && typeof config.aiElo === 'number';
    this._tookBack = false;
    this.firstTurn = true;
    this.presenter.reset(fen);
    if (config.kind === 'vs-ai') {
      this.ai.newGame();
      this.aiReady = this.ai.init().catch((e) => { console.warn('[game] AI init failed, falling back to random moves', e); });
    }
    this.bus.emit('game:start', { mode: config.kind, fen });
    this.startLoop();
  }

  /** Try to play a move for the human. Resolves true if it was accepted. */
  async attemptMove(from: Square, to: Square, promotion?: PromotionRole): Promise<boolean> {
    if (this._state !== 'awaitInput' || !this.pending) return false;
    const lm = this.rules.legalMovesFrom(from).find((m) => m.to === to);
    if (!lm) return false;
    let promo = promotion;
    if (lm.isPromotion) {
      if (!promo) {
        const epoch = this.epoch;
        this.setState('promotion');
        const picked = await this.presenter.choosePromotion(this.rules.turn());
        if (this.epoch !== epoch) return false;
        if (!picked) { this.setState('awaitInput'); return false; }
        promo = picked;
      }
      if (!lm.promotions!.includes(promo)) { this.setState('awaitInput'); return false; }
    }
    const p = this.pending;
    this.pending = null;
    p?.({ from, to, promotion: promo });
    return true;
  }

  /** attemptMove + wait until the whole turn (animation, AI reply) has played out. Used by tests. */
  async playMove(from: Square, to: Square, promotion?: PromotionRole): Promise<boolean> {
    const done = this.settled();
    const ok = await this.attemptMove(from, to, promotion);
    if (ok) await done;
    return ok;
  }

  /** Tap during a sequence: finish it now. */
  skip(): void {
    if (this._state === 'resolving' || this._state === 'sequence' || this._state === 'postMove') {
      this.skipRequested = true;
      this.presenter.skip();
    }
  }

  canUndo(): boolean {
    if (!this.mode) return false;
    if (!(this._state === 'awaitInput' || this._state === 'aiThinking' || this._state === 'gameOver' || this._state === 'promotion')) return false;
    const ply = this.rules.plyCount();
    if (this.mode.kind === 'hotseat') return ply > 0;
    // vs-AI: undo only makes sense once the human has moved at least once.
    return ply > (this.mode.playerSide === 'w' ? 0 : 1);
  }

  /** Take back the last move (hot-seat) or the last full exchange (vs-AI: 2 plies). */
  async undo(): Promise<boolean> {
    if (!this.canUndo() || !this.mode) return false;
    const mode = this.mode;
    this._tookBack = true;
    await this.interrupt();
    this.rules.undo();
    if (mode.kind === 'vs-ai') {
      while (this.rules.turn() !== mode.playerSide && this.rules.plyCount() > 0) this.rules.undo();
    }
    this.cache = null;
    this.result = null;
    this.presenter.syncToFen(this.rules.fen());
    const ksq = this.rules.inCheck() ? this.rules.kingSquare(this.rules.turn()) : null;
    this.presenter.markCheck(ksq);
    this.startLoop();
    return true;
  }

  async resign(): Promise<void> {
    if (!this.mode || this._state === 'gameOver' || this._state === 'menu') return;
    const loser: Side = this.mode.kind === 'vs-ai' ? this.mode.playerSide : this.rules.turn();
    await this.interrupt();
    this.finish({ result: loser === 'w' ? '0-1' : '1-0', reason: 'resign' });
  }

  dispose(): void {
    this.epoch++;
    this.ai.cancel();
    this.cancelPending();
    this.listeners.clear();
  }

  // ------------------------------------------------------------------ internals

  /** Stop the running loop (human wait, AI search, sequence) and wait until it has exited. */
  private async interrupt(): Promise<void> {
    this.epoch++;
    this.ai.cancel();
    this.cancelPending();
    this.presenter.cancelPromotion?.();
    if (this._state === 'sequence' || this._state === 'resolving' || this._state === 'postMove' || this.presenter.running) this.presenter.skip();
    await this.loopDone;
  }

  private cancelPending(): void {
    const p = this.pending;
    this.pending = null;
    p?.(null);
  }

  private startLoop(): void {
    const epoch = this.epoch;
    this.loopDone = this.loop(epoch).catch((e) => { console.error('[game] loop failed', e); });
  }

  private seatFor(turn: Side): Side | null {
    const mode = this.mode;
    if (!mode) return null;
    const cam = this.settings.get().cameraMode;
    if (cam === 'free') return this.firstTurn ? (mode.kind === 'vs-ai' ? mode.playerSide : 'w') : null;
    if (mode.kind === 'vs-ai') return mode.playerSide;
    return cam === 'fixed' ? 'w' : turn;
  }

  private async loop(epoch: number): Promise<void> {
    const alive = () => this.epoch === epoch;
    while (alive()) {
      const end = this.rules.gameOver();
      if (end) { this.finish(end); return; }
      this.setState('turnStart');
      const side = this.rules.turn();
      const seat = this.seatFor(side);
      if (seat) void this.presenter.seatCamera(seat, this.firstTurn || this.instant);
      this.firstTurn = false;
      this.bus.emit('turn:start', { side, fen: this.rules.fen(), moveNumber: Math.floor(this.rules.plyCount() / 2) + 1 });
      const intent = this.isAiTurn() ? await this.aiIntent(epoch) : await this.humanIntent();
      if (!alive()) return;
      if (!intent) continue;
      await this.resolve(intent, epoch);
    }
  }

  private humanIntent(): Promise<Intent | null> {
    this.setState('awaitInput');
    return new Promise<Intent | null>((resolve) => { this.pending = resolve; });
  }

  private async aiIntent(epoch: number): Promise<Intent | null> {
    const side = this.rules.turn();
    const level = this._aiElo ?? this.mode?.aiLevel ?? 'medium';
    this.setState('aiThinking');
    this.bus.emit('ai:thinking', { side, thinking: true });
    const t0 = Date.now();
    try {
      await this.aiReady;
      let mv: AiMove | null = null;
      try {
        mv = await this.ai.getMove(this.rules.fen(), level);
      } catch (e) {
        if (this.epoch !== epoch) return null;
        console.warn('[game] AI failed, playing a random legal move', e);
      }
      if (this.epoch !== epoch) return null;
      if (!mv) mv = this.randomLegal();
      else {
        const piece = this.rules.pieceAt(mv.from);
        const lastRank = mv.to[1] === (side === 'w' ? '8' : '1');
        const promotion = piece?.role === 'pawn' && lastRank ? (mv.promotion ?? 'queen') : undefined;
        mv = { from: mv.from, to: mv.to, promotion };
        if (!this.rules.isLegal(mv.from, mv.to, mv.promotion)) {
          console.warn('[game] AI returned an illegal move, substituting', mv);
          mv = this.randomLegal();
        }
      }
      if (!this.instant) {
        const wait = this.aiMinDelay - (Date.now() - t0);
        if (wait > 0) await sleep(wait);
        if (this.epoch !== epoch) return null;
      }
      return mv;
    } finally {
      this.bus.emit('ai:thinking', { side, thinking: false });
    }
  }

  private randomLegal(): Intent {
    const all = this.rules.allLegalMoves();
    return all[Math.floor(Math.random() * all.length)];
  }

  private async resolve(intent: Intent, epoch: number): Promise<void> {
    const p = this.presenter;
    this.setState('resolving');
    const res = this.rules.move(intent.from, intent.to, intent.promotion);
    if (!res) { console.error('[game] move rejected by rules', intent); return; }
    this.skipRequested = false;
    p.markCheck(null);
    this.bus.emit('move:resolved', res);
    this.setState('sequence');

    const run = async (fn: () => Promise<void>) => {
      const pr = fn();
      if (this.skipRequested) p.skip();
      await pr;
    };

    await run(() => p.playMove(res));
    if (this.epoch !== epoch) return;
    if (res.promotion) {
      await run(() => p.playPromotion(res, res.promotion!));
      if (this.epoch !== epoch) return;
    }
    p.syncToFen(res.fenAfter);

    this.setState('postMove');
    const turn = this.rules.turn();
    const kingSq = this.rules.kingSquare(turn);
    const end = this.rules.gameOver();
    if (res.check && kingSq) {
      this.bus.emit('check', { side: turn, kingSquare: kingSq });
      p.markCheck(kingSq);
      if (res.mate) {
        // The mate sequence lasts ~5 s; the game-over overlay is due ~3 s after it STARTS, so run them concurrently.
        const seq = run(() => p.playCheckmate(res, kingSq));
        if (!this.instant) await Promise.race([seq, sleep(3000)]);
        if (this.epoch !== epoch) return;
        if (end) this.finish(end);
        await seq;
        return;
      }
      await run(() => p.playCheck(res, kingSq));
    } else if (end) {
      await run(() => p.playStalemate(res));
    }
    if (this.epoch !== epoch) return;
    if (end) { this.finish(end); return; }
    this.setState('turnEnd');
  }

  private finish(end: GameEnd): void {
    this.result = end;
    this.setState('gameOver');
    this.bus.emit('game:over', end);
  }
}

export function createGameController(deps: ControllerDeps): GameController {
  return new GameController(deps);
}
