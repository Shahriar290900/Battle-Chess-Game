import { Vector3 } from 'three';
import type { EmitOptions, ParticlePreset, SocketName } from '../../contracts';
import { socketObject, socketPos } from '../common';
import type { CaptureEnv } from './types';

/** Ribbon trail on a socket between two master times; always stopped on settle. */
export function trailBetween(env: CaptureEnv, startAt: number, stopAt: number, socket: SocketName = 'socket_weapon_R'): void {
  let h: { stop(): void } | undefined;
  const stop = () => { try { h?.stop(); } catch { /* ignore */ } h = undefined; };
  env.stage.at(startAt, () => { h = env.ctx.fx.trail(socketObject(env.attacker, socket), env.faction); });
  env.stage.at(stopAt, stop);
  env.stage.onSettle(stop);
}

/** Emit a preset at a live socket position when the callback fires. */
export function burstAtSocket(env: CaptureEnv, at: number, preset: ParticlePreset, socket: SocketName, opts?: EmitOptions): void {
  env.stage.at(at, () => env.stage.emit(preset, socketPos(env.attacker, socket, new Vector3()), opts));
}

/** Emit a preset at a fixed world point (lifted by `y`). */
export function burstAt(env: CaptureEnv, at: number, preset: ParticlePreset, pos: Vector3, opts?: EmitOptions, y = 0.1): void {
  env.stage.at(at, () => env.stage.emit(preset, new Vector3(pos.x, pos.y + y, pos.z), opts));
}

/** Footfall-style camera nudge. */
export function shakeAt(env: CaptureEnv, at: number, trauma: number): void {
  env.stage.at(at, () => env.ctx.camera.shake(trauma));
}

/** Wind-up rock-back then a forward snap into the blow (anticipation), reset afterwards. */
export function windUp(env: CaptureEnv, attackAt: number, impactAt: number, back = -0.16, snap = 0.2): void {
  const lead = Math.max(0.25, (impactAt - attackAt) * 0.45);
  const startBack = Math.max(attackAt, impactAt - lead - 0.2);
  env.stage.tilt(env.attacker, back, startBack, lead, 'power2.out');
  env.stage.tilt(env.attacker, snap, impactAt - 0.12, 0.12, 'power3.in');
  env.stage.tilt(env.attacker, 0, impactAt + 0.05, 0.4, 'power2.out');
}
