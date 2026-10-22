// Pure look-at solver: splits a desired yaw/pitch (in the actor's local frame) over the available bones with clamps.
import { DEG, HEAD_PITCH_MAX, HEAD_YAW_MAX, MOUNT_PITCH_MAX, MOUNT_YAW_MAX, ROOK_BODY_YAW_MAX, ROOK_TOP_YAW_MAX, SPINE_YAW_MAX } from './tables';

export type LookKind = 'none' | 'humanoid' | 'knight' | 'rook';

export interface LookAngles {
  headYaw: number; headPitch: number; spineYaw: number;
  mountYaw: number; mountPitch: number; bodyYaw: number; topYaw: number;
}
export const newLookAngles = (): LookAngles => ({ headYaw: 0, headPitch: 0, spineYaw: 0, mountYaw: 0, mountPitch: 0, bodyYaw: 0, topYaw: 0 });
const clamp = (v: number, m: number) => (v > m ? m : v < -m ? -m : v);

/**
 * @param yaw   desired turn about local +Y (positive turns +Z toward +X), radians, any value
 * @param pitch desired rotation about local +X (positive = nose down; look UP is negative), radians
 */
export function solveLook(kind: LookKind, hasSpine: boolean, yaw: number, pitch: number, out: LookAngles): LookAngles {
  out.headYaw = out.headPitch = out.spineYaw = out.mountYaw = out.mountPitch = out.bodyYaw = out.topYaw = 0;
  switch (kind) {
    case 'humanoid': {
      out.spineYaw = hasSpine ? clamp(yaw * 0.3, SPINE_YAW_MAX) : 0;
      out.headYaw = clamp(yaw - out.spineYaw, HEAD_YAW_MAX);
      out.headPitch = clamp(pitch, HEAD_PITCH_MAX);
      break;
    }
    case 'knight': {
      out.mountYaw = clamp(yaw * 0.8, MOUNT_YAW_MAX);
      const rest = yaw - out.mountYaw;
      out.spineYaw = hasSpine ? clamp(rest * 0.4, 25 * DEG) : 0;
      out.headYaw = clamp(rest - out.spineYaw, HEAD_YAW_MAX);
      out.mountPitch = clamp(pitch, MOUNT_PITCH_MAX);
      out.headPitch = clamp(pitch * 0.6, HEAD_PITCH_MAX);
      break;
    }
    case 'rook': {
      out.bodyYaw = clamp(yaw * 0.5, ROOK_BODY_YAW_MAX);
      out.topYaw = clamp(yaw - out.bodyYaw, ROOK_TOP_YAW_MAX);
      break;
    }
    default: break;
  }
  return out;
}

/** Knockback falloff: 1 at the origin, 0 at radius, smooth in between. */
export function impulseFalloff(dist: number, radius: number): number {
  if (radius <= 0 || dist >= radius) return 0;
  const t = 1 - Math.max(dist, 0) / radius;
  return t * t;
}
