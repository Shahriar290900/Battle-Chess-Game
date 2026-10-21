// Small shared helpers for the cinematics module (no engine imports; contracts only).
import { Vector3 } from 'three';
import type { Object3D } from 'three';
import type { PieceActor, SocketName } from '../contracts';
import { ROLE_HEIGHT } from '../contracts';

export const TAU = Math.PI * 2;

export const clamp = (v: number, lo: number, hi: number) => Math.min(hi, Math.max(lo, v));
export const lerp = (a: number, b: number, t: number) => a + (b - a) * t;
export const smoothstep = (t: number) => { const u = clamp(t, 0, 1); return u * u * (3 - 2 * u); };

/** Wrap an angle to (-π, π]. */
export function wrapPi(a: number): number {
  let r = (a + Math.PI) % TAU;
  if (r < 0) r += TAU;
  return r - Math.PI;
}

/** True if two yaw angles are the same direction. */
export const sameYaw = (a: number, b: number, eps = 1e-3) => Math.abs(wrapPi(a - b)) < eps;

/** Horizontal unit vector from a to b (falls back to +z). */
export function flatDir(a: { x: number; z: number }, b: { x: number; z: number }, out = new Vector3()): Vector3 {
  out.set(b.x - a.x, 0, b.z - a.z);
  const l = out.length();
  if (l < 1e-6) return out.set(0, 0, 1);
  return out.multiplyScalar(1 / l);
}

export const flatDist = (a: { x: number; z: number }, b: { x: number; z: number }) => Math.hypot(b.x - a.x, b.z - a.z);

const FALLBACKS: Record<SocketName, SocketName[]> = {
  socket_cast: ['socket_cast', 'socket_weapon_R', 'socket_impact', 'socket_head'],
  socket_weapon_R: ['socket_weapon_R', 'socket_impact', 'socket_head'],
  socket_impact: ['socket_impact', 'socket_head'],
  socket_head: ['socket_head', 'socket_impact'],
};

/** World position of a socket, with graceful fallback when the asset lacks it (placeholder GLBs have no socket_cast). */
export function socketPos(actor: PieceActor, name: SocketName, out = new Vector3()): Vector3 {
  for (const n of FALLBACKS[name]) {
    if (actor.sockets[n]) return actor.socketWorld(n, out);
  }
  actor.root.getWorldPosition(out);
  out.y += ROLE_HEIGHT[actor.role] * 0.6;
  return out;
}

/** The Object3D to follow for a socket (falls back like socketPos, ultimately to the root). */
export function socketObject(actor: PieceActor, name: SocketName): Object3D {
  for (const n of FALLBACKS[name]) {
    const o = actor.sockets[n];
    if (o) return o;
  }
  return actor.root;
}

export const isHeavy = (role: string) => role === 'rook' || role === 'queen' || role === 'king';

/** Chebyshev distance in squares between two algebraic squares. */
export function squareSteps(a: string, b: string): number {
  return Math.max(Math.abs(a.charCodeAt(0) - b.charCodeAt(0)), Math.abs(Number(a[1]) - Number(b[1])));
}

export function withTimeout<T>(p: Promise<T>, ms: number): Promise<T | undefined> {
  return new Promise((resolve) => {
    const id = setTimeout(() => resolve(undefined), ms);
    p.then((v) => { clearTimeout(id); resolve(v); }, () => { clearTimeout(id); resolve(undefined); });
  });
}
