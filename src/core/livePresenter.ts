// Live GamePresenter: drives the real board, camera rig, fx and the cinematics SequencePlayer.
// After every sequence it calls board.syncToFen() as a safety net (architecture §4).
import type {
  AssetRegistry, CameraRig, EventBus, FxApi, MoveResult, PromotionRole, SequenceContext, SequencePlayer, SettingsStore, Side, Square,
} from '../contracts';
import type { BoardImpl } from '../render/board';
import type { GamePresenter } from './presenter';

export interface LivePresenterDeps {
  board: BoardImpl;
  camera: CameraRig;
  fx: FxApi;
  registry: AssetRegistry;
  sequences: SequencePlayer;
  bus: EventBus;
  settings: SettingsStore;
  /** Shows the promotion picker (UI). */
  choosePromotion(side: Side): Promise<PromotionRole | null>;
  cancelPromotion(): void;
}

const CHECK_TINT = 0xff3a2a;

export function createLivePresenter(d: LivePresenterDeps): GamePresenter {
  let checked: Square | null = null;
  let generation = 0; // bumped by reset(): a sequence that outlives its game must not sync a stale FEN
  const ctx = (move: MoveResult): SequenceContext => ({
    move, board: d.board, camera: d.camera, fx: d.fx, registry: d.registry, bus: d.bus, settings: d.settings.get(),
  });
  const run = async (fn: () => Promise<void>, fen?: string) => {
    const gen = generation;
    try { await fn(); } catch (e) { console.error('[presenter] sequence failed', e); }
    if (gen !== generation) return;
    if (fen) d.board.syncToFen(fen);
  };

  return {
    get running() { return d.sequences.running; },
    reset(fen) {
      generation++;
      d.sequences.skip();
      d.board.syncToFen(fen);
      this.markCheck(null);
      },
    syncToFen: (fen) => d.board.syncToFen(fen),
    playMove(m) {
      const c = ctx(m);
      const fn = () => (m.captured ? d.sequences.capture(c) : m.isCastle ? d.sequences.castle(c) : d.sequences.move(c));
      // Promotion moves sync after the reveal: the FEN already holds the promoted piece.
      return run(fn, m.promotion ? undefined : m.fenAfter);
    },
    playPromotion: (m, role) => run(() => d.sequences.promote(ctx(m), role), m.fenAfter),
    playCheck: (m, ksq) => run(() => d.sequences.check(ctx(m), ksq), m.fenAfter),
    playCheckmate: (m, ksq) => run(() => d.sequences.checkmate(ctx(m), ksq), m.fenAfter),
    playStalemate: (m) => run(() => d.sequences.stalemate(ctx(m))),
    skip: () => d.sequences.skip(),
    seatCamera: (side, instant) => d.camera.toSeat(side, { instant }),
    markCheck(sq) {
      if (checked) d.board.tintSquare(checked, null);
      checked = sq;
      if (sq) d.board.tintSquare(sq, CHECK_TINT);
    },
    choosePromotion: (side) => d.choosePromotion(side),
    cancelPromotion: () => d.cancelPromotion(),
  };
}
