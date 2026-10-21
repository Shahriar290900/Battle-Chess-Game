// STUB (lead) — replaced by cinematics. Plain tweens, no fights; always ends in the final board state.
import { gsap } from 'gsap';
import { Vector3 } from 'three';
import type { SequenceContext, SequencePlayer } from '../contracts';
import { restYaw } from '../contracts';

export function createSequencePlayer(): SequencePlayer {
  let tl: gsap.core.Timeline | null = null;
  const slide = (ctx: SequenceContext, from: string, to: string, t: gsap.core.Timeline, at = 0) => {
    const a = ctx.board.actorAt(from);
    if (!a) return;
    const p = ctx.board.squareCenter(to, new Vector3());
    t.to(a.root.position, { x: p.x, z: p.z, duration: 0.45, ease: 'power2.inOut' }, at);
    ctx.board.setActorSquare(a, to);
  };
  const run = (build: (t: gsap.core.Timeline) => void, ctx: SequenceContext) =>
    new Promise<void>((resolve) => {
      tl = gsap.timeline({ onComplete: () => { tl = null; ctx.board.syncToFen(ctx.move.fenAfter); resolve(); } });
      build(tl);
      if (tl.duration() === 0) tl.progress(1);
    });
  const player: SequencePlayer = {
    get running() { return tl !== null; },
    move: (ctx) => run((t) => slide(ctx, ctx.move.from, ctx.move.to, t), ctx),
    capture: (ctx) => run((t) => {
      const victim = ctx.board.actorAt(ctx.move.capturedSquare ?? ctx.move.to);
      if (victim) ctx.board.removeActor(victim);
      slide(ctx, ctx.move.from, ctx.move.to, t);
    }, ctx),
    castle: (ctx) => run((t) => {
      slide(ctx, ctx.move.from, ctx.move.to, t);
      if (ctx.move.rookFrom && ctx.move.rookTo) slide(ctx, ctx.move.rookFrom, ctx.move.rookTo, t);
    }, ctx),
    promote: async (ctx, role) => {
      const pawn = ctx.board.actorAt(ctx.move.to);
      if (pawn) ctx.board.removeActor(pawn);
      const a = ctx.board.spawnActor(ctx.move.side === 'w' ? 'emberhold' : 'rime', role, ctx.move.to);
      a.setYaw(restYaw(ctx.move.side));
    },
    check: async () => {},
    checkmate: async () => {},
    stalemate: async () => {},
    skip() { tl?.progress(1); },
  };
  return player;
}
