// Additive layering on top of mixer-driven bones. The AnimationMixer only rewrites a channel when the clip value
// changed, so a bone we offset last frame either still holds our offset (channel static) or holds a fresh clip value
// (channel animated). We remember what we wrote: if the bone still equals it, the clean clip pose is `base`;
// otherwise the mixer overwrote it and the current value IS the base. Either way we never accumulate drift.
import { Euler, Quaternion, Vector3, type Object3D } from 'three';

const _e = new Euler();
const _q = new Quaternion();
const TINY = 1e-6;
type RawQuat = { _x: number; _y: number; _z: number; _w: number };
/** Set components without firing Quaternion's onChange (which would recompute bone.rotation every write).
 *  Rendering reads bone.quaternion only; bone.rotation (Euler) is intentionally left stale while an offset is active. */
function rawSet(q: Quaternion, s: Quaternion): void {
  const r = q as unknown as RawQuat;
  r._x = s.x; r._y = s.y; r._z = s.z; r._w = s.w;
}

export class TrackedRot {
  readonly base = new Quaternion();
  private readonly written = new Quaternion();
  private has = false;
  constructor(readonly bone: Object3D) {}

  private sync(): void {
    const q = this.bone.quaternion, w = this.written;
    if (!(this.has && q.x === w.x && q.y === w.y && q.z === w.z && q.w === w.w)) this.base.copy(q);
  }

  /** Pose = offset(rx, ry, rz) * clipPose (offset expressed in the parent bone's frame). */
  write(rx: number, ry: number, rz: number): void {
    this.sync();
    if (Math.abs(rx) + Math.abs(ry) + Math.abs(rz) < TINY) {
      if (this.has) { this.bone.quaternion.copy(this.base); this.has = false; }
      return;
    }
    _e.set(rx, ry, rz, 'YXZ');
    _q.setFromEuler(_e).multiply(this.base);
    rawSet(this.bone.quaternion, _q);
    this.written.copy(_q);
    this.has = true;
  }

  restore(): void {
    if (!this.has) return;
    const q = this.bone.quaternion, w = this.written;
    if (q.x === w.x && q.y === w.y && q.z === w.z && q.w === w.w) q.copy(this.base);
    this.has = false;
  }
}

/** Position (additive) or scale (multiplicative) channel of a bone. */
export class TrackedVec {
  readonly base = new Vector3();
  private readonly written = new Vector3();
  private has = false;
  constructor(readonly vec: Vector3, private readonly mul: boolean) {}

  private sync(): void {
    const v = this.vec, w = this.written;
    if (!(this.has && v.x === w.x && v.y === w.y && v.z === w.z)) this.base.copy(v);
  }

  write(x: number, y: number, z: number): void {
    this.sync();
    const b = this.base;
    const neutral = this.mul ? 1 : 0;
    if (Math.abs(x - neutral) + Math.abs(y - neutral) + Math.abs(z - neutral) < TINY) {
      if (this.has) { this.vec.copy(b); this.has = false; }
      return;
    }
    if (this.mul) this.vec.set(b.x * x, b.y * y, b.z * z); else this.vec.set(b.x + x, b.y + y, b.z + z);
    this.written.copy(this.vec);
    this.has = true;
  }

  restore(): void {
    if (!this.has) return;
    const v = this.vec, w = this.written;
    if (v.x === w.x && v.y === w.y && v.z === w.z) v.copy(this.base);
    this.has = false;
  }
}
