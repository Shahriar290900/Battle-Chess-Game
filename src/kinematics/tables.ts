// Per-role tuning for the kinematics layer. Angles are radians, gains are "radians of steady-state offset per
// 1 u/s^2 of acceleration", freq in Hz. Values are intentionally subtle: this is secondary motion.
import type { Role } from '../contracts';

export interface SpringCfg { freq: number; zeta: number; gain: number; max: number; }
export interface TopCfg extends SpringCfg {
  /** +1: hangs below its pivot (cape, censer, halo chain) so it swings back on acceleration; -1: stands above it (brazier, crest). */
  sign: 1 | -1;
  /** Twist gain per rad/s^2 of yaw acceleration. */
  twist: number;
}
export interface RoleCfg {
  /** Inverse-mass for knockback: heavier = smaller response. */
  mass: number;
  lean: SpringCfg;
  top: TopCfg;
  head: SpringCfg;
  /** Idle sway amplitude multiplier. */
  idle: number;
}

export const ROLE_CFG: Record<Role, RoleCfg> = {
  pawn:   { mass: 0.6, lean: { freq: 2.6, zeta: 0.32, gain: 0.022, max: 0.14 }, top: { freq: 3.2, zeta: 0.2, gain: 0.06, max: 0.5, sign: 1, twist: 0.012 }, head: { freq: 4.5, zeta: 0.35, gain: 0.02, max: 0.2 }, idle: 1.2 },
  bishop: { mass: 0.9, lean: { freq: 2.3, zeta: 0.32, gain: 0.016, max: 0.1 }, top: { freq: 2.0, zeta: 0.12, gain: 0.08, max: 0.6, sign: 1, twist: 0.02 }, head: { freq: 4, zeta: 0.35, gain: 0.018, max: 0.18 }, idle: 1.0 },
  knight: { mass: 1.3, lean: { freq: 2.0, zeta: 0.34, gain: 0.012, max: 0.08 }, top: { freq: 3.0, zeta: 0.2, gain: 0.05, max: 0.45, sign: 1, twist: 0.012 }, head: { freq: 4, zeta: 0.35, gain: 0.015, max: 0.15 }, idle: 1.0 },
  queen:  { mass: 1.3, lean: { freq: 2.2, zeta: 0.32, gain: 0.014, max: 0.09 }, top: { freq: 2.4, zeta: 0.15, gain: 0.07, max: 0.55, sign: 1, twist: 0.015 }, head: { freq: 3.8, zeta: 0.35, gain: 0.016, max: 0.16 }, idle: 0.9 },
  king:   { mass: 2.0, lean: { freq: 1.9, zeta: 0.36, gain: 0.009, max: 0.06 }, top: { freq: 2.2, zeta: 0.18, gain: 0.05, max: 0.4, sign: 1, twist: 0.01 }, head: { freq: 3.5, zeta: 0.4, gain: 0.012, max: 0.12 }, idle: 0.8 },
  rook:   { mass: 2.4, lean: { freq: 1.6, zeta: 0.4, gain: 0.005, max: 0.035 }, top: { freq: 1.8, zeta: 0.22, gain: 0.04, max: 0.25, sign: -1, twist: 0.006 }, head: { freq: 3, zeta: 0.4, gain: 0.0, max: 0.05 }, idle: 0.6 },
};

/** Look-at limits (radians). */
export const DEG = Math.PI / 180;
export const HEAD_YAW_MAX = 70 * DEG;
export const HEAD_PITCH_MAX = 30 * DEG;
export const SPINE_YAW_MAX = 35 * DEG;
export const MOUNT_YAW_MAX = 50 * DEG;
export const MOUNT_PITCH_MAX = 20 * DEG;
export const ROOK_BODY_YAW_MAX = 25 * DEG;
export const ROOK_TOP_YAW_MAX = 40 * DEG;
