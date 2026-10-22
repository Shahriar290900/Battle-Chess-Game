// Occluder fading: bystander pieces that stand between the camera and the fighters (or right next to the
// camera) are faded to ~0.15 through PieceActor.setFade and restored when clear.
import { Vector3 } from 'three';
import type { PieceActor } from '../contracts';
import { ROLE_HEIGHT } from '../contracts';
import { clamp } from './common';

export const OCCLUDER_ALPHA = 0.15;
const RADIUS = 0.46;
const NEAR_CAMERA = 1.2;
const FADE_SECONDS = 0.12;

/** Does the segment C->T pass through the vertical cylinder of piece `a`? Also true when the piece is close to C. */
export function occludes(c: Vector3, t: Vector3, a: PieceActor, nearCamera = NEAR_CAMERA): boolean {
  const p = a.root.position;
  const h = ROLE_HEIGHT[a.role] + 0.05;
  // close to the camera (centre of the piece vs camera)
  const dx0 = p.x - c.x; const dy0 = p.y + h / 2 - c.y; const dz0 = p.z - c.z;
  if (dx0 * dx0 + dy0 * dy0 + dz0 * dz0 < nearCamera * nearCamera) return true;
  const sx = t.x - c.x; const sz = t.z - c.z;
  const len2 = sx * sx + sz * sz;
  if (len2 < 1e-6) return false;
  const u = clamp(((p.x - c.x) * sx + (p.z - c.z) * sz) / len2, 0, 1);
  if (u >= 0.985) return false; // behind / at the target
  const qx = c.x + sx * u; const qz = c.z + sz * u;
  if ((qx - p.x) ** 2 + (qz - p.z) ** 2 > RADIUS * RADIUS) return false;
  const y = c.y + (t.y - c.y) * u;
  return y <= p.y + h;
}

/** Number of `actors` that occlude any of the `targets` seen from `cam` (used to score shots). */
export function countOccluders(cam: Vector3, targets: readonly Vector3[], actors: readonly PieceActor[]): { occluders: number; near: number } {
  let occluders = 0; let near = 0;
  for (const a of actors) {
    const p = a.root.position;
    const d2 = (p.x - cam.x) ** 2 + (p.y + 0.6 - cam.y) ** 2 + (p.z - cam.z) ** 2;
    if (d2 < NEAR_CAMERA * NEAR_CAMERA) { near++; continue; }
    if (targets.some((t) => occludes(cam, t, a, 0))) occluders++;
  }
  return { occluders, near };
}

export class OccluderFader {
  private alpha = new Map<PieceActor, number>();
  private lastT = -1;

  constructor(private readonly actors: () => readonly PieceActor[]) {}

  /** Advance fades. `release` = restore everything (camera handed back). */
  update(t: number, cam: Vector3, targets: readonly Vector3[], release: boolean): void {
    const dt = this.lastT < 0 ? 1 / 30 : Math.max(0, t - this.lastT);
    this.lastT = t;
    const step = (dt / FADE_SECONDS) * (1 - OCCLUDER_ALPHA);
    for (const a of this.actors()) {
      const cur = this.alpha.get(a) ?? 1;
      let want = 1;
      if (!release) for (const tg of targets) if (occludes(cam, tg, a)) { want = OCCLUDER_ALPHA; break; }
      if (cur === want) continue;
      const next = cur < want ? Math.min(want, cur + step) : Math.max(want, cur - step);
      if (next === 1) this.alpha.delete(a); else this.alpha.set(a, next);
      a.setFade(next);
    }
  }

  /** Everything opaque again (settle / skip). */
  restoreAll(): void {
    for (const a of this.alpha.keys()) { try { a.setFade(1); } catch { /* actor may be gone */ } }
    this.alpha.clear();
  }

  /** Currently faded actors (tests/debug). */
  get faded(): PieceActor[] { return [...this.alpha.keys()]; }
}
