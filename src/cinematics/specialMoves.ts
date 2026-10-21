// Castling, promotion, check, checkmate, stalemate (choreography §5).
import { Vector3 } from 'three';
import type { PieceActor, PromotionRole, Square } from '../contracts';
import { restYaw, SIDE_FACTION, yawToward } from '../contracts';
import { CameraDriver } from './cameraDriver';
import { buildTravel, settleActor } from './moveSequence';
import { clamp, flatDist, smoothstep, socketPos, wrapPi } from './common';
import { ShatterJob } from './shatterJob';
import { orbit360 } from './shots';
import type { Stage } from './stage';

// ------------------------------------------------------------------ castle
export function buildCastle(stage: Stage, king: PieceActor, rook: PieceActor): void {
  const { ctx } = stage;
  const { move } = ctx;
  const kA = ctx.board.squareCenter(move.from, new Vector3()); const kB = ctx.board.squareCenter(move.to, new Vector3());
  const rA = ctx.board.squareCenter(move.rookFrom!, new Vector3()); const rB = ctx.board.squareCenter(move.rookTo!, new Vector3());
  const kingEnd = buildTravel(stage, king, kA, kB, 0);

  // The rook does its hop as one high flat-topped arc so it clears the king (1.7 tall) the whole time they
  // overlap horizontally, then drops straight onto its square just after the king has passed.
  const n = Math.max(1, Math.round(flatDist(rA, rB)));
  const hopDur = 0.8 + 0.1 * n;
  const start = Math.max(0.1, kingEnd - 0.1 - hopDur);
  stage.yaw(rook, yawToward(rA, rB), 0, 0.2);
  const hopEnd = start + hopDur;
  stage.proxy(start, hopDur, 'none', (p) => {
    const h = smoothstep((p - 0.12) / 0.63);
    rook.root.position.x = rA.x + (rB.x - rA.x) * h;
    rook.root.position.z = rA.z + (rB.z - rA.z) * h;
    rook.root.position.y = p < 0.2 ? 2.0 * (1 - (1 - p / 0.2) ** 2) : p < 0.75 ? 2.0 : 2.0 * (1 - ((p - 0.75) / 0.25) ** 2);
  });
  stage.killOn(rook.root.position);
  stage.at(hopEnd, () => {
    rook.root.position.set(rB.x, 0, rB.z);
    ctx.bus.emit('move:step', { faction: rook.faction, role: 'rook' });
    ctx.fx.emit(rook.faction === 'emberhold' ? 'dustPuff' : 'frostMist', rB.clone().setY(0.05), { count: 8, scale: 0.8 });
  });
  const rookEnd = stage.yaw(rook, restYaw(rook.side), hopEnd, 0.25);

  const end = Math.max(kingEnd, rookEnd);
  stage.at(end, () => {
    ctx.fx.emit('dustPuff', kB.clone().setY(0.05), { count: 8, scale: 0.8 });
    ctx.fx.emit('dustPuff', rB.clone().setY(0.05), { count: 8, scale: 0.8 });
    ctx.bus.emit('castle', { side: move.side });
  });
  stage.tl.set({}, {}, end + 0.1);
  settleActor(stage, king, move.to, kB);
  settleActor(stage, rook, move.rookTo!, rB);
}

// ------------------------------------------------------------------ promotion
export function buildPromotion(stage: Stage, pawn: PieceActor | undefined, role: PromotionRole): void {
  const { ctx } = stage;
  const { board, fx, move } = ctx;
  const faction = SIDE_FACTION[move.side];
  const pos = board.squareCenter(move.to, new Vector3());
  const colDur = 0.8;
  let spawned: PieceActor | null = null;
  let pawnGone = false;

  const reveal = () => {
    if (!pawnGone) { pawnGone = true; if (pawn) board.removeActor(pawn); }
    if (!spawned) {
      spawned = board.spawnActor(faction, role, move.to);
      spawned.setYaw(restYaw(move.side));
    }
    return spawned;
  };

  stage.at(0, () => stage.safe(() => fx.column(pos.clone(), faction, colDur)));
  stage.at(0.01, () => ctx.bus.emit('promotion', { side: move.side, role, square: move.to }));
  stage.at(colDur * 0.65, () => {
    const a = reveal();
    // The cocoon cracks and the promoted piece is revealed with its Victory.
    if (a.hasClip('Victory')) {
      const v = a.clipTimeline('Victory');
      if (v.duration() > 1.2) v.timeScale(v.duration() / 1.2);
      stage.tl.add(v, stage.tl.time());
    }
    fx.emit('sparks', pos.clone().setY(0.6), { count: 20, scale: 0.8 });
  });
  stage.tl.set({}, {}, colDur * 0.65 + 1.3);
  stage.onSettle(() => {
    const a = reveal();
    a.root.position.set(pos.x, 0, pos.z);
    a.setYaw(restYaw(move.side));
    a.play('Idle', { fade: 0 });
  });
}

// ------------------------------------------------------------------ check
const AURA_TINT = { emberhold: 0xff4a2a, rime: 0x66e6ff } as const;

export function buildCheck(stage: Stage, kingSquare: Square): void {
  const { ctx } = stage;
  const { board, fx, move } = ctx;
  const king = board.actorAt(kingSquare);
  if (!king) { stage.tl.set({}, {}, 0.01); return; }
  const checker = board.actorAt(move.to);
  const glancer = checker && checker !== king ? checker : null;

  if (glancer) {
    const rest = restYaw(glancer.side);
    const turn = clamp(wrapPi(yawToward(glancer.root.position, king.root.position) - rest) * 0.7, -1.1, 1.1);
    stage.yaw(glancer, rest + turn, 0, 0.3, 'power2.out');
    stage.yaw(glancer, rest, 1.1, 0.3, 'power2.inOut');
  }
  // king flinch
  stage.poseClip(king, 'HitReact', 0.3, 0.25, 0.15);
  stage.proxy(0.55, 0.3, 'power2.inOut', (p) => king.scrub('HitReact', king.clipDuration('HitReact') * 0.3 * (1 - p)));

  const aura = () => fx.aura(socketPos(king, 'socket_head', new Vector3()), king.faction);
  stage.at(0.3, aura);
  stage.at(0.95, aura);
  stage.at(0.2, () => board.tintSquare(kingSquare, AURA_TINT[king.faction]));
  stage.tl.set({}, {}, 1.5);
  stage.onSettle(() => {
    board.tintSquare(kingSquare, null);
    if (glancer) glancer.setYaw(restYaw(glancer.side));
    king.play('Idle', { fade: 0 });
  });
}

// ------------------------------------------------------------------ checkmate
export const MATE_ORBIT_SECONDS = 5.2;

export function buildCheckmate(stage: Stage, kingSquare: Square): void {
  const { ctx, tl } = stage;
  const { board, camera, fx } = ctx;
  const king = board.actorAt(kingSquare);
  if (!king) { tl.set({}, {}, 0.01); return; }
  const kingFaction = king.faction;
  const winners = board.allActors().filter((a) => a.side !== king.side);
  const job = new ShatterJob(stage, king);
  job.prefetch();
  const K = king.root.position.clone();

  let driver: CameraDriver | null = null;
  let restoreStarted = false;
  try {
    driver = new CameraDriver(camera.borrow(), () => board.allActors());
    const cp = camera.camera.position;
    driver.setCues([{ at: 0, shot: orbit360(() => king.root.position, MATE_ORBIT_SECONDS, Math.atan2(cp.x - K.x, cp.z - K.z), 3.4) }], 0.8);
    const d = driver;
    tl.eventCallback('onUpdate', () => d.update(tl.time()));
  } catch (e) { console.warn('[cinematics] camera.borrow failed', e); }
  const startRestore = (duration: number) => {
    if (restoreStarted || !driver) return;
    restoreStarted = true; driver.released = true;
    stage.safe(() => { stage.track(camera.restore(duration)); });
  };

  // the king drops to a knee (HitReact held), cracks spread over 1.5 s
  stage.poseClip(king, 'HitReact', 0.6, 0.2, 0.6);
  stage.at(0.4, () => {
    stage.safe(() => fx.sweep(king, kingFaction === 'emberhold' ? 'ember' : 'frost', 1.5));
    fx.decal(K.clone(), 'crack');
  });
  stage.at(1.2, () => fx.emit(kingFaction === 'emberhold' ? 'embers' : 'iceGlitter', K.clone().setY(0.8), { count: 20, scale: 0.8 }));
  // winners celebrate (staggered; capped clip length keeps phones light)
  winners.forEach((w, i) => stage.clip(w, 'Victory', 0.5 + (i % 8) * 0.06, 1.6));
  // it crumbles in slow motion
  const crumbleAt = 2.4;
  stage.at(crumbleAt, () => {
    stage.warp.play({ segments: [{ scale: 0.3, seconds: 1.4 }], ramp: 0.8 });
    camera.shake(0.6);
    fx.flash(king);
    job.run({ impulseDir: new Vector3(0, 0.3, 1).normalize(), magnitude: 1.2 });
  });
  stage.at(MATE_ORBIT_SECONDS - 0.9, () => startRestore(1.0));
  tl.set({}, {}, MATE_ORBIT_SECONDS);
  stage.onSettle((reason) => {
    job.settle(reason);
    board.tintSquare(kingSquare, null);
    for (const w of winners) { w.setYaw(restYaw(w.side)); w.play('Idle', { fade: 0 }); }
    // skip/watchdog: snap the camera back instantly, even if a restore tween is already in flight
    if (driver && (!restoreStarted || reason !== 'complete')) { restoreStarted = true; driver.released = true; stage.safe(() => { stage.track(camera.restore(reason === 'complete' ? 0.4 : 0)); }); }
  });
}

// ------------------------------------------------------------------ stalemate
export function buildStalemate(stage: Stage): void {
  const { ctx } = stage;
  const { board, fx } = ctx;
  const kings = board.allActors().filter((a) => a.role === 'king');
  if (kings.length >= 2) {
    const [a, b] = kings;
    stage.yaw(a, yawToward(a.root.position, b.root.position), 0, 0.6);
    stage.yaw(b, yawToward(b.root.position, a.root.position), 0, 0.6);
    stage.yaw(a, restYaw(a.side), 2.1, 0.5);
    stage.yaw(b, restYaw(b.side), 2.1, 0.5);
  }
  stage.at(0.3, () => fx.mist());
  stage.tl.set({}, {}, 2.7);
  stage.onSettle(() => { for (const k of kings) { k.setYaw(restYaw(k.side)); k.play('Idle', { fade: 0 }); } });
}
