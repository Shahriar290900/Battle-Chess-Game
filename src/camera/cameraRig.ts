// Turn camera rig (architecture §7).
// The camera orbits the board centre via a spherical proxy {azimuth, polar, radius} that GSAP tweens;
// the camera transform is rebuilt from it every frame. Positions are never lerped across the board
// (that dives through pieces) and azimuth always takes the shorter arc to the seat.
//   seats: White azimuth 0 (camera on +z), Black azimuth π
//   modes: follow / fixed (proxy, seat-driven), free (OrbitControls, limited polar), top (near top-down)
//   borrow()/restore(): the capture director drives the camera; restore() tweens back to the seat
//
// Free-look (render-readability): in follow / fixed / top modes the player may orbit and zoom with `orbit()` / `zoom()` (driven by
// boardInput: mouse drag on empty space, wheel, two-finger drag, pinch). The offsets are layered on top of the seat pose, so a refit
// on resize keeps them proportional, and `recenter()` (or the next `toSeat`, e.g. after a move) eases them back to zero.
// `viewFallen()` flies to a captured-pieces ledge for a close 3/4 view; `recenter()` or another `viewFallen()` leaves it.
//
// Every pose goal (seat / ledge) is a function evaluated live, so a resize or orientation change during a swing or while idle
// refits immediately instead of finishing a stale tween.
import { gsap } from 'gsap';
import { PerspectiveCamera, Vector3 } from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import type { CameraMode, CameraRig, CinematicCameraHandle, Side, Square } from '../contracts';
import { squareToWorld } from '../contracts';

/** Close-up of one captured-pieces ledge (see Graveyard.viewOf). All vectors are on the ground plane. */
export interface LedgeView {
  /** World centre of the occupied part of the ledge. */
  cx: number; cz: number;
  /** Unit vector the kneeling pieces face (toward the board). */
  fx: number; fz: number;
  /** Unit vector along the ledge. */
  lx: number; lz: number;
  /** Half length of the occupied part (>= a minimum so an empty ledge is still framed). */
  half: number;
}

export interface CameraRigImpl extends CameraRig {
  readonly seat: Side;
  /** Reserve screen space (px) at the bottom for the HUD device; the board is fitted above it. */
  setReserve(bottomPx: number): void;
  /** Animation-speed multiplier for the turn swing (settings.animSpeed). */
  setSpeed(speed: number): void;
  /** Suspend OrbitControls while a piece is being dragged. */
  setInputLocked(locked: boolean): void;
  /** Project a point of the board plane into CSS pixels (tests / debugging). */
  projectSquare(sq: Square): { x: number; y: number };
  /** True when the player may free-look right now (not borrowed, not OrbitControls' own 'free' mode). */
  readonly canFreeLook: boolean;
  /** Orbit offset in radians (positive dAzimuth swings the camera toward +x; positive dPolar lowers it). */
  orbit(dAzimuth: number, dPolar: number): void;
  /** Multiply the camera distance (factor < 1 zooms in), within limits. */
  zoom(factor: number): void;
  /** Ease the free-look offsets (and the ledge view) back to the seat pose. */
  recenter(duration?: number): Promise<void>;
  /** Fly to a ledge (null = back to the seat). Resolves when the move is done. */
  viewFallen(ledge: LedgeView | null): Promise<void>;
  /** 'seat' | 'fallen'. */
  readonly view: 'seat' | 'fallen';
  /** Free-look offset or ledge view active (something recenter() would undo). */
  readonly offSeat: boolean;
  /** Notified (next frame at the latest) when `view` / `offSeat` change. */
  onViewChange(fn: () => void): () => void;
  dispose(): void;
}

const TARGET = new Vector3(0, 0.3, 0);
const FOV = 32; // long lens: near pieces stay small, far ranks stay readable
const DEG = Math.PI / 180;
// Steeper than the original 46 / 31 degrees: the board reads squarer, the far ranks are easy to hit and tall pieces hide less.
const LANDSCAPE_POLAR = 36 * DEG;
const PORTRAIT_POLAR = 26 * DEG;
const TOP_POLAR = 4 * DEG;
const SEAT_AZIMUTH: Record<Side, number> = { w: 0, b: Math.PI };
const FREE_MIN_POLAR = 10 * DEG;
const FREE_MAX_POLAR = 72 * DEG; // never reaches the board plane
const ZOOM_MIN = 0.42, ZOOM_MAX = 1.4;

/** Wrap an angle difference into (-π, π]. */
const wrapPi = (a: number) => { a = (a + Math.PI) % (Math.PI * 2); if (a <= 0) a += Math.PI * 2; return a - Math.PI; };
const clamp01 = (v: number) => Math.min(Math.max(v, 0), 1);
const clamp = (v: number, lo: number, hi: number) => Math.min(Math.max(v, lo), hi);

// Points that must stay on screen: frame corners and the tops of the tallest pieces.
const FRAME_POINTS: Vector3[] = [];
const FIT_POINTS: Vector3[] = [];
for (const sx of [-1, 1]) for (const sz of [-1, 1]) {
  FRAME_POINTS.push(new Vector3(5.3 * sx, 0, 5.3 * sz));
  FIT_POINTS.push(new Vector3(5.3 * sx, 0, 5.3 * sz), new Vector3(3.6 * sx, 1.6, 3.6 * sz));
}

// Landscape also keeps the captured-pieces ledges (render/graveyard.ts, x = +-6.2, 1.05 wide) in frame; portrait puts them at the board ends.
const LEDGE_FIT_POINTS: Vector3[] = [];
const FIT_ALL: Vector3[] = [];
for (const sx of [-1, 1]) for (const sz of [-1, 1]) LEDGE_FIT_POINTS.push(new Vector3(6.8 * sx, 0, 3.7 * sz));
FIT_ALL.push(...FIT_POINTS, ...LEDGE_FIT_POINTS);

interface Goal { az: number; polar: number; radius: number; fx: number; fy: number; fz: number }

export function createCameraRig(dom: HTMLElement, opts: { aspect?: number } = {}): CameraRigImpl {
  const camera = new PerspectiveCamera(FOV, opts.aspect ?? 16 / 9, 0.1, 160);
  const probe = new PerspectiveCamera(FOV, 16 / 9, 0.1, 160);
  const proxy = { azimuth: 0, polar: LANDSCAPE_POLAR, radius: 15 };
  /** Look-at offset from TARGET (ledge views). */
  const focus = { x: 0, y: 0, z: 0 };
  /** Free-look offsets: target values (tweened) and the damped values actually applied. */
  const fl = { az: 0, pol: 0, zoom: 0 }; // zoom is ln(factor)
  const shown = { az: 0, pol: 0, zoom: 0 };
  const rig = { seat: 'w' as Side, mode: 'follow' as CameraMode };
  let width = 1280, height = 720;
  let seatPolar = LANDSCAPE_POLAR;
  let seatRadius = 15;
  let topRadius = 14;
  let swing: gsap.core.Tween | null = null;
  let swingResolve: (() => void) | null = null;
  let flTween: gsap.core.Tween | null = null;
  let borrowed = false;
  let restoring = false;
  let restoreTween: gsap.core.Tween | null = null;
  let restoreResolve: (() => void) | null = null;
  let locked = false;
  let speed = 1;
  let reserve = 0;
  let time = 0;
  let trauma = 0;
  let ledge: LedgeView | null = null;
  const viewListeners = new Set<() => void>();
  let lastNotified = '';
  const offset = new Vector3();
  const look = TARGET.clone();
  const tmp = new Vector3();
  const centre = new Vector3();

  const controls = new OrbitControls(camera, dom);
  controls.enabled = false;
  controls.enablePan = false;
  controls.enableDamping = true;
  controls.dampingFactor = 0.09;
  controls.minPolarAngle = 12 * DEG;
  controls.maxPolarAngle = 80 * DEG;
  controls.minDistance = 5;
  controls.maxDistance = 30;
  controls.target.copy(TARGET);

  // -------------------------------------------------------------- pose maths
  /** Smallest radius at which every point stays inside the given NDC limits, for a camera orbiting `c` at (az, polar). */
  function fitRadiusAt(polar: number, az: number, c: Vector3, pts: Vector3[], aspect: number, limX: number, limHi: number, limLo: number = -limHi): number {
    probe.aspect = aspect;
    probe.updateProjectionMatrix();
    const sp = Math.sin(polar), cp = Math.cos(polar);
    let lo = 2, hi = 70;
    for (let i = 0; i < 28; i++) {
      const r = (lo + hi) / 2;
      probe.position.set(c.x + r * sp * Math.sin(az), c.y + r * cp, c.z + r * sp * Math.cos(az));
      probe.lookAt(c);
      probe.updateMatrixWorld(true);
      let ok = true;
      for (const p of pts) {
        tmp.copy(p).project(probe);
        if (Math.abs(tmp.x) > limX || tmp.y > limHi || tmp.y < limLo || tmp.z > 1) { ok = false; break; }
      }
      if (ok) hi = r; else lo = r;
    }
    return hi;
  }
  function fitRadius(polar: number, aspect: number, limX: number, limHi: number, limLo: number = -limHi): number {
    return fitRadiusAt(polar, 0, TARGET, aspect > 1.05 ? FIT_ALL : FIT_POINTS, aspect, limX, limHi, limLo);
  }

  const limits = () => {
    const aspect = width / height;
    const limX = aspect > 1.05 ? 0.9 : 0.96;
    const limY = aspect > 1.05 ? 0.92 : 0.82;
    const limLo = Math.min(-limY + (2 * reserve) / height, limY - 0.5);
    return { aspect, limX, limY, limLo };
  };

  function recomputeFit() {
    const { aspect, limX, limY, limLo } = limits();
    // Portrait raises the camera (smaller polar); landscape sits a little lower for a more cinematic player view.
    const k = clamp01((aspect - 0.7) / (1.45 - 0.7));
    seatPolar = PORTRAIT_POLAR + (LANDSCAPE_POLAR - PORTRAIT_POLAR) * k;
    const goal = (limLo + limY) / 2;
    // Fit the radius, then nudge the look-at height until the board (frame corners) is vertically centred.
    TARGET.y = 0.3;
    for (let i = 0; i < 4; i++) {
      seatRadius = fitRadius(seatPolar, aspect, limX, limY, limLo);
      probe.position.set(0, TARGET.y + seatRadius * Math.cos(seatPolar), seatRadius * Math.sin(seatPolar));
      probe.lookAt(TARGET);
      probe.updateMatrixWorld(true);
      let lo = Infinity, hi = -Infinity;
      for (const p of FRAME_POINTS) { tmp.copy(p).project(probe); lo = Math.min(lo, tmp.y); hi = Math.max(hi, tmp.y); }
      const mid = (lo + hi) / 2 - goal;
      TARGET.y = Math.min(Math.max(TARGET.y + mid * seatRadius * Math.tan((FOV * DEG) / 2) * 0.9, -1.5), 1.5);
    }
    seatRadius = fitRadius(seatPolar, aspect, limX, limY, limLo);
    topRadius = fitRadius(TOP_POLAR, aspect, limX, limY, limLo);
    controls.maxDistance = Math.max(30, seatRadius * 1.8);
    controls.target.copy(TARGET);
  }

  function modePolar(): number { return rig.mode === 'top' ? TOP_POLAR : seatPolar; }
  function modeRadius(): number { return rig.mode === 'top' ? topRadius : seatRadius; }

  /** Goal pose of the current view (seat or ledge), evaluated live so a resize refits it. */
  function goalNow(): Goal {
    if (ledge) return ledgeGoal(ledge);
    return { az: proxy.azimuth, polar: modePolar(), radius: modeRadius(), fx: 0, fy: 0, fz: 0 };
  }
  function seatGoal(az: number): Goal { return { az, polar: modePolar(), radius: modeRadius(), fx: 0, fy: 0, fz: 0 }; }

  const LEDGE_POLAR = 44 * DEG;
  function ledgeGoal(v: LedgeView): Goal {
    // Camera on the board side of the ledge, swung toward the seat along the ledge: a 3/4 view of the kneeling pieces.
    const seatZ = rig.seat === 'w' ? 1 : -1;
    let sgn = v.lz * seatZ >= 0 ? 1 : -1;
    if (Math.abs(v.lz) < 0.2) sgn = v.lx >= 0 ? 1 : -1; // ledge along x (portrait ends): pick a fixed side
    let dx = v.fx * 0.82 + v.lx * sgn * 0.57, dz = v.fz * 0.82 + v.lz * sgn * 0.57;
    const n = Math.hypot(dx, dz) || 1; dx /= n; dz /= n;
    const az = Math.atan2(dx, dz);
    const c = centre.set(v.cx, 0.34, v.cz);
    const pts: Vector3[] = [];
    for (const s of [-1, 1]) for (const w of [-0.45, 0.45]) {
      pts.push(new Vector3(v.cx + v.lx * v.half * s + v.fx * w, 0, v.cz + v.lz * v.half * s + v.fz * w));
      pts.push(new Vector3(v.cx + v.lx * v.half * s, 0.95, v.cz + v.lz * v.half * s));
    }
    const { aspect, limX, limY, limLo } = limits();
    const radius = fitRadiusAt(LEDGE_POLAR, az, c, pts, aspect, Math.min(limX, 0.95), Math.min(limY, 0.9), Math.max(limLo, -0.9));
    return { az, polar: LEDGE_POLAR, radius, fx: v.cx - TARGET.x, fy: 0.34 - TARGET.y, fz: v.cz - TARGET.z };
  }

  function poseFrom(az: number, polar: number, radius: number, cx: number, cy: number, cz: number, lookAt: Vector3 = centre.set(cx, cy, cz)) {
    const sp = Math.sin(polar);
    camera.position.set(cx + radius * sp * Math.sin(az), cy + radius * Math.cos(polar), cz + radius * sp * Math.cos(az));
    camera.lookAt(lookAt);
  }

  /** Rebuild the camera from proxy + focus + free-look offsets (not borrowed, not OrbitControls mode). */
  function applyPose(idle: number) {
    const pol = clamp(proxy.polar + shown.pol, FREE_MIN_POLAR, FREE_MAX_POLAR);
    const rad = clamp(proxy.radius * Math.exp(shown.zoom), 3.5, 40);
    poseFrom(proxy.azimuth + shown.az + idle, pol, rad, TARGET.x + focus.x, TARGET.y + focus.y, TARGET.z + focus.z);
  }

  const offSeatNow = () => ledge !== null || Math.abs(fl.az) > 1e-3 || Math.abs(fl.pol) > 1e-3 || Math.abs(fl.zoom) > 1e-3;
  function notifyView() {
    const key = `${ledge ? 'f' : 's'}${offSeatNow() ? 1 : 0}`;
    if (key === lastNotified) return;
    lastNotified = key;
    viewListeners.forEach((f) => f());
  }

  // -------------------------------------------------------------- tweens
  function killSwing() {
    swing?.kill();
    swing = null;
    const r = swingResolve;
    swingResolve = null;
    r?.();
  }
  function killFl() { flTween?.kill(); flTween = null; }

  /** Fly the proxy (+ focus, + free-look offsets back to zero) to a live goal along the shorter arc. */
  function flyTo(goal: () => Goal, duration: number, pushOut: boolean): Promise<void> {
    killSwing();
    killFl();
    const g0 = goal();
    const a0 = proxy.azimuth, p0 = proxy.polar, r0 = proxy.radius;
    const f0 = { x: focus.x, y: focus.y, z: focus.z };
    const s0 = { az: fl.az, pol: fl.pol, zoom: fl.zoom };
    const arc = wrapPi(g0.az - a0);
    // The free-look offsets fold into the start pose so the swing starts exactly where the camera is.
    const k = { t: 0 };
    return new Promise<void>((resolve) => {
      swingResolve = resolve;
      const finish = () => {
        const g = goal();
        proxy.azimuth = a0 + arc + (g.az - g0.az); proxy.polar = g.polar; proxy.radius = g.radius;
        focus.x = g.fx; focus.y = g.fy; focus.z = g.fz;
        fl.az = fl.pol = fl.zoom = 0;
        swing = null; swingResolve = null;
        notifyView();
        resolve();
      };
      swing = gsap.to(k, {
        t: 1, duration, ease: 'power2.inOut',
        onUpdate: () => {
          const e = k.t;
          const g = goal(); // live: a resize mid-swing refits
          proxy.azimuth = a0 + (arc + (g.az - g0.az)) * e;
          proxy.polar = p0 + (g.polar - p0) * e;
          proxy.radius = r0 + (g.radius - r0) * e + (pushOut ? Math.sin(Math.PI * k.t) * 1.0 : 0);
          focus.x = f0.x + (g.fx - f0.x) * e; focus.y = f0.y + (g.fy - f0.y) * e; focus.z = f0.z + (g.fz - f0.z) * e;
          fl.az = s0.az * (1 - e); fl.pol = s0.pol * (1 - e); fl.zoom = s0.zoom * (1 - e);
        },
        onComplete: finish,
      });
      swing.timeScale(speed);
    });
  }

  function syncProxyFromCamera() {
    const p = camera.position;
    const dx = p.x - TARGET.x, dy = p.y - TARGET.y, dz = p.z - TARGET.z;
    const r = Math.hypot(dx, dy, dz);
    proxy.radius = r;
    proxy.polar = Math.acos(Math.min(Math.max(dy / r, -1), 1));
    proxy.azimuth = Math.atan2(dx, dz);
  }

  function resetFreeLook() {
    killFl();
    fl.az = fl.pol = fl.zoom = 0;
    shown.az = shown.pol = shown.zoom = 0;
    focus.x = focus.y = focus.z = 0;
    ledge = null;
    notifyView();
  }

  // -------------------------------------------------------------- public API
  const handle: CinematicCameraHandle = {
    camera,
    set(position, lookAt, fov) {
      camera.position.copy(position);
      camera.lookAt(lookAt);
      look.copy(lookAt);
      offset.set(0, 0, 0);
      if (fov !== undefined && Math.abs(camera.fov - fov) > 1e-4) { camera.fov = fov; camera.updateProjectionMatrix(); }
    },
  };

  const api: CameraRigImpl = {
    camera,
    get mode() { return rig.mode; },
    set mode(m: CameraMode) { api.setMode(m); },
    get seat() { return rig.seat; },
    get canFreeLook() { return !borrowed && rig.mode !== 'free'; },
    get view() { return ledge ? 'fallen' : 'seat'; },
    get offSeat() { return offSeatNow(); },

    setMode(mode) {
      if (mode === rig.mode) return;
      const prev = rig.mode;
      rig.mode = mode;
      if (borrowed) return;
      if (mode === 'free') {
        killSwing();
        // fold the layered free-look pose into the proxy so OrbitControls starts from what the player sees
        applyPose(0);
        resetFreeLook();
        syncProxyFromCamera();
        controls.enabled = !locked;
        controls.update();
        return;
      }
      controls.enabled = false;
      if (prev === 'free') syncProxyFromCamera();
      void flyTo(() => seatGoal(SEAT_AZIMUTH[rig.seat]), 0.9, false);
    },

    toSeat(side, o = {}) {
      rig.seat = side;
      if (borrowed) return Promise.resolve();
      if (rig.mode === 'free') return Promise.resolve();
      if (o.instant) {
        killSwing();
        resetFreeLook();
        proxy.azimuth = SEAT_AZIMUTH[side]; proxy.polar = modePolar(); proxy.radius = modeRadius();
        return Promise.resolve();
      }
      const az = SEAT_AZIMUTH[side];
      return flyTo(() => seatGoal(az), 1.4, true);
    },

    borrow() {
      killSwing();
      resetFreeLook();
      restoreTween?.kill();
      restoreTween = null;
      const r = restoreResolve; restoreResolve = null; r?.();
      restoring = false;
      borrowed = true;
      controls.enabled = false;
      look.copy(TARGET);
      return handle;
    },

    restore(duration = 0.9) {
      if (!borrowed) return Promise.resolve();
      restoring = true;
      const p = camera.position;
      const r0 = Math.hypot(p.x - TARGET.x, p.y - TARGET.y, p.z - TARGET.z);
      const pol0 = Math.acos(Math.min(Math.max((p.y - TARGET.y) / r0, -1), 1));
      const az0 = Math.atan2(p.x - TARGET.x, p.z - TARGET.z);
      const look0 = look.clone();
      const fov0 = camera.fov;
      const free = rig.mode === 'free';
      const az1 = free ? az0 : az0 + wrapPi(SEAT_AZIMUTH[rig.seat] - az0);
      const pol1 = () => (free ? pol0 : modePolar());
      const r1 = () => (free ? r0 : modeRadius()); // live: a resize during the sequence refits the landing pose
      const s = { t: 0 };
      const lk = new Vector3();
      if (duration <= 0) {
        // restore(0) snaps immediately.
        poseFrom(az1, pol1(), r1(), TARGET.x, TARGET.y, TARGET.z, TARGET);
        if (camera.fov !== FOV) { camera.fov = FOV; camera.updateProjectionMatrix(); }
        restoring = false; borrowed = false;
        proxy.azimuth = az1; proxy.polar = pol1(); proxy.radius = r1();
        if (free) { controls.enabled = !locked; controls.update(); }
        return Promise.resolve();
      }
      return new Promise<void>((resolve) => {
        restoreResolve = resolve;
        const finish = () => {
          restoring = false; borrowed = false; restoreTween = null; restoreResolve = null;
          if (camera.fov !== FOV) { camera.fov = FOV; camera.updateProjectionMatrix(); }
          proxy.azimuth = az1; proxy.polar = pol1(); proxy.radius = r1();
          if (free) { controls.enabled = !locked; controls.update(); }
          resolve();
        };
        restoreTween = gsap.to(s, {
          t: 1, duration, ease: 'power2.inOut',
          onUpdate: () => {
            const e = s.t;
            lk.copy(look0).lerp(TARGET, e);
            poseFrom(az0 + (az1 - az0) * e, pol0 + (pol1() - pol0) * e, r0 + (r1() - r0) * e, TARGET.x, TARGET.y, TARGET.z, lk);
            const fov = fov0 + (FOV - fov0) * e;
            if (Math.abs(camera.fov - fov) > 1e-4) { camera.fov = fov; camera.updateProjectionMatrix(); }
          },
          onComplete: finish,
        });
      });
    },

    shake(t) { trauma = Math.min(1, trauma + Math.max(0, t)); },

    resize(w, h) {
      width = Math.max(1, w); height = Math.max(1, h);
      camera.aspect = width / height;
      camera.updateProjectionMatrix();
      recomputeFit();
      // A running swing re-reads its goal every frame; otherwise (and not borrowed) the proxy snaps to the new fit right now.
      if (!swing && !borrowed && rig.mode !== 'free') {
        const g = goalNow();
        proxy.polar = g.polar; proxy.radius = g.radius; proxy.azimuth = ledge ? g.az : proxy.azimuth;
        focus.x = g.fx; focus.y = g.fy; focus.z = g.fz;
        applyPose(0);
      }
    },

    setReserve(px) {
      const n = Math.max(0, Math.round(px));
      if (n === reserve) return;
      reserve = n;
      api.resize(width, height);
    },

    setSpeed(v) { speed = Math.min(Math.max(v, 0.25), 4); swing?.timeScale(speed); },

    setInputLocked(l) {
      locked = l;
      if (rig.mode === 'free' && !borrowed) controls.enabled = !l;
    },

    orbit(dAz, dPol) {
      if (!api.canFreeLook || swing) return; // a seat swing / ledge flight in progress owns the camera
      killFl();
      fl.az += dAz;
      fl.pol = clamp(proxy.polar + fl.pol + dPol, FREE_MIN_POLAR, FREE_MAX_POLAR) - proxy.polar;
      notifyView();
    },

    zoom(factor) {
      if (!api.canFreeLook || swing) return;
      killFl();
      const lo = Math.max(Math.log(ZOOM_MIN), Math.log(3.5 / Math.max(proxy.radius, 1)));
      const hi = Math.min(Math.log(ZOOM_MAX), Math.log(40 / Math.max(proxy.radius, 1)));
      fl.zoom = clamp(fl.zoom + Math.log(factor), lo, hi);
      notifyView();
    },

    recenter(duration = 0.7) {
      if (borrowed) return Promise.resolve();
      if (rig.mode === 'free') return Promise.resolve();
      if (!offSeatNow() && !swing) return Promise.resolve();
      const az = proxy.azimuth + wrapPi(SEAT_AZIMUTH[rig.seat] - proxy.azimuth);
      ledge = null;
      if (duration <= 0) {
        killSwing(); resetFreeLook();
        proxy.azimuth = az; proxy.polar = modePolar(); proxy.radius = modeRadius();
        return Promise.resolve();
      }
      return flyTo(() => seatGoal(az), duration, false).then(notifyView);
    },

    viewFallen(v) {
      if (borrowed || rig.mode === 'free') return Promise.resolve();
      if (!v) return api.recenter(0.9);
      ledge = v;
      notifyView();
      return flyTo(() => ledgeGoal(v), 1.05, false);
    },

    onViewChange(fn) { viewListeners.add(fn); return () => { viewListeners.delete(fn); }; },

    projectSquare(sq) {
      if (!borrowed && rig.mode !== 'free') applyPose(0);
      camera.updateMatrixWorld(true);
      squareToWorld(sq, tmp);
      tmp.project(camera);
      return { x: (tmp.x * 0.5 + 0.5) * width, y: (-tmp.y * 0.5 + 0.5) * height };
    },

    update(dt) {
      time += dt;
      if (borrowed && !restoring) {
        // The capture director sets the pose each frame; shake is additive on top.
        offset.set(0, 0, 0);
      } else if (!borrowed) {
        if (rig.mode === 'free') {
          camera.position.sub(offset);
          offset.set(0, 0, 0);
          controls.update();
        } else {
          // damp the free-look offsets (instant while a tween drives them, so the swing is not delayed)
          const k = swing || flTween ? 1 : 1 - Math.exp(-dt * 16);
          shown.az += (fl.az - shown.az) * k; shown.pol += (fl.pol - shown.pol) * k; shown.zoom += (fl.zoom - shown.zoom) * k;
          const calm = !swing && !ledge && Math.abs(shown.az) + Math.abs(shown.pol) + Math.abs(shown.zoom) < 0.02;
          const idle = calm ? Math.sin((time * Math.PI * 2) / 8) * 0.6 * DEG : 0;
          applyPose(idle);
          offset.set(0, 0, 0);
        }
      }
      if (trauma > 0.001) {
        const a = trauma * trauma;
        const n = (f: number, ph: number) => Math.sin(time * f + ph) + 0.5 * Math.sin(time * f * 2.3 + ph * 1.7);
        const o = tmp.set(n(41, 0) * 0.16 * a, n(37, 2) * 0.16 * a, n(29, 4) * 0.1 * a);
        o.applyQuaternion(camera.quaternion);
        camera.position.add(o);
        offset.add(o);
        camera.rotateZ(n(33, 1) * 0.035 * a);
        trauma = Math.max(0, trauma - dt * 1.4);
      }
    },

    dispose() {
      killSwing();
      killFl();
      restoreTween?.kill();
      controls.dispose();
      viewListeners.clear();
    },
  };

  recomputeFit();
  api.resize(width, height);
  proxy.azimuth = SEAT_AZIMUTH.w; proxy.polar = seatPolar; proxy.radius = seatRadius;
  applyPose(0);
  return api;
}
