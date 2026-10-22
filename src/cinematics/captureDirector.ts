// Capture director (choreography §1/§2): one master GSAP timeline per capture with the labels
// setup -> face -> approach -> attack -> impact -> resolve -> cleanup.
import { Vector3 } from 'three';
import type { PieceActor, SequenceContext } from '../contracts';
import { restYaw, yawToward } from '../contracts';
import { CameraDriver } from './cameraDriver';
import { FightFrame } from './fightFrame';
import { pickShot } from './shotPicker';
import { CHOREOGRAPHIES } from './choreographies';
import type { AttackPlacement, CaptureEnv, ChoreoPlan, ResolvePlacement } from './choreographies/types';
import { clamp, flatDir, flatDist, socketPos, wrapPi } from './common';
import { ShatterJob } from './shatterJob';
import { perpToSeat, type ShotInputs } from './shots';
import type { Stage } from './stage';
import { hitStopPlan, type WarpPlan } from './timeWarp';

/** captureMode 'quick' plays the timeline at 2.5x (~40 % of the length). */
export const QUICK_SCALE = 2.5;
/** Bystanders are only dimmed slightly (the lighting rig makes the fighters stand out). */
const DIM = 0.15;
const SETUP_END = 0.1;
const FACE_DUR = 0.2;
/** The Attack clip's follow-through is played this much faster so a capture does not drag. */
const TAIL_START = 0.35;
const TAIL_SPEEDUP = 1.6;

export interface CaptureActors { attacker: PieceActor; defender: PieceActor }

/** Find the actors for a capture (the defender stands on capturedSquare for en passant). */
export function findCaptureActors(ctx: SequenceContext): CaptureActors | null {
  const attacker = ctx.board.actorAt(ctx.move.from);
  const defender = ctx.board.actorAt(ctx.move.capturedSquare ?? ctx.move.to);
  if (!attacker || !defender || attacker === defender) return null;
  return { attacker, defender };
}

function impulseFor(dir: Vector3, vel: Vector3 | null): Vector3 {
  const out = dir.clone();
  if (vel && vel.lengthSq() > 0.0025) out.multiplyScalar(0.7).addScaledVector(vel.clone().normalize(), 0.3);
  out.y = 0;
  if (out.lengthSq() < 1e-6) out.copy(dir);
  return out.normalize();
}

/** captureMode 'off': 0.35 s slide + a quick shatter, no camera borrow, no dim. */
export function buildOffCapture(stage: Stage, { attacker, defender }: CaptureActors): void {
  const { ctx } = stage;
  const { board, move, bus } = ctx;
  const A = board.squareCenter(move.from, new Vector3());
  const D = board.squareCenter(move.capturedSquare ?? move.to, new Vector3());
  const To = board.squareCenter(move.to, new Vector3());
  const dir = flatDir(A, D);
  const job = new ShatterJob(stage, defender, 400);
  job.prefetch();
  bus.emit('capture:begin', { attacker: attacker.role, defender: defender.role, attackerFaction: attacker.faction, defenderFaction: defender.faction, square: move.to });
  attacker.setYaw(yawToward(A, D));
  stage.bus('attack:whoosh', { role: attacker.role, faction: attacker.faction });
  stage.moveTo(attacker, To, 0, 0.35, 'power2.in');
  stage.at(0.28, () => {
    stage.bus('capture:impact', { attacker: attacker.role, defender: defender.role, attackerFaction: attacker.faction, defenderFaction: defender.faction, heavy: false });
    ctx.fx.flash(defender);
    job.run({ impulseDir: dir, magnitude: 0.8 });
  });
  stage.yaw(attacker, restYaw(attacker.side), 0.3, 0.15);
  stage.tl.set({}, {}, 0.45);
  stage.onSettle((reason) => {
    attacker.root.position.set(To.x, 0, To.z);
    attacker.setYaw(restYaw(attacker.side));
    board.setActorSquare(attacker, move.to);
    job.settle(reason);
    stage.bus('capture:end', { square: move.to });
  });
}

/** captureMode 'full' / 'quick'. */
export function buildFullCapture(stage: Stage, { attacker, defender }: CaptureActors, quick: boolean): void {
  const { ctx, tl } = stage;
  const { board, camera, fx, bus, move } = ctx;
  const A = board.squareCenter(move.from, new Vector3());
  const D = board.squareCenter(move.capturedSquare ?? move.to, new Vector3());
  const To = board.squareCenter(move.to, new Vector3());
  const dir = flatDir(A, D);
  const dist = flatDist(A, D);
  const strikeRange = attacker.extras.strikeRange;
  const S = dist > strikeRange + 0.05 ? D.clone().addScaledVector(dir, -strikeRange) : A.clone();

  // ------------------------------------------------------------ setup (imperative; runs before the first tick)
  const job = new ShatterJob(stage, defender);
  job.prefetch();
  bus.emit('capture:begin', { attacker: attacker.role, defender: defender.role, attackerFaction: attacker.faction, defenderFaction: defender.faction, square: move.to });

  let driver: CameraDriver | null = null;
  let restoreStarted = false;
  try {
    const handle = camera.borrow();
    driver = new CameraDriver(handle, () => board.allActors());
  } catch (e) { console.warn('[cinematics] camera.borrow failed', e); }
  const seatZ: 1 | -1 = (driver ? camera.camera.position.z : 1) >= 0 ? 1 : -1;
  const startRestore = (duration: number) => {
    if (restoreStarted || !driver) return;
    restoreStarted = true; driver.released = true; frame.release();
    stage.safe(() => { stage.track(camera.restore(duration)); });
  };

  const bystanders = board.allActors().filter((a) => a !== attacker && a !== defender);
  const startYaw = new Map<PieceActor, number>(bystanders.map((a) => [a, a.getYaw()]));
  const centre = A.clone().lerp(D, 0.5);
  const setDim = (v: number) => { for (const a of bystanders) a.setDim(v); };
  stage.tweenEach(0, 0.3, 0, DIM, setDim);
  // nearby pieces watch the fight: kinematics head/spine look-at when available, else a short yaw turn
  const watchers = bystanders.filter((a) => Math.hypot(a.root.position.x - centre.x, a.root.position.z - centre.z) <= 5.5);
  const lookPoint = new Vector3(centre.x, 0.9, centre.z);
  if (stage.hasKinematics) {
    stage.at(0.05, () => { for (const a of watchers) stage.look(a, lookPoint, 0.7); });
  } else {
    for (const a of watchers) {
      const ap = a.root.position;
      const rest = restYaw(a.side);
      const turn = clamp(wrapPi(yawToward(ap, centre) - rest) * 0.4, -0.7, 0.7);
      stage.yaw(a, rest + turn, 0.05, 0.35, 'power2.out');
    }
  }

  // ------------------------------------------------------------ face
  const t0 = SETUP_END + FACE_DUR;
  stage.yaw(attacker, yawToward(A, D), SETUP_END, FACE_DUR);
  stage.yaw(defender, yawToward(D, A), SETUP_END, FACE_DUR);

  // ------------------------------------------------------------ lighting + occluder fading
  const frame = new FightFrame(stage, {
    driver, keyFaction: attacker.faction, rimFaction: defender.faction,
    focus: () => [attacker.root.position, defender.root.position], bystanders: () => bystanders,
  });

  // ------------------------------------------------------------ choreography
  const perp = perpToSeat(dir, seatZ);
  const inputs: ShotInputs = {
    attacker: () => attacker.root.position, defender: () => defender.root.position, seatZ,
    aspect: () => camera.camera.aspect || 16 / 9,
  };
  const env: CaptureEnv = {
    stage, ctx, attacker, defender, faction: attacker.faction, defFaction: defender.faction, quick,
    A, D, To, dir, perp, dist, strikeRange, S, t0, isEnPassant: move.isEnPassant, seatZ, inputs,
    pickShot: (name, o) => pickShot(name, inputs, bystanders, board.allActors(), o),
    placeAttack(earliest, desired): AttackPlacement {
      const at = attacker.attackTimeline();
      const imp = at.labels.impact ?? attacker.extras.impactTime;
      const attackAt = Math.max(earliest, (desired ?? 0) - imp);
      tl.add(at, attackAt);
      const impactAt = attackAt + imp;
      stage.at(Math.max(attackAt, impactAt - 0.22), () => bus.emit('attack:whoosh', { role: attacker.role, faction: attacker.faction }));
      const rawEnd = attackAt + Math.max(at.duration(), imp);
      const cut = impactAt + TAIL_START;
      let end = rawEnd;
      if (rawEnd > cut + 0.1) {
        stage.at(cut, () => { at.timeScale(TAIL_SPEEDUP); });
        end = cut + (rawEnd - cut) / TAIL_SPEEDUP;
      }
      return { attackAt, impactAt, end };
    },
    resolve(at, from, o): ResolvePlacement {
      // slide onto `to` during the Attack's follow-through (no gait: the clip is still driving the pose)
      const walkEnd = stage.walk(attacker, from, To, at, { speed: 1.6, minDur: 0.3, maxDur: 0.7, idle: false, gait: false });
      const turnEnd = stage.yaw(attacker, restYaw(attacker.side), at, Math.max(0.3, walkEnd - at));
      const vStart = Math.max(walkEnd, turnEnd, o?.after ?? 0);
      const vEnd = stage.clip(attacker, 'Victory', vStart, o?.victoryMax ?? (quick ? 0.6 : 0.8));
      return { resolveAt: at, walkEnd: vStart, end: Math.max(vStart, vEnd) };
    },
  };
  const plan: ChoreoPlan = CHOREOGRAPHIES[attacker.role](env);

  // ------------------------------------------------------------ labels
  tl.addLabel('setup', 0).addLabel('face', SETUP_END).addLabel('approach', plan.approachAt).addLabel('attack', plan.attackAt)
    .addLabel('impact', plan.impactAt).addLabel('resolve', plan.resolveAt).addLabel('cleanup', plan.walkEnd);

  // ------------------------------------------------------------ impact
  const q = quick ? 0.4 : 1;
  const warp: WarpPlan = plan.warp ?? hitStopPlan(plan.hitStopMs * q, (0.25 + (['queen', 'king', 'rook'].includes(defender.role) ? 0.2 : 0)) * q, 0.6 * (quick ? 0.6 : 1));
  const decal = plan.decal ?? (attacker.faction === 'emberhold' ? 'scorch' : 'frost');
  // weapon velocity sample just before impact -> debris direction
  const p1 = new Vector3(); const p2 = new Vector3();
  let sampled = false;
  stage.at(Math.max(0, plan.impactAt - 0.06), () => { socketPos(attacker, 'socket_weapon_R', p1); sampled = true; });
  stage.at(plan.impactAt, () => {
    bus.emit('capture:impact', { attacker: attacker.role, defender: defender.role, attackerFaction: attacker.faction, defenderFaction: defender.faction, heavy: plan.heavy });
    stage.warp.play(warp);
    camera.shake(plan.trauma);
    if (attacker.role !== 'bishop') { // weapon meets weapon (spells have no clash)
      bus.emit('clash', { attackerFaction: attacker.faction, defenderFaction: defender.faction, heavy: plan.heavy });
      fx.emit('sparks', D.clone().setY(0.8), { count: plan.heavy ? 28 : 14, scale: plan.heavy ? 1 : 0.7 });
    }
    stage.impulse(D, plan.trauma * 1.3, 3.2); // nearby pieces wobble away from the blow
    if (sampled) socketPos(attacker, 'socket_weapon_R', p2);
    fx.decal(D.clone(), decal);
  });
  // anticipation: the defender braces (leans away) as the blow winds up, then recoils on impact
  const braceAt = Math.max(plan.attackAt, plan.impactAt - 0.6);
  stage.tilt(defender, -0.1, braceAt, Math.max(0.2, plan.impactAt - braceAt), 'power2.out');
  stage.tilt(defender, -0.4, plan.impactAt, 0.12, 'power3.out');
  stage.moveTo(defender, { x: D.x + dir.x * 0.22, z: D.z + dir.z * 0.22 }, plan.impactAt, 0.15, 'power3.out');
  // aftershock when the body breaks
  const hitEnd = stage.poseClip(defender, 'HitReact', plan.holdHitReact ? 0.55 : 0.6, plan.impactAt, 0.12);
  const shatterAt = hitEnd + (plan.shatterDelay ?? 0);
  stage.at(shatterAt, () => {
    fx.flash(defender);
    camera.shake(plan.trauma * 0.6);
    const vel = sampled ? p2.clone().sub(p1) : null;
    job.run({
      impulseDir: plan.shatter.impulseDir ?? impulseFor(dir, vel),
      magnitude: plan.shatter.magnitude, cutNormal: plan.shatter.cutNormal,
    });
  });

  // ------------------------------------------------------------ camera
  if (driver) {
    driver.setCues(plan.cues);
    driver.setPunch(plan.impactAt, 0.5, plan.heavy ? 6 : 4, plan.heavy ? 0.3 : 0.2);
  }
  frame.fadeIn(0, 0.3);
  tl.eventCallback('onUpdate', () => frame.update(tl.time()));

  // ------------------------------------------------------------ cleanup
  const cleanupAt = plan.walkEnd;
  stage.at(cleanupAt, () => {
    startRestore(quick ? 0.5 : 1.1); board.setActorSquare(attacker, move.to);
    for (const a of watchers) stage.unlook(a);
  });
  stage.tweenEach(cleanupAt, 0.3, DIM, 0, setDim);
  frame.fadeOut(cleanupAt, 0.3);
  for (const a of bystanders) if (startYaw.has(a)) stage.yaw(a, startYaw.get(a)!, cleanupAt, 0.35, 'power2.out');
  tl.set({}, {}, Math.max(plan.end, cleanupAt + 0.4, shatterAt + 0.1));

  stage.onSettle((reason) => {
    attacker.root.position.set(To.x, 0, To.z);
    attacker.setYaw(restYaw(attacker.side));
    attacker.setWeaponSummon(0);
    board.setActorSquare(attacker, move.to);
    attacker.play('Idle', { fade: reason === 'complete' ? 0.2 : 0 });
    job.settle(reason);
    for (const a of bystanders) { a.setDim(0); a.setYaw(startYaw.get(a) ?? restYaw(a.side)); }
    // skip/watchdog: snap the camera back instantly, even if a restore tween is already in flight
    if (driver && (!restoreStarted || reason !== 'complete')) { restoreStarted = true; driver.released = true; stage.safe(() => { stage.track(camera.restore(reason === 'complete' ? 0.4 : 0)); }); }
    stage.bus('capture:end', { square: move.to });
  });
}
