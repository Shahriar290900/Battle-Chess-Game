// Castling, promotion, check, checkmate, stalemate (choreography §5).
import { Vector3 } from 'three';
import type { PieceActor, PromotionRole, Square } from '../contracts';
import { restYaw, SIDE_FACTION, yawToward } from '../contracts';
import { CameraDriver } from './cameraDriver';
import { buildTravel, settleActor } from './moveSequence';
import { clamp, flatDist, smoothstep, socketPos } from './common';
import { FightFrame } from './fightFrame';
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
    ctx.bus.emit('land', { faction: rook.faction, role: 'rook', strength: 0.8 }); // dropped from 2 units
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

// ------------------------------------------------------------------ checkmate
/** Nominal length of the surrender sequence (extended when many pieces surrender). */
export const MATE_MIN_SECONDS = 4.2;

/** Procedural surrender (no Surrender clip): lower the body, pitch forward, bow the head. Final values held. */
const SURRENDER_POSE = { king: { dy: -0.38, rx: 0.42 }, other: { dy: -0.14, rx: 0.24 } } as const;
const poseFor = (a: PieceActor) => (a.role === 'king' ? SURRENDER_POSE.king : SURRENDER_POSE.other);

function snapSurrender(a: PieceActor): void {
  if (a.hasClip('Surrender')) { a.scrub('Surrender', a.clipDuration('Surrender')); return; }
  const p = poseFor(a);
  a.model.position.y = p.dy; a.model.rotation.x = p.rx;
}

/**
 * Checkmate: slow orbit around the mated king, who plays Surrender (kneels, held). Then, staggered 0.1-0.2 s,
 * every other piece of the losing side surrenders its weapon (Surrender clip, or a procedural lowering plus a
 * drop puff). Winners raise their weapons (Victory) and look at the fallen king. Nothing is shattered or removed.
 */
export function buildCheckmate(stage: Stage, kingSquare: Square): void {
  const { ctx, tl } = stage;
  const { board, camera, fx } = ctx;
  const king = board.actorAt(kingSquare);
  if (!king) { tl.set({}, {}, 0.01); return; }
  const all = board.allActors();
  const losers = all.filter((a) => a.side === king.side && a !== king)
    .sort((a, b) => king.root.position.distanceTo(a.root.position) - king.root.position.distanceTo(b.root.position));
  const winners = all.filter((a) => a.side !== king.side);
  const step = clamp(1.6 / Math.max(1, losers.length), 0.1, 0.2);
  const KING_AT = 0.35; const LOSERS_AT = 0.95; const CLIP_CAP = 1.8;
  const duration = Math.max(MATE_MIN_SECONDS, LOSERS_AT + losers.length * step + CLIP_CAP + 0.4);
  const K = king.root.position.clone();
  const kingPoint = new Vector3(K.x, 0.5, K.z);
  const winnerFaction = SIDE_FACTION[king.side === 'w' ? 'b' : 'w'];

  // ---- camera: slow full orbit around the king + lighting + occluder fading
  let driver: CameraDriver | null = null;
  let restoreStarted = false;
  try {
    driver = new CameraDriver(camera.borrow(), () => board.allActors());
    const cp = camera.camera.position;
    driver.setCues([{ at: 0, shot: orbit360(() => king.root.position, duration, Math.atan2(cp.x - K.x, cp.z - K.z), 3.8) }], 0.8);
  } catch (e) { console.warn('[cinematics] camera.borrow failed', e); }
  const bystanders = all.filter((a) => a !== king);
  const frame = new FightFrame(stage, {
    driver, keyFaction: winnerFaction, rimFaction: king.faction,
    focus: () => [king.root.position], bystanders: () => bystanders,
  });
  frame.fadeIn(0, 0.4);
  frame.fadeOut(duration - 0.6, 0.5);
  tl.eventCallback('onUpdate', () => frame.update(tl.time()));
  const startRestore = (d: number) => {
    if (restoreStarted || !driver) return;
    restoreStarted = true; driver.released = true; frame.release();
    stage.safe(() => { stage.track(camera.restore(d)); });
  };

  // ---- the mated king surrenders and kneels
  const dropEvent = (a: PieceActor) => stage.bus('weapon:drop', { faction: a.faction, role: a.role });
  const surrender = (a: PieceActor, at: number): number => {
    if (a.hasClip('Surrender')) {
      const end = stage.clip(a, 'Surrender', at, CLIP_CAP);
      const dur = end - at;
      stage.at(at + dur * 0.6, () => { dropEvent(a); fx.emit('dustPuff', socketPos(a, 'socket_weapon_R', new Vector3()).setY(0.05), { count: 4, scale: 0.5 }); });
      return end;
    }
    const p = poseFor(a);
    const dur = a.role === 'king' ? 0.8 : 0.5;
    stage.proxy(at, dur, 'power2.out', (u) => { a.model.position.y = p.dy * u; a.model.rotation.x = p.rx * u; });
    stage.at(at + 0.2, () => { dropEvent(a); fx.emit('dustPuff', socketPos(a, 'socket_weapon_R', new Vector3()).setY(0.05), { count: 4, scale: 0.5 }); });
    return at + dur;
  };
  stage.at(KING_AT, () => stage.bus('surrender', { side: king.side }));
  stage.at(KING_AT, () => stage.warp.play({ segments: [{ scale: 0.6, seconds: 1.1 }], ramp: 0.7 }));
  const kingEnd = surrender(king, KING_AT);
  stage.at(KING_AT + 0.7, () => {
    camera.shake(0.3); fx.emit('dustPuff', K.clone().setY(0.05), { count: 10, scale: 1 });
    ctx.bus.emit('land', { faction: king.faction, role: 'king', strength: 0.7 }); // the knees meet the stone
  });

  // ---- every other piece of the losing side drops its weapon, staggered
  let lastEnd = kingEnd;
  losers.forEach((a, i) => { lastEnd = Math.max(lastEnd, surrender(a, LOSERS_AT + i * step)); });

  // ---- winners raise their weapons and look at the fallen king
  winners.forEach((w, i) => stage.clip(w, 'Victory', 0.5 + (i % 8) * 0.06, 1.6));
  if (stage.hasKinematics) stage.at(0.3, () => { for (const w of winners) stage.look(w, kingPoint, 0.8); });

  stage.at(duration - 0.9, () => startRestore(0.9));
  tl.set({}, {}, Math.max(duration, lastEnd + 0.2));
  stage.onSettle((reason) => {
    // final, held state: the losing side kneels / has dropped its weapons; nothing is removed or shattered
    for (const a of [king, ...losers]) snapSurrender(a);
    for (const w of winners) { w.setYaw(restYaw(w.side)); w.play('Idle', { fade: 0 }); }
    board.tintSquare(kingSquare, null);
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
