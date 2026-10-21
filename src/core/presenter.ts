// The view layer the game controller drives. The controller never touches three.js: it talks to a
// GamePresenter, which has a live implementation (livePresenter.ts: board + camera + SequencePlayer + UI)
// and a headless one (headlessPresenter.ts) for tests and instant replay.
import type { MoveResult, PromotionRole, Side, Square } from '../contracts';

export interface GamePresenter {
  /** True while any sequence is playing. */
  readonly running: boolean;
  /** New game: forget everything and show this position. */
  reset(fen: string): void;
  /** Snap every visual to the position (undo, safety net after sequences). */
  syncToFen(fen: string): void;
  /** Plain move, capture or castle sequence. For promotion moves stops before the reveal. */
  playMove(move: MoveResult): Promise<void>;
  /** Pawn already on the last rank → promoted piece revealed. Called after playMove. */
  playPromotion(move: MoveResult, role: PromotionRole): Promise<void>;
  playCheck(move: MoveResult, kingSquare: Square): Promise<void>;
  playCheckmate(move: MoveResult, kingSquare: Square): Promise<void>;
  /** Stalemate and every other draw. */
  playStalemate(move: MoveResult): Promise<void>;
  /** Finish the running sequence immediately. */
  skip(): void;
  seatCamera(side: Side, instant?: boolean): Promise<void>;
  /** Glow the king's tile (null clears). */
  markCheck(square: Square | null): void;
  /** Ask the human which piece to promote to. Resolves null if dismissed. */
  choosePromotion(side: Side): Promise<PromotionRole | null>;
  /** Close any open promotion picker (new game, undo). */
  cancelPromotion?(): void;
}
