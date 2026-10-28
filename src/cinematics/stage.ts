// Stage = one running sequence: a master GSAP timeline plus the bookkeeping that guarantees the board
// ends in its final state whether the timeline completes, is skipped, or a watchdog fires.
import { gsap } from 'gsap';
import { Vector3 } from 'three';
import type { Object3D } from 'three';
import type {
  ClipName, EmitOptions, GameEvents, ParticlePreset, PieceActor, SequenceContext, Timeline,
} from '../contracts';
import { clamp, wrapPi, withTimeout } from './common';
import { TimeWarp } from './timeWarp';

export type FinishReason = 'complete' | 'skip' | 'watchdog';
export type SettleFn = (reason: FinishReason) => void;

export interface WalkOpts {
  speed?: number; minDur?: number; maxDur?: number; ease?: string;
  /** Seconds between footfalls (default derived from speed). */
  stepEvery?: number;
  /** Scrub the Move clip while travelling (default true). */
  gait?: boolean;
  /** Return to Idle when done (default true). */
  idle?: boolean;
  /** Emit a dust puff at each footfall. */
  dust?: boolean;
  /** Camera shake trauma per footfall (heavy walkers). */
  thud?: number;
  /** Suppress the grinding-slide audio events for this walk (default: emit move:slide start/stop). */
  slide?: boolean;
}

/** Max real time a sequence may take beyond its nominal length before the watchdog finishes it. */
const WATCHDOG_EXTRA_MS = 8000;
/** Max real time to wait for fx/camera promises after the timeline ends. */
export const TAIL_GUARD_MS = 2500;

export class Stage {
  readonly tl: Timeline;
  readonly warp = new TimeWarp();
  finished = false;
  /** Why the stage finished (null while running). */
  reason: FinishReason | null = null;
  readonly done: Promise<void>;
  private resolveDone!: () => void;
  private readonly settles: SettleFn[] = [];
  private readonly waits: Promise<unknown>[] = [];
  private watchdog: ReturnType<typeof setInterval> | null = null;
  private readonly killTargets = new Set<object>();
  private readonly tmpV = new Vector3();

  constructor(readonly ctx: SequenceContext, readonly label: string) {
    this.tl = gsap.timeline({ paused: true, onComplete: () => { void this.complete(); } });
    this.done = new Promise<void>((r) => { this.resolveDone = r; });
    // kinematics look-at targets are always released first when the stage settles
    this.onSettle(() => { for (const a of this.looked) { try { this.ctx.kinematics?.lookAt(a, null); } catch { /* ignore */ } } this.looked.clear(); });
    // a slide loop must never outlive the stage (skip / watchdog / quick all end here)
    this.onSettle(() => this.stopSlides());
  }

  // ------------------------------------------------------------ audio: piece slides (contract v1.4 move:slide)

  /** actor -> number of overlapping slide segments currently open (start is sent on 0 -> 1, stop on 1 -> 0). */
  private readonly slides = new Map<PieceActor, number>();

  /**
   * Announce a ground slide of `actor` between master times `at` and `at + dur` as move:slide start / stop.
   * `dist` is in board units (= squares) or a function evaluated when the slide starts (live position).
   * speed = squares per real second (timeline time scale included). Stops are balanced and forced on settle.
   */
  slide(actor: PieceActor, at: number, dur: number, dist: number | (() => number)): void {
    if (dur <= 0) return;
    this.at(at, () => {
      const d = typeof dist === 'function' ? dist() : dist;
      if (d < 0.05) return;
      const speed = (d / dur) * Math.max(0.1, this.tl.timeScale());
      const n = this.slides.get(actor) ?? 0;
      this.slides.set(actor, n + 1);
      this.ctx.bus.emit('move:slide', { faction: actor.faction, role: actor.role, phase: 'start', speed });
    });
    this.at(at + dur, () => this.slideStop(actor));
  }

  private slideStop(actor: PieceActor, force = false): void {
    const n = this.slides.get(actor) ?? 0;
    if (n <= 0) return;
    if (!force && n > 1) { this.slides.set(actor, n - 1); return; }
    this.slides.delete(actor);
    try { this.ctx.bus.emit('move:slide', { faction: actor.faction, role: actor.role, phase: 'stop', speed: 0 }); } catch { /* ignore */ }
  }

  private stopSlides(): void {
    for (const a of [...this.slides.keys()]) this.slideStop(a, true);
  }

  /** moveTo that also announces a ground slide (short shoves, sidesteps, the off-mode lunge). */
  glide(actor: PieceActor, to: { x: number; z: number }, at: number, dur: number, ease = 'power2.inOut'): number {
    const end = this.moveTo(actor, to, at, dur, ease);
    this.slide(actor, at, dur, () => Math.hypot(to.x - actor.root.position.x, to.z - actor.root.position.z));
    return end;
  }

  // ------------------------------------------------------------ kinematics hooks (optional layer)

  private readonly looked = new Set<PieceActor>();

  get hasKinematics(): boolean { return !!this.ctx.kinematics; }

  /** Head/spine turn toward a world point (released automatically on settle). */
  look(actor: PieceActor, target: Vector3, weight = 1): void {
    const k = this.ctx.kinematics;
    if (!k) return;
    this.looked.add(actor);
    this.safe(() => k.lookAt(actor, target.clone(), weight));
  }

  unlook(actor: PieceActor): void {
    if (!this.looked.delete(actor)) return;
    this.safe(() => this.ctx.kinematics?.lookAt(actor, null));
  }

  /** Radial shove for impacts, slams and landings. */
  impulse(origin: Vector3, strength: number, radius = 3): void {
    const k = this.ctx.kinematics;
    if (k) this.safe(() => k.impulse(origin.clone(), strength, radius));
  }

  // ------------------------------------------------------------ lifecycle

  /** Register a state-fixing function to run (in order) when the stage finishes for any reason. */
  onSettle(fn: SettleFn): void { this.settles.push(fn); }

  /** Make `finish` wait (bounded) for a promise, e.g. camera.restore or an fx call. */
  track(p: Promise<unknown> | undefined | void): void {
    if (p && typeof (p as Promise<unknown>).then === 'function') this.waits.push((p as Promise<unknown>).catch(() => undefined));
  }

  killOn(target: object): void { this.killTargets.add(target); }

  /** Start playback. `speed` multiplies the timeline time scale (animSpeed * mode scale). */
  start(speed: number): void {
    this.tl.timeScale(speed);
    const real = (this.tl.totalDuration() / Math.max(0.05, speed)) * 1000;
    // Watchdog: counts only un-paused real time (a deliberately paused global timeline is not a hang).
    const limit = real + WATCHDOG_EXTRA_MS;
    let used = 0;
    this.watchdog = setInterval(() => {
      if (this.finished) return;
      if (!gsap.globalTimeline.paused()) used += 500;
      if (used >= limit) this.finish('watchdog');
    }, 500);
    if (this.tl.totalDuration() <= 0) { void this.complete(); return; }
    this.tl.play(0);
  }

  private async complete(): Promise<void> {
    if (this.finished) return;
    if (this.waits.length) await withTimeout(Promise.allSettled(this.waits), TAIL_GUARD_MS);
    this.finish('complete');
  }

  skip(): void { this.finish('skip'); }

  finish(reason: FinishReason): void {
    if (this.finished) return;
    this.finished = true;
    this.reason = reason;
    if (this.watchdog) { clearInterval(this.watchdog); this.watchdog = null; }
    try { this.tl.kill(); } catch { /* ignore */ }
    for (const t of this.killTargets) gsap.killTweensOf(t);
    this.warp.stop();
    for (const fn of this.settles) {
      try { fn(reason); } catch (err) { console.warn(`[cinematics] settle failed in ${this.label}`, err); }
    }
    gsap.globalTimeline.timeScale(1);
    this.resolveDone();
  }

  // ------------------------------------------------------------ safe calls

  /** Run an fx/bus/camera call without letting a throw or a rejected promise break the sequence. */
  safe(fn: () => unknown): void {
    try {
      const r = fn();
      if (r && typeof (r as Promise<unknown>).then === 'function') (r as Promise<unknown>).catch((e) => console.warn(`[cinematics] ${this.label} async fx failed`, e));
    } catch (err) {
      console.warn(`[cinematics] ${this.label} fx failed`, err);
    }
  }

  /** Schedule a callback at master time `at` (skipped once finished). */
  at(at: number, fn: () => void): void {
    this.tl.call(() => { if (!this.finished) this.safe(fn); }, undefined, at);
  }

  bus<K extends keyof GameEvents>(name: K, payload: GameEvents[K]): void {
    this.safe(() => this.ctx.bus.emit(name, payload));
  }

  emit(preset: ParticlePreset, pos: Vector3, opts?: EmitOptions): void {
    this.safe(() => this.ctx.fx.emit(preset, pos.clone(), opts));
  }

  // ------------------------------------------------------------ tween helpers (all return the end time)

  /** Generic 0..1 proxy tween. */
  proxy(at: number, dur: number, ease: string, fn: (p: number) => void): number {
    const o = { p: 0 };
    this.tl.to(o, { p: 1, duration: Math.max(1e-4, dur), ease, onUpdate: () => fn(o.p) }, at);
    return at + dur;
  }

  /** Turn to an absolute yaw by the shortest arc. */
  yaw(actor: PieceActor, target: number, at: number, dur = 0.25, ease = 'power2.inOut'): number {
    let from = 0; let delta = 0;
    const o = { p: 0 };
    this.killOn(o);
    this.tl.to(o, {
      p: 1, duration: Math.max(1e-4, dur), ease,
      onStart: () => { from = actor.getYaw(); delta = wrapPi(target - from); },
      onUpdate: () => actor.setYaw(from + delta * o.p),
    }, at);
    return at + dur;
  }

  /** Slide the root to (x, z) (y untouched). */
  moveTo(actor: PieceActor, to: { x: number; z: number }, at: number, dur: number, ease = 'power2.inOut'): number {
    this.killOn(actor.root.position);
    this.tl.to(actor.root.position, { x: to.x, z: to.z, duration: Math.max(1e-4, dur), ease }, at);
    return at + dur;
  }

  /** Tween the root's y. */
  lift(actor: PieceActor, y: number, at: number, dur: number, ease = 'power2.out'): number {
    this.killOn(actor.root.position);
    this.tl.to(actor.root.position, { y, duration: Math.max(1e-4, dur), ease }, at);
    return at + dur;
  }

  /** Instantly place the root at (x, z) at master time `at`. */
  place(actor: PieceActor, to: { x: number; z: number }, at: number): void {
    this.tl.set(actor.root.position, { x: to.x, z: to.z }, at);
  }

  /** Walk (Move clip scrubbed in step with the translation) at `speed` units/s; durations are clamped. */
  walk(actor: PieceActor, from: { x: number; z: number }, to: { x: number; z: number }, at: number, o: WalkOpts = {}): number {
    const speed = o.speed ?? 2.2;
    const dist = Math.hypot(to.x - from.x, to.z - from.z);
    if (dist < 0.01) return at;
    const dur = clamp(dist / speed, o.minDur ?? 0.25, o.maxDur ?? 1.8);
    this.moveTo(actor, to, at, dur, o.ease ?? 'power1.inOut');
    if (o.slide !== false) this.slide(actor, at, dur, dist);
    if (o.gait !== false && actor.hasClip('Move')) {
      const md = Math.max(0.2, actor.clipDuration('Move'));
      const g = { t: 0 };
      this.killOn(g);
      this.tl.to(g, { t: dur, duration: dur, ease: 'none', onUpdate: () => actor.scrub('Move', g.t % md) }, at);
    }
    const every = o.stepEvery ?? Math.max(0.22, 0.7 / speed);
    const n = Math.max(1, Math.floor(dur / every));
    for (let i = 0; i < n; i++) {
      const ts = at + (i + 0.5) * (dur / n);
      this.at(ts, () => {
        this.ctx.bus.emit('move:step', { faction: actor.faction, role: actor.role });
        if (o.dust) { actor.root.getWorldPosition(this.tmpV); this.ctx.fx.emit('dustPuff', this.tmpV.clone(), { count: 4, scale: 0.6 }); }
        if (o.thud) this.ctx.camera.shake(o.thud);
      });
    }
    if (o.idle !== false) this.at(at + dur, () => actor.play('Idle', { fade: 0.15 }));
    return at + dur;
  }

  /** One parabolic hop between two points; footfall + land events and a puff on landing. */
  hop(actor: PieceActor, from: { x: number; z: number }, to: { x: number; z: number }, at: number, dur: number, height: number,
    o: { puff?: ParticlePreset; step?: boolean; onLand?: () => void; landStrength?: number } = {}): number {
    const g = { p: 0 };
    this.killOn(g);
    this.tl.to(g, {
      p: 1, duration: Math.max(1e-4, dur), ease: 'none',
      onUpdate: () => {
        actor.root.position.x = from.x + (to.x - from.x) * g.p;
        actor.root.position.z = from.z + (to.z - from.z) * g.p;
        actor.root.position.y = 4 * height * g.p * (1 - g.p);
      },
    }, at);
    this.at(at + dur, () => {
      actor.root.position.y = 0;
      if (o.step !== false) {
        this.ctx.bus.emit('move:step', { faction: actor.faction, role: actor.role });
        this.ctx.bus.emit('land', { faction: actor.faction, role: actor.role, strength: o.landStrength ?? 0.4 });
      }
      if (o.puff) this.ctx.fx.emit(o.puff, new Vector3(to.x, 0.05, to.z), { count: 8, scale: 0.7 });
      o.onLand?.();
    });
    return at + dur;
  }

  /**
   * Move the root along `path(p)` (world position, p 0..1). `faceTangent` (0..1) smoothly turns the yaw
   * to the direction of travel; `pitch(p)` tilts the model about its local X (rearing, leaping).
   */
  arc(actor: PieceActor, path: (p: number, out: Vector3) => void, at: number, dur: number, ease: string,
    o: { faceTangent?: number; pitch?: (p: number) => number; faceTarget?: { x: number; z: number } } = {}): number {
    const g = { p: 0 };
    const cur = new Vector3(); const p0 = new Vector3(); const p1 = new Vector3();
    this.killOn(g); this.killOn(actor.root.position);
    if (o.pitch) this.touchModel(actor);
    this.tl.to(g, {
      p: 1, duration: Math.max(1e-4, dur), ease,
      onUpdate: () => {
        path(g.p, cur);
        actor.root.position.copy(cur);
        if (o.faceTangent !== undefined) {
          path(Math.max(0, g.p - 0.03), p0); path(Math.min(1, g.p + 0.03), p1);
          const dx = p1.x - p0.x; const dz = p1.z - p0.z;
          if (Math.hypot(dx, dz) > 1e-4) {
            const y = Math.atan2(dx, dz);
            actor.setYaw(actor.getYaw() + wrapPi(y - actor.getYaw()) * o.faceTangent);
          }
        } else if (o.faceTarget) {
          actor.setYaw(Math.atan2(o.faceTarget.x - cur.x, o.faceTarget.z - cur.z));
        }
        if (o.pitch) actor.model.rotation.x = o.pitch(g.p);
      },
    }, at);
    return at + dur;
  }

  /** Tilt the model about its local X (positive = front down). Reset automatically when the stage settles. */
  tilt(actor: PieceActor, rx: number, at: number, dur: number, ease = 'power2.out'): number {
    this.touchModel(actor);
    this.tl.to(actor.model.rotation, { x: rx, duration: Math.max(1e-4, dur), ease }, at);
    return at + dur;
  }

  private touched = new Map<Object3D, number>();
  touchModel(actor: PieceActor): void {
    if (this.touched.has(actor.model)) return;
    this.touched.set(actor.model, actor.model.rotation.x);
    this.killOn(actor.model.rotation);
    this.onSettle(() => { actor.model.rotation.x = this.touched.get(actor.model) ?? 0; });
  }

  /** Nest a once-clip (Victory, HitReact) at `at`; durations above `maxDur` are sped up to fit. Returns the end time. */
  clip(actor: PieceActor, clip: ClipName, at: number, maxDur?: number): number {
    if (!actor.hasClip(clip)) return at;
    const c = actor.clipTimeline(clip);
    const d = c.duration();
    if (maxDur && d > maxDur) c.timeScale(d / maxDur);
    this.tl.add(c, at);
    return at + (maxDur ? Math.min(d, maxDur) : d);
  }

  /** Scrub `clip` from 0 to `frac` of its length over `dur` seconds, then hold it there. */
  poseClip(actor: PieceActor, clip: ClipName, frac: number, at: number, dur: number, ease = 'power2.out'): number {
    if (!actor.hasClip(clip)) return at + dur;
    const total = Math.max(0.05, actor.clipDuration(clip));
    return this.proxy(at, dur, ease, (p) => actor.scrub(clip, total * frac * p));
  }

  /** Tween a numeric 0..1 style value pair on all of `actors` (used for dim). */
  tweenEach(at: number, dur: number, from: number, to: number, fn: (v: number) => void, ease = 'power1.inOut'): number {
    return this.proxy(at, dur, ease, (p) => fn(from + (to - from) * p));
  }
}
