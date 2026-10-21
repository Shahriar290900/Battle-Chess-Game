// SequencePlayer implementation. Every method resolves with the board in its final state, even if fx or
// camera promises never settle (stages are bounded by a watchdog and by guarded tail waits).
import { gsap } from 'gsap';
import type { PieceActor, SequenceContext, SequencePlayer } from '../contracts';
import { buildFullCapture, buildOffCapture, findCaptureActors, QUICK_SCALE } from './captureDirector';
import { clamp } from './common';
import { buildMove } from './moveSequence';
import { buildCastle, buildCheck, buildCheckmate, buildPromotion, buildStalemate } from './specialMoves';
import { Stage } from './stage';

export function createSequencePlayer(): SequencePlayer {
  let current: Stage | null = null;

  const safeSync = (ctx: SequenceContext) => {
    try { ctx.board.syncToFen(ctx.move.fenAfter); } catch (e) { console.warn('[cinematics] syncToFen failed', e); }
  };

  /** Run one stage to completion. `build` queues tweens synchronously and returns the extra speed scale. */
  async function run(ctx: SequenceContext, label: string, build: (stage: Stage) => number | void, opts: { sync?: boolean } = {}): Promise<void> {
    if (current) current.skip(); // a new sequence always finishes the previous one first
    const stage = new Stage(ctx, label);
    current = stage;
    try {
      const modeScale = build(stage) ?? 1;
      stage.start(clamp(ctx.settings.animSpeed || 1, 0.25, 4) * modeScale);
    } catch (e) {
      console.error(`[cinematics] ${label} failed to build`, e);
      stage.finish('skip');
    }
    await stage.done;
    if (current === stage) current = null;
    gsap.globalTimeline.timeScale(1);
    // skipped / watchdog'd / failed sequences re-sync the board as a safety net
    if (stage.reason !== 'complete' || opts.sync) safeSync(ctx);
  }

  const player: SequencePlayer = {
    get running() { return current !== null; },

    async move(ctx) {
      const actor = ctx.board.actorAt(ctx.move.from);
      if (!actor) { safeSync(ctx); return; }
      await run(ctx, 'move', (s) => { buildMove(s, actor); });
    },

    async capture(ctx) {
      const actors = findCaptureActors(ctx);
      if (!actors) {
        // inconsistent board: degrade to a plain move (or just sync)
        const a = ctx.board.actorAt(ctx.move.from);
        if (a) await run(ctx, 'move', (s) => { buildMove(s, a); }, { sync: true }); else safeSync(ctx);
        return;
      }
      const mode = ctx.settings.captureMode;
      await run(ctx, 'capture', (s) => {
        if (mode === 'off') { buildOffCapture(s, actors); return 1; }
        buildFullCapture(s, actors, mode === 'quick');
        return mode === 'quick' ? QUICK_SCALE : 1;
      });
    },

    async castle(ctx) {
      const king = ctx.board.actorAt(ctx.move.from);
      const rook = ctx.move.rookFrom ? ctx.board.actorAt(ctx.move.rookFrom) : undefined;
      if (!king || !rook || !ctx.move.rookTo) { safeSync(ctx); return; }
      await run(ctx, 'castle', (s) => { buildCastle(s, king, rook); });
    },

    async promote(ctx, role) {
      const pawn: PieceActor | undefined = ctx.board.actorAt(ctx.move.to);
      await run(ctx, 'promote', (s) => { buildPromotion(s, pawn, role); });
    },

    async check(ctx, kingSquare) {
      await run(ctx, 'check', (s) => { buildCheck(s, kingSquare); });
    },

    async checkmate(ctx, kingSquare) {
      await run(ctx, 'checkmate', (s) => { buildCheckmate(s, kingSquare); });
    },

    async stalemate(ctx) {
      await run(ctx, 'stalemate', (s) => { buildStalemate(s); });
    },

    skip() { current?.skip(); },
  };
  return player;
}
