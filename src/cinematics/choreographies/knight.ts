// Knight - the leap (choreography §3). Mount rears (0.4 s), parabolic leap along a smooth L-shaped curve
// (peak 1.6), lance/glaive strike on landing. Emberhold: ember trail from the mane. Rime: the mount
// headbutts first (ice crack), then the rider's glaive finishes.
import { Vector3 } from 'three';
import { flatDir, lerp, smoothstep, socketObject } from '../common';
import { HIT_STOP_MS, MAGNITUDE, TRAUMA, type Choreography } from './types';
import { burstAt, shakeAt } from './util';

export const LEAP_PEAK = 1.6;

/** Smooth L: quadratic Bezier A -> elbow -> land, with a parabolic height of `peak`. */
export function lPath(A: Vector3, C: Vector3, B: Vector3, peak: number) {
  return (p: number, out: Vector3) => {
    const u = 1 - p;
    out.set(u * u * A.x + 2 * u * p * C.x + p * p * B.x, 4 * peak * p * u, u * u * A.z + 2 * u * p * C.z + p * p * B.z);
  };
}

/** Elbow of the L: travel the long leg first. */
export function lElbow(A: Vector3, B: Vector3): Vector3 {
  return Math.abs(B.x - A.x) > Math.abs(B.z - A.z) ? new Vector3(B.x, 0, A.z) : new Vector3(A.x, 0, B.z);
}

export const knight: Choreography = (e) => {
  const { stage, attacker, faction, D } = e;
  const B = e.To;
  const C = lElbow(e.A, B);
  const endTan = flatDir(C, B);
  const land = B.clone().addScaledVector(endTan, -e.strikeRange);
  const approachAt = e.t0;

  // rear
  const rearDur = e.quick ? 0.2 : 0.4;
  stage.tilt(attacker, -0.5, approachAt, rearDur * 0.75, 'power2.out');
  burstAt(e, approachAt + rearDur * 0.5, 'dustPuff', e.A, { count: 6, scale: 0.6 });
  const leapStart = approachAt + rearDur;
  const leapDur = e.quick ? 0.55 : 0.85;
  const landing = leapStart + leapDur;
  const gap = faction === 'rime' ? 0.35 : 0.12;

  const a = e.placeAttack(approachAt, landing + gap);
  stage.arc(attacker, lPath(e.A, C, land, LEAP_PEAK), leapStart, leapDur, 'power1.inOut', {
    faceTangent: 0.4, pitch: (p) => lerp(-0.5, 0.3, smoothstep(p)),
  });
  stage.tilt(attacker, 0, landing, 0.2, 'power2.out');
  stage.at(leapStart, () => e.ctx.bus.emit('attack:whoosh', { role: 'knight', faction }));

  if (faction === 'emberhold') {
    // ember trail from the mane for the whole leap
    let h: { stop(): void } | undefined;
    const stopTrail = () => { try { h?.stop(); } catch { /* ignore */ } h = undefined; };
    stage.at(leapStart, () => {
      const mane = socketObject(attacker, 'socket_head');
      h = e.ctx.fx.trail(mane, faction);
      e.ctx.fx.emit('embers', attacker.root.position.clone(), { follow: mane, duration: leapDur, count: 40, scale: 0.8 });
    });
    stage.at(landing + 0.3, stopTrail);
    stage.onSettle(stopTrail);
  }

  stage.at(landing, () => {
    e.ctx.bus.emit('move:step', { faction, role: 'knight' });
    e.ctx.fx.emit('dustPuff', land.clone(), { count: 10, scale: 0.9 });
    e.ctx.camera.shake(0.2);
  });

  if (faction === 'rime') {
    // the mount headbutts first: short lunge, ice crack, then the glaive finishes
    stage.moveTo(attacker, land.clone().addScaledVector(endTan, 0.18), landing + 0.02, 0.1, 'power2.out');
    stage.moveTo(attacker, land, landing + 0.14, 0.18, 'power2.inOut');
    stage.at(landing + 0.06, () => {
      e.ctx.fx.decal(D.clone(), 'crack');
      e.ctx.fx.emit('iceGlitter', D.clone().setY(0.7), { count: 14, scale: 0.7 });
    });
    shakeAt(e, landing + 0.06, 0.25);
  }

  const r = e.resolve(a.impactAt + 0.35, land, { after: a.end });
  return {
    approachAt, attackAt: a.attackAt, impactAt: a.impactAt, resolveAt: r.resolveAt, walkEnd: r.walkEnd, end: r.end,
    cues: [{ at: 0, shot: e.pickShot('trackingLeap', { attackerAt: land }) }],
    shatter: { magnitude: MAGNITUDE.knight }, trauma: TRAUMA.knight, hitStopMs: HIT_STOP_MS.knight, heavy: false,
  };
};
