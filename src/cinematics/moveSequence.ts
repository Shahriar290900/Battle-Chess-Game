// Non-capture moves: pawn/bishop/queen walk or glide (Move clip, ~2.2 units/s), rook hops per square,
// knight leaps along its L, king walks heavily. Turn to face the travel direction, then back to restYaw.
import { Vector3 } from 'three';
import type { PieceActor } from '../contracts';
import { restYaw, yawToward } from '../contracts';
import { flatDir, flatDist, lerp, smoothstep } from './common';
import { lElbow, lPath } from './choreographies/knight';
import type { Stage } from './stage';

export const MOVE_SPEED = 2.2;
export const KING_SPEED = 1.4;
const HOP = 0.25;

/** Queue a travel of `actor` from A to B starting at `at`. Returns the time it is standing (rest yaw) on B. */
export function buildTravel(stage: Stage, actor: PieceActor, A: Vector3, B: Vector3, at: number): number {
  const { ctx } = stage;
  const faction = actor.faction;
  const rest = restYaw(actor.side);
  let t = stage.yaw(actor, yawToward(A, B), at, 0.2);
  let end: number;
  switch (actor.role) {
    case 'rook': {
      const dir = flatDir(A, B);
      const n = Math.max(1, Math.round(flatDist(A, B)));
      const puff = faction === 'emberhold' ? 'dustPuff' : 'frostMist';
      let prev = A.clone();
      for (let i = 1; i <= n; i++) {
        const P = i === n ? B : A.clone().addScaledVector(dir, i);
        t = stage.hop(actor, prev, P, t, HOP, 0.28, { puff });
        prev = P;
      }
      end = t;
      break;
    }
    case 'knight': {
      const C = lElbow(A, B);
      stage.tilt(actor, -0.3, t, 0.15, 'power2.out');
      t += 0.15;
      const dur = 0.75;
      end = stage.arc(actor, lPath(A, C, B, 1.2), t, dur, 'power1.inOut', { faceTangent: 0.4, pitch: (p) => lerp(-0.3, 0.25, smoothstep(p)) });
      stage.tilt(actor, 0, end, 0.15, 'power2.out');
      stage.at(end, () => { ctx.bus.emit('move:step', { faction, role: 'knight' }); ctx.fx.emit('dustPuff', B.clone().setY(0.05), { count: 8, scale: 0.8 }); });
      break;
    }
    case 'king':
      end = stage.walk(actor, A, B, t, { speed: KING_SPEED, minDur: 0.6, maxDur: 2.4, stepEvery: 0.5, dust: true });
      break;
    default:
      end = stage.walk(actor, A, B, t, { speed: MOVE_SPEED, minDur: 0.35, maxDur: 2.0 });
  }
  return stage.yaw(actor, rest, end, 0.25);
}

/** Snap an actor to its final square/pose; idempotent. */
export function settleActor(stage: Stage, actor: PieceActor, sq: string, B: Vector3): void {
  stage.onSettle(() => {
    actor.root.position.set(B.x, 0, B.z);
    actor.setYaw(restYaw(actor.side));
    stage.ctx.board.setActorSquare(actor, sq);
    actor.play('Idle', { fade: stage.reason === 'complete' ? 0.2 : 0 });
  });
}

export function buildMove(stage: Stage, actor: PieceActor): void {
  const { ctx } = stage;
  const A = ctx.board.squareCenter(ctx.move.from, new Vector3());
  const B = ctx.board.squareCenter(ctx.move.to, new Vector3());
  const end = buildTravel(stage, actor, A, B, 0);
  stage.at(end, () => ctx.fx.emit('dustPuff', B.clone().setY(0.05), { count: 5, scale: 0.6 }));
  stage.tl.set({}, {}, end + 0.05);
  settleActor(stage, actor, ctx.move.to, B);
}
