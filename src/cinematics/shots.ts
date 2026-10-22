// Camera shot library (choreography §6). Every shot is `pose(t) -> { position, lookAt, fov }` where t is
// shot-local seconds. Poses are clamped above the board (y >= 0.6) and pushed out of piece volumes.
import { Vector3 } from 'three';
import type { PieceActor } from '../contracts';
import { ROLE_HEIGHT } from '../contracts';
import { clamp, flatDir, lerp, smoothstep, TAU } from './common';

export const MIN_CAMERA_Y = 0.6;

export interface ShotPose { position: Vector3; lookAt: Vector3; fov: number }

export type ShotName = 'lowSide' | 'overShoulder' | 'topDownSlam' | 'trackingLeap' | 'heroOrbit' | 'lowHero' | 'orbit360';

export interface ShotInputs {
  /** Live world position of the attacker root. */
  attacker: () => Vector3;
  /** Live world position of the defender root. */
  defender: () => Vector3;
  /** +1 if the camera seat is on the +z side of the board (White), -1 otherwise. */
  seatZ: 1 | -1;
  /** Viewport aspect ratio; used to keep both pieces in frame on portrait phones. */
  aspect?: () => number;
  /** Candidate angle: 0 seat side, 1 opposite side, 2 seat side farther and higher (shot scoring picks one). */
  variant?: 0 | 1 | 2;
}

const variantOf = (i: ShotInputs) => {
  const v = i.variant ?? 0;
  return { flip: v === 1, far: v === 2 ? 1.25 : 1, up: v === 2 ? 0.8 : 0 };
};

export interface Shot {
  readonly name: ShotName;
  pose(t: number, out?: ShotPose): ShotPose;
}

export const newPose = (): ShotPose => ({ position: new Vector3(), lookAt: new Vector3(), fov: 40 });

const aspectOf = (i: ShotInputs) => Math.max(0.4, i.aspect?.() ?? 16 / 9);

/** Distance at which a box of half extents (halfW, halfH) fits the frame for a vertical `fov` and aspect. */
export function frameDistance(halfW: number, halfH: number, fovDeg: number, aspect: number): number {
  const tanHalf = Math.tan((fovDeg * Math.PI) / 360);
  return Math.max(halfH / tanHalf, halfW / (tanHalf * aspect));
}

/** Unit horizontal vector perpendicular to `d`, pointing to the camera seat side. */
export function perpToSeat(d: Vector3, seatZ: number, out = new Vector3(), flip = false): Vector3 {
  out.set(-d.z, 0, d.x);
  const side = out.z * seatZ;
  if (Math.abs(out.z) < 1e-4 ? out.x < 0 : side < 0) out.negate();
  return flip ? out.negate() : out;
}

function rotY(v: Vector3, a: number, out: Vector3): Vector3 {
  const c = Math.cos(a); const s = Math.sin(a);
  return out.set(v.x * c + v.z * s, 0, -v.x * s + v.z * c);
}

/** Perpendicular to the strike line, height 0.9, distance 3, FOV 35. */
export function lowSide(i: ShotInputs): Shot {
  const A = new Vector3(); const D = new Vector3(); const d = new Vector3(); const s = new Vector3(); const mid = new Vector3();
  return {
    name: 'lowSide',
    pose(_t, out = newPose()) {
      A.copy(i.attacker()); D.copy(i.defender());
      const vr = variantOf(i);
      flatDir(A, D, d); perpToSeat(d, i.seatZ, s, vr.flip);
      mid.copy(A).lerp(D, 0.5);
      const sep = Math.hypot(D.x - A.x, D.z - A.z);
      const fov = 35;
      const dist = Math.max(3.6, frameDistance(sep / 2 + 1.0, 1.3, fov, aspectOf(i))) * vr.far;
      out.position.copy(mid).addScaledVector(s, dist); out.position.y = 0.9 + Math.max(0, sep - 2) * 0.12 + vr.up;
      out.lookAt.set(mid.x, 0.75, mid.z);
      out.fov = fov;
      return out;
    },
  };
}

/** Behind the attacker, offset 0.6 to the side, height 1.4, FOV 40. */
export function overShoulder(i: ShotInputs): Shot {
  const A = new Vector3(); const D = new Vector3(); const d = new Vector3(); const s = new Vector3();
  return {
    name: 'overShoulder',
    pose(_t, out = newPose()) {
      A.copy(i.attacker()); D.copy(i.defender());
      const vr = variantOf(i);
      flatDir(A, D, d); perpToSeat(d, i.seatZ, s, vr.flip);
      const sep = Math.hypot(D.x - A.x, D.z - A.z);
      const back = Math.max(2.6, frameDistance(sep / 2 * 0.35 + 0.8, 1.0, 42, aspectOf(i)) * 0.7) * vr.far;
      out.position.copy(A).addScaledVector(d, -back).addScaledVector(s, 0.7 * vr.far); out.position.y = 1.7 + vr.up;
      out.lookAt.copy(A).lerp(D, 0.6); out.lookAt.y = 0.8;
      out.fov = 42;
      return out;
    },
  };
}

/** High above the target, slight tilt toward the seat, FOV 45. */
export function topDownSlam(i: ShotInputs): Shot {
  const A = new Vector3(); const D = new Vector3(); const centre = new Vector3();
  return {
    name: 'topDownSlam',
    pose(_t, out = newPose()) {
      A.copy(i.attacker()); D.copy(i.defender());
      const bias = clamp(Math.hypot(A.x - D.x, A.z - D.z), 0, 6) / 6;
      centre.copy(D).lerp(A, 0.18 + bias * 0.12);
      const fov = 45;
      const sep = Math.hypot(D.x - A.x, D.z - A.z);
      const h = clamp(frameDistance(Math.max(2.4, sep * 0.4), 2.2, fov, aspectOf(i)), 5.2, 9);
      const vr = variantOf(i);
      out.position.set(centre.x, h + vr.up, centre.z + i.seatZ * 1.5 * (vr.flip ? -1 : 1) * vr.far);
      out.lookAt.set(centre.x, 0, centre.z);
      out.fov = fov;
      return out;
    },
  };
}

/** Follows the knight's arc from the side with a ~0.1 s lag. */
export function trackingLeap(i: ShotInputs): Shot {
  const A0 = new Vector3(); const D = new Vector3(); const L = new Vector3(); const A = new Vector3();
  const d = new Vector3(); const s = new Vector3();
  let lastT = -1; let primed = false;
  return {
    name: 'trackingLeap',
    pose(t, out = newPose()) {
      A.copy(i.attacker()); D.copy(i.defender());
      if (!primed || t <= lastT) { A0.copy(A); L.copy(A); primed = true; if (t <= lastT) lastT = -1; }
      const dt = lastT < 0 ? 1 / 60 : Math.max(0, t - lastT);
      lastT = t;
      L.lerp(A, 1 - Math.exp(-dt / 0.1));
      const vr = variantOf(i);
      flatDir(A0, D, d); perpToSeat(d, i.seatZ, s, vr.flip);
      const dist = Math.max(4, frameDistance(2.1, 1.3, 40, aspectOf(i))) * vr.far;
      out.position.copy(L).addScaledVector(s, dist); out.position.y = 1.5 + L.y * 0.5 + vr.up;
      out.lookAt.copy(L).lerp(D, 0.3); out.lookAt.y = 0.7 + L.y * 0.45;
      out.fov = 40;
      return out;
    },
  };
}

export interface HeroOrbitOptions { /** Seconds for the 120 degree swing. */ duration?: number }

/** Starts behind the attacker, orbits 120 degrees to a 3/4 front view. */
export function heroOrbit(i: ShotInputs, opts: HeroOrbitOptions = {}): Shot {
  const T = opts.duration ?? 1.8;
  const A = new Vector3(); const D = new Vector3(); const d = new Vector3(); const c = new Vector3(); const dc = new Vector3();
  const probe = new Vector3();
  return {
    name: 'heroOrbit',
    pose(t, out = newPose()) {
      A.copy(i.attacker()); D.copy(i.defender());
      flatDir(A, D, d);
      // swing toward the seat side so the end view faces the audience
      const vr = variantOf(i);
      const end = Math.PI / 3;
      const sign = (rotY(d, end, probe).z * i.seatZ >= rotY(d, -end, dc).z * i.seatZ ? 1 : -1) * (vr.flip ? -1 : 1);
      const u = smoothstep(t / T);
      const phi = lerp(Math.PI, end, u);
      rotY(d, sign * phi, dc);
      const follow = smoothstep(t / (T * 1.4));
      c.copy(A).lerp(probe.copy(A).lerp(D, 0.5), follow);
      const sep = Math.hypot(D.x - A.x, D.z - A.z);
      const R = Math.max(3.9, frameDistance(sep * 0.25 + 1.1, 1.3, 42, aspectOf(i))) * vr.far;
      out.position.copy(c).addScaledVector(dc, R); out.position.y = lerp(1.6, 1.25, u) + vr.up;
      out.lookAt.copy(c).lerp(D, 0.3 * follow); out.lookAt.y = 1.0;
      out.fov = 42;
      return out;
    },
  };
}

/** Low and close (just above the pawn line), wide FOV 55, looking up at the attacker. */
export function lowHero(i: ShotInputs): Shot {
  const A = new Vector3(); const D = new Vector3(); const d = new Vector3(); const s = new Vector3();
  return {
    name: 'lowHero',
    pose(_t, out = newPose()) {
      A.copy(i.attacker()); D.copy(i.defender());
      const vr = variantOf(i);
      flatDir(A, D, d); perpToSeat(d, i.seatZ, s, vr.flip);
      const fov = 52;
      const sep = Math.hypot(D.x - A.x, D.z - A.z);
      const dist = Math.max(3.1, frameDistance(sep / 2 + 0.9, 1.4, fov, aspectOf(i)) * 0.85) * vr.far;
      out.position.copy(A).addScaledVector(s, dist).addScaledVector(d, 0.3); out.position.y = 1.35 + vr.up;
      out.lookAt.copy(A).lerp(D, 0.45); out.lookAt.y = 0.9;
      out.fov = fov;
      return out;
    },
  };
}

/** Slow full circle around a point (checkmate). */
export function orbit360(centre: () => Vector3, seconds: number, startAngle = 0, radius = 3.4): Shot {
  const c = new Vector3();
  return {
    name: 'orbit360',
    pose(t, out = newPose()) {
      c.copy(centre());
      const a = startAngle + (t / seconds) * TAU;
      out.position.set(c.x + Math.sin(a) * radius, lerp(1.7, 1.15, smoothstep(t / seconds)), c.z + Math.cos(a) * radius);
      out.lookAt.set(c.x, 0.85, c.z);
      out.fov = 40;
      return out;
    },
  };
}

/** Camera must look down enough that the top frame edge stays on the lit board, not the dark hall. */
const PITCH_FRACTION = 1.3;
const MAX_CAMERA_Y = 6;
/** Keep clear of piece volumes by this horizontal radius. */
const CLEARANCE = 0.8;

/** Clamp above the board, tilt down toward the board, and push the camera out of piece volumes. */
export function constrainPose(pose: ShotPose, actors: readonly PieceActor[]): ShotPose {
  const p = pose.position;
  const dh = Math.hypot(p.x - pose.lookAt.x, p.z - pose.lookAt.z);
  const minY = pose.lookAt.y + dh * Math.tan((pose.fov * Math.PI / 180) / 2 * PITCH_FRACTION);
  if (p.y < minY) p.y = Math.min(minY, MAX_CAMERA_Y);
  for (let pass = 0; pass < 2; pass++) {
    for (const a of actors) {
      const ap = a.root.position;
      const h = ROLE_HEIGHT[a.role] + 0.45;
      if (p.y > h) continue;
      const dx = p.x - ap.x; const dz = p.z - ap.z;
      const d2 = dx * dx + dz * dz;
      if (d2 >= CLEARANCE * CLEARANCE) continue;
      const d = Math.sqrt(d2);
      if (d < 1e-4) {
        const lx = p.x - pose.lookAt.x; const lz = p.z - pose.lookAt.z;
        const l = Math.hypot(lx, lz) || 1;
        p.x = ap.x + (lx / l) * CLEARANCE; p.z = ap.z + (lz / l) * CLEARANCE;
      } else {
        p.x = ap.x + (dx / d) * CLEARANCE; p.z = ap.z + (dz / d) * CLEARANCE;
      }
    }
  }
  if (p.y < MIN_CAMERA_Y) p.y = MIN_CAMERA_Y;
  if (!Number.isFinite(p.x + p.y + p.z)) p.set(0, 6, 8);
  return pose;
}

/** One shot active from `at` (master timeline seconds). `blend` seconds cross-fade from the previous pose; 0 = hard cut. */
export interface ShotCue { at: number; shot: Shot; blend?: number }

/** Resolve the shot name used by each attacker role (choreography §3). */
export const SHOT_FOR_ROLE = { pawn: 'lowSide', rook: 'topDownSlam', knight: 'trackingLeap', bishop: 'overShoulder', queen: 'heroOrbit', king: 'lowHero' } as const;
