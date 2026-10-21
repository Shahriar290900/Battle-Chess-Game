// Turn camera rig (architecture §7).
// The camera orbits the board centre via a spherical proxy {azimuth, polar, radius} that GSAP tweens;
// the camera transform is rebuilt from it every frame. Positions are never lerped across the board
// (that dives through pieces) and azimuth always takes the shorter arc to the seat.
//   seats: White azimuth 0 (camera on +z), Black azimuth π
//   modes: follow / fixed (proxy, seat-driven), free (OrbitControls, limited polar), top (near top-down)
//   borrow()/restore(): the capture director drives the camera; restore() tweens back to the seat
import { gsap } from 'gsap';
import { PerspectiveCamera, Vector3 } from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import type { CameraMode, CameraRig, CinematicCameraHandle, Side, Square } from '../contracts';
import { squareToWorld } from '../contracts';

export interface CameraRigImpl extends CameraRig {
  readonly seat: Side;
  /** Suspend OrbitControls while a piece is being dragged. */
  setInputLocked(locked: boolean): void;
  /** Project a point of the board plane into CSS pixels (tests / debugging). */
  projectSquare(sq: Square): { x: number; y: number };
  dispose(): void;
}

const TARGET = new Vector3(0, 0.3, 0);
const FOV = 38;
const DEG = Math.PI / 180;
const LANDSCAPE_POLAR = 52 * DEG;
const PORTRAIT_POLAR = 34 * DEG;
const TOP_POLAR = 4 * DEG;
const SEAT_AZIMUTH: Record<Side, number> = { w: 0, b: Math.PI };

/** Wrap an angle difference into (-π, π]. */
const wrapPi = (a: number) => { a = (a + Math.PI) % (Math.PI * 2); if (a <= 0) a += Math.PI * 2; return a - Math.PI; };
const clamp01 = (v: number) => Math.min(Math.max(v, 0), 1);

// Points that must stay on screen: frame corners and the tops of the tallest pieces.
const FIT_POINTS: Vector3[] = [];
for (const sx of [-1, 1]) for (const sz of [-1, 1]) {
  FIT_POINTS.push(new Vector3(5.3 * sx, -0.2, 5.3 * sz), new Vector3(4.4 * sx, 1.6, 4.4 * sz));
}

export function createCameraRig(dom: HTMLElement, opts: { aspect?: number } = {}): CameraRigImpl {
  const camera = new PerspectiveCamera(FOV, opts.aspect ?? 16 / 9, 0.1, 160);
  const probe = new PerspectiveCamera(FOV, 16 / 9, 0.1, 160);
  const proxy = { azimuth: 0, polar: LANDSCAPE_POLAR, radius: 15 };
  const rig = { seat: 'w' as Side, mode: 'follow' as CameraMode };
  let width = 1280, height = 720;
  let seatPolar = LANDSCAPE_POLAR;
  let seatRadius = 15;
  let topRadius = 14;
  let swing: gsap.core.Timeline | null = null;
  let swingResolve: (() => void) | null = null;
  let borrowed = false;
  let restoring = false;
  let restoreTween: gsap.core.Tween | null = null;
  let restoreResolve: (() => void) | null = null;
  let locked = false;
  let time = 0;
  let trauma = 0;
  const offset = new Vector3();
  const look = TARGET.clone();
  const tmp = new Vector3();

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
  function fitRadius(polar: number, aspect: number, limX: number, limY: number): number {
    probe.aspect = aspect;
    probe.updateProjectionMatrix();
    let lo = 5, hi = 60;
    for (let i = 0; i < 28; i++) {
      const r = (lo + hi) / 2;
      probe.position.set(0, TARGET.y + r * Math.cos(polar), r * Math.sin(polar));
      probe.lookAt(TARGET);
      probe.updateMatrixWorld(true);
      let ok = true;
      for (const p of FIT_POINTS) {
        tmp.copy(p).project(probe);
        if (Math.abs(tmp.x) > limX || Math.abs(tmp.y) > limY || tmp.z > 1) { ok = false; break; }
      }
      if (ok) hi = r; else lo = r;
    }
    return hi;
  }

  function recomputeFit() {
    const aspect = width / height;
    // Portrait raises the camera (smaller polar) and reserves room for the HUD above and below the board.
    const k = clamp01((aspect - 0.7) / (1.45 - 0.7));
    seatPolar = PORTRAIT_POLAR + (LANDSCAPE_POLAR - PORTRAIT_POLAR) * k;
    const limY = 0.8 + 0.1 * k;
    // Landscape HUD panels flank the board (CSS --side-w = clamp(150px, 19vw, 250px) + gutter).
    const side = Math.min(250, Math.max(150, width * 0.19)) + 14;
    const limX = aspect > 1.05 ? Math.max(0.5, (width / 2 - side) / (width / 2)) : 0.97;
    seatRadius = fitRadius(seatPolar, aspect, limX, limY);
    topRadius = fitRadius(TOP_POLAR, aspect, limX, limY);
    controls.maxDistance = Math.max(30, seatRadius * 1.8);
  }

  function modePolar(): number { return rig.mode === 'top' ? TOP_POLAR : seatPolar; }
  function modeRadius(): number { return rig.mode === 'top' ? topRadius : seatRadius; }

  function poseFrom(az: number, polar: number, radius: number, lookAt: Vector3) {
    const sp = Math.sin(polar);
    camera.position.set(
      TARGET.x + radius * sp * Math.sin(az),
      TARGET.y + radius * Math.cos(polar),
      TARGET.z + radius * sp * Math.cos(az),
    );
    camera.lookAt(lookAt);
  }

  // -------------------------------------------------------------- tweens
  function killSwing() {
    swing?.kill();
    swing = null;
    const r = swingResolve;
    swingResolve = null;
    r?.();
  }

  /** Tween the proxy to the given seat/polar/radius along the shorter arc. */
  function swingTo(az: number, polar: number, radius: number, duration: number, pushOut: boolean): Promise<void> {
    killSwing();
    const target = proxy.azimuth + wrapPi(az - proxy.azimuth);
    return new Promise<void>((resolve) => {
      swingResolve = resolve;
      const tl = gsap.timeline({
        onComplete: () => {
          proxy.azimuth = target; proxy.polar = modePolar(); proxy.radius = modeRadius();
          swing = null; swingResolve = null; resolve();
        },
      });
      swing = tl;
      tl.to(proxy, { azimuth: target, polar, duration, ease: 'power2.inOut' }, 0);
      if (pushOut) {
        tl.to(proxy, { radius: radius + 1.0, duration: duration * 0.5, ease: 'sine.out' }, 0);
        tl.to(proxy, { radius: radius - 0.08, duration: duration * 0.5, ease: 'sine.in' }, duration * 0.5);
        tl.to(proxy, { radius, duration: 0.15, ease: 'power2.out' }, duration);
      } else {
        tl.to(proxy, { radius, duration, ease: 'power2.inOut' }, 0);
      }
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

    setMode(mode) {
      if (mode === rig.mode) return;
      const prev = rig.mode;
      rig.mode = mode;
      if (borrowed) return;
      if (mode === 'free') {
        killSwing();
        syncProxyFromCamera();
        controls.enabled = !locked;
        controls.update();
        return;
      }
      controls.enabled = false;
      if (prev === 'free') syncProxyFromCamera();
      void swingTo(SEAT_AZIMUTH[rig.seat], modePolar(), modeRadius(), 0.9, false);
    },

    toSeat(side, o = {}) {
      rig.seat = side;
      if (borrowed) return Promise.resolve();
      if (rig.mode === 'free') return Promise.resolve();
      if (o.instant) {
        killSwing();
        proxy.azimuth = SEAT_AZIMUTH[side]; proxy.polar = modePolar(); proxy.radius = modeRadius();
        return Promise.resolve();
      }
      return swingTo(SEAT_AZIMUTH[side], modePolar(), modeRadius(), 1.4, true);
    },

    borrow() {
      killSwing();
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
      const pol1 = free ? pol0 : modePolar();
      const r1 = free ? r0 : modeRadius();
      const s = { t: 0 };
      const lk = new Vector3();
      if (duration <= 0) {
        // restore(0) snaps immediately.
        poseFrom(az1, pol1, r1, TARGET);
        if (camera.fov !== FOV) { camera.fov = FOV; camera.updateProjectionMatrix(); }
        restoring = false; borrowed = false;
        proxy.azimuth = az1; proxy.polar = pol1; proxy.radius = r1;
        if (free) { controls.enabled = !locked; controls.update(); }
        return Promise.resolve();
      }
      return new Promise<void>((resolve) => {
        restoreResolve = resolve;
        const finish = () => {
          restoring = false; borrowed = false; restoreTween = null; restoreResolve = null;
          if (camera.fov !== FOV) { camera.fov = FOV; camera.updateProjectionMatrix(); }
          proxy.azimuth = az1; proxy.polar = pol1; proxy.radius = r1;
          if (free) { controls.enabled = !locked; controls.update(); }
          resolve();
        };
        restoreTween = gsap.to(s, {
          t: 1, duration, ease: 'power2.inOut',
          onUpdate: () => {
            const e = s.t;
            lk.copy(look0).lerp(TARGET, e);
            poseFrom(az0 + (az1 - az0) * e, pol0 + (pol1 - pol0) * e, r0 + (r1 - r0) * e, lk);
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
      if (!swing && !borrowed) {
        if (rig.mode !== 'free') { proxy.polar = modePolar(); proxy.radius = modeRadius(); }
      }
    },

    setInputLocked(l) {
      locked = l;
      if (rig.mode === 'free' && !borrowed) controls.enabled = !l;
    },

    projectSquare(sq) {
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
          const idle = !swing ? Math.sin((time * Math.PI * 2) / 8) * 0.6 * DEG : 0;
          poseFrom(proxy.azimuth + idle, proxy.polar, proxy.radius, TARGET);
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
      restoreTween?.kill();
      controls.dispose();
    },
  };

  recomputeFit();
  api.resize(width, height);
  proxy.azimuth = SEAT_AZIMUTH.w; proxy.polar = seatPolar; proxy.radius = seatRadius;
  poseFrom(proxy.azimuth, proxy.polar, proxy.radius, TARGET);
  return api;
}
