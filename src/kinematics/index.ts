// Kinematics layer (see README.md): procedural secondary motion applied AFTER the clip pose each frame.
// Spring bones (top, head), inertial lean + landing squash (body / mount_body), look-at IK, knockback wobble,
// idle life. Only bone rotations, plus body position/scale, are touched; root and model transforms are read, never written.
import { Object3D, Vector3, type Camera } from 'three';
import { PEDESTAL_HEIGHT, ROLE_HEIGHT, type KinematicsApi, type PieceActor } from '../contracts';
import { TrackedRot, TrackedVec } from './bones';
import { impulseFalloff, newLookAngles, solveLook, type LookAngles, type LookKind } from './look';
import { MAX_SIM_DT, SUBSTEP, Spring } from './spring';
import { ROLE_CFG, type RoleCfg } from './tables';

export { impulseFalloff, solveLook } from './look';
export { ROLE_CFG } from './tables';

export interface KinematicsExtras {
  /** Optional: enables distance and behind-camera culling. */
  setCamera(camera: Camera | null): void;
  /** Rigs simulated / culled in the last update (diagnostics). */
  stats(): { attached: number; active: number; culled: number };
}

const TAU = Math.PI * 2;
const CULL_DIST2 = 26 * 26;
const MAX_DV = 2.5;
const WARP_SPEED = 30;
const GRAVITY = 14;
const wrapPi = (a: number) => (a > Math.PI ? a - TAU : a < -Math.PI ? a + TAU : a);
const clamp = (v: number, lo: number, hi: number) => (v < lo ? lo : v > hi ? hi : v);

let rigSeed = 1;
function rnd(): number { rigSeed = (rigSeed * 1664525 + 1013904223) >>> 0; return rigSeed / 4294967296; }

class Rig {
  readonly cfg: RoleCfg;
  readonly isKnight: boolean;
  readonly look: LookKind;
  // bones (any may be null)
  readonly body: TrackedRot | null; readonly bodyPos: TrackedVec | null; readonly bodyScale: TrackedVec | null;
  readonly spine: TrackedRot | null; readonly head: TrackedRot | null; readonly top: TrackedRot | null; readonly mountHead: TrackedRot | null;
  readonly all: TrackedRot[] = [];
  readonly vecs: TrackedVec[] = [];
  // springs
  readonly leanP: Spring; readonly leanR: Spring; readonly leanT: Spring;
  readonly topP: Spring; readonly topR: Spring; readonly topT: Spring;
  readonly headP: Spring; readonly headR: Spring;
  readonly knockP: Spring; readonly knockR: Spring; readonly squash: Spring;
  readonly springs: Spring[];
  hop = 0; hopV = 0;
  // motion tracking
  warm = false; px = 0; py = 0; pz = 0; vsx = 0; vsy = 0; vsz = 0; pyaw = 0; wys = 0; fall = 0;
  gate = 1;
  // look-at
  hasTarget = false; readonly target = new Vector3(); lookWT = 0; lookW = 0;
  readonly lookTgt = newLookAngles(); readonly lookCur = newLookAngles();
  readonly headLocal = new Vector3();
  jointH = 0.4;
  // idle life
  t = rnd() * 100;
  idleTick = (rigSeed >>> 8) % 3;
  readonly idle = [0, 0, 0, 0, 0, 0, 0, 0];
  readonly ph = [rnd() * TAU, rnd() * TAU, rnd() * TAU, rnd() * TAU, rnd() * TAU, rnd() * TAU, rnd() * TAU, rnd() * TAU];
  readonly fr = [0.31 + rnd() * 0.22, 0.13 + rnd() * 0.1, 0.17 + rnd() * 0.12, 0.43 + rnd() * 0.2, 0.23 + rnd() * 0.15, 0.09 + rnd() * 0.08];

  constructor(readonly actor: PieceActor) {
    const m = actor.model;
    this.cfg = ROLE_CFG[actor.role];
    this.isKnight = actor.role === 'knight';
    const find = (n: string) => m.getObjectByName(n) ?? null;
    const rot = (n: string): TrackedRot | null => {
      const o = find(n);
      if (!o) return null;
      const t = new TrackedRot(o);
      this.all.push(t);
      return t;
    };
    const mountBody = this.isKnight ? find('mount_body') : null;
    const primary = mountBody ?? find('body');
    if (primary) {
      this.body = new TrackedRot(primary); this.all.push(this.body);
      this.bodyPos = new TrackedVec(primary.position, false);
      this.bodyScale = new TrackedVec(primary.scale, true);
      this.vecs.push(this.bodyPos, this.bodyScale);
    } else { this.body = null; this.bodyPos = null; this.bodyScale = null; }
    this.spine = rot('spine'); this.head = rot('head'); this.top = rot('top'); this.mountHead = this.isKnight ? rot('mount_head') : null;
    this.look = this.mountHead ? 'knight' : this.head ? 'humanoid' : this.top && this.body ? 'rook' : 'none';

    const c = this.cfg;
    this.leanP = new Spring(c.lean.freq, c.lean.zeta, c.lean.max);
    this.leanR = new Spring(c.lean.freq, c.lean.zeta, c.lean.max);
    this.leanT = new Spring(c.lean.freq * 1.2, 0.4, 0.15);
    this.topP = new Spring(c.top.freq, c.top.zeta, c.top.max);
    this.topR = new Spring(c.top.freq * 0.93, c.top.zeta, c.top.max);
    this.topT = new Spring(c.top.freq * 1.3, c.top.zeta + 0.1, c.top.max);
    this.headP = new Spring(c.head.freq, c.head.zeta, c.head.max);
    this.headR = new Spring(c.head.freq * 1.1, c.head.zeta, c.head.max);
    this.knockP = new Spring(2.2, 0.22, 0.35);
    this.knockR = new Spring(2.2, 0.22, 0.35);
    this.squash = new Spring(3.2, 0.28, 0.09);
    this.springs = [this.leanP, this.leanR, this.leanT, this.topP, this.topR, this.topT, this.headP, this.headR, this.knockP, this.knockR, this.squash];

    // rest heights, measured once (matrices are recomputed here; attach is not a hot path)
    const root = actor.root;
    root.updateWorldMatrix(true, true);
    const probe = (o: Object3D | undefined | null, fallback: number): number => {
      if (!o) return fallback;
      o.getWorldPosition(this.headLocal);
      root.worldToLocal(this.headLocal);
      return Number.isFinite(this.headLocal.y) && this.headLocal.y > 0.15 ? this.headLocal.y : fallback;
    };
    this.jointH = probe(primary, 0.4);
    const headObj = (this.head ?? this.mountHead ?? this.top)?.bone ?? null;
    const hy = probe(headObj, ROLE_HEIGHT[actor.role] * 0.85);
    if (headObj) {
      headObj.getWorldPosition(this.headLocal); root.worldToLocal(this.headLocal);
      if (!(Number.isFinite(this.headLocal.x) && Number.isFinite(this.headLocal.z))) this.headLocal.set(0, hy, 0);
      this.headLocal.y = hy;
    } else this.headLocal.set(0, hy, 0);
  }

  hasAnyBone(): boolean { return this.all.length > 0; }

  restore(): void {
    for (const t of this.all) t.restore();
    for (const v of this.vecs) v.restore();
  }

  clear(): void {
    for (const s of this.springs) s.reset();
    this.hop = this.hopV = 0; this.warm = false; this.fall = 0; this.vsx = this.vsy = this.vsz = this.wys = 0;
    this.lookW = 0;
    const a = this.lookCur; a.headYaw = a.headPitch = a.spineYaw = a.mountYaw = a.mountPitch = a.bodyYaw = a.topYaw = 0;
  }
}

const noise = (t: number, f1: number, f2: number, p1: number, p2: number) =>
  0.6 * Math.sin(TAU * f1 * t + p1) + 0.4 * Math.sin(TAU * f2 * t + p2);

export function createKinematics(): KinematicsApi & KinematicsExtras {
  const rigs: Rig[] = [];
  const byActor = new WeakMap<PieceActor, Rig>();
  let enabled = true;
  let camera: Camera | null = null;
  let active = 0, culled = 0;

  const _zero: LookAngles = newLookAngles();

  function landing(r: Rig, speed: number): void {
    if (speed < 1.5) return;
    r.squash.kick(-Math.min(speed, 8) * 0.28 / Math.max(0.7, r.cfg.mass * 0.6 + 0.4));
  }

  function stepRig(r: Rig, dt: number, dtS: number, n: number, h: number, kv: number, kLook: number, kGate: number): void {
    const a = r.actor, root = a.root, model = a.model, cfg = r.cfg;
    // ---- clip gate: scripted (scrubbed) clips own the pose; fade our additive layer out around them
    const scripted = (a as unknown as { mode?: string }).mode === 'scrub';
    r.gate += ((scripted ? 0 : 1) - r.gate) * kGate;
    const g = r.gate;

    // ---- motion estimate (root + model offsets, in world XZ; cinematics tween both)
    const yaw = root.rotation.y + model.rotation.y;
    const sy = Math.sin(yaw), cy = Math.cos(yaw);
    const rs = Math.sin(root.rotation.y), rc = Math.cos(root.rotation.y);
    const mp = model.position;
    const wx = root.position.x + mp.x * rc + mp.z * rs;
    const wy = root.position.y + mp.y;
    const wz = root.position.z - mp.x * rs + mp.z * rc;
    if (!r.warm) {
      r.px = wx; r.py = wy; r.pz = wz; r.pyaw = yaw; r.warm = true; r.vsx = r.vsy = r.vsz = r.wys = 0; r.fall = 0;
    } else {
      const inv = 1 / dt;
      const vx = (wx - r.px) * inv, vy = (wy - r.py) * inv, vz = (wz - r.pz) * inv;
      const wyaw = wrapPi(yaw - r.pyaw) * inv;
      r.px = wx; r.py = wy; r.pz = wz; r.pyaw = yaw;
      if (vx * vx + vy * vy + vz * vz > WARP_SPEED * WARP_SPEED) {
        r.vsx = r.vsy = r.vsz = r.wys = 0; r.fall = 0; // teleport (undo/sync): no inertia
      } else {
        const dx = clamp((vx - r.vsx) * kv, -MAX_DV, MAX_DV), dz = clamp((vz - r.vsz) * kv, -MAX_DV, MAX_DV);
        const dw = clamp((wyaw - r.wys) * kv, -MAX_DV * 4, MAX_DV * 4);
        r.vsx += dx; r.vsz += dz; r.vsy += (vy - r.vsy) * kv; r.wys += dw;
        const df = dx * sy + dz * cy;       // forward component
        const dl = dx * cy - dz * sy;       // left (+X local) component
        const L = cfg.lean, T = cfg.top, H = cfg.head;
        r.leanP.kick(r.leanP.k * L.gain * df);
        r.leanR.kick(-r.leanR.k * L.gain * dl);
        r.leanT.kick(-r.leanT.k * 0.01 * dw);
        r.topP.kick(T.sign * r.topP.k * T.gain * df);
        r.topR.kick(-T.sign * r.topR.k * T.gain * dl);
        r.topT.kick(-r.topT.k * T.twist * dw);
        r.headP.kick(-r.headP.k * H.gain * df);
        r.headR.kick(r.headR.k * H.gain * dl);
        // landing: large downward speed arrested
        if (vy < -1.5) r.fall = Math.max(r.fall, -vy);
        else if (r.fall > 0 && vy > -0.4) { landing(r, r.fall); r.fall = 0; }
      }
    }

    // ---- hop ballistics (impulse-driven), lands into squash
    if (r.hop > 0 || r.hopV > 0) {
      r.hopV -= GRAVITY * dtS;
      r.hop += r.hopV * dtS;
      if (r.hop <= 0) { landing(r, -r.hopV); r.hop = 0; r.hopV = 0; }
    }

    // ---- springs
    for (let s = 0; s < n; s++) for (let i = 0; i < r.springs.length; i++) r.springs[i].step(h);
    r.t += dtS;

    // ---- look-at
    r.lookW += (r.lookWT - r.lookW) * kLook;
    if (r.hasTarget && r.look !== 'none' && (r.lookW > 0.001 || r.lookWT > 0)) {
      const hl = r.headLocal;
      const hx = root.position.x + hl.x * rc + hl.z * rs, hz = root.position.z - hl.x * rs + hl.z * rc;
      const ddx = r.target.x - hx, ddy = r.target.y - (root.position.y + hl.y), ddz = r.target.z - hz;
      const lx = ddx * cy - ddz * sy, lz = ddx * sy + ddz * cy;
      const horiz = Math.sqrt(lx * lx + lz * lz);
      if (horiz > 0.05) solveLook(r.look, r.spine !== null, Math.atan2(lx, lz), -Math.atan2(ddy, horiz), r.lookTgt);
    }
    const c = r.lookCur, tg = r.lookTgt, wl = r.lookWT > 0 ? 1 : 0; // targets decay to zero on release
    const tgt = wl ? tg : _zero;
    c.headYaw += (tgt.headYaw - c.headYaw) * kLook; c.headPitch += (tgt.headPitch - c.headPitch) * kLook;
    c.spineYaw += (tgt.spineYaw - c.spineYaw) * kLook; c.mountYaw += (tgt.mountYaw - c.mountYaw) * kLook;
    c.mountPitch += (tgt.mountPitch - c.mountPitch) * kLook; c.bodyYaw += (tgt.bodyYaw - c.bodyYaw) * kLook;
    c.topYaw += (tgt.topYaw - c.topYaw) * kLook;
    const lw = r.lookW; // 0..1 weight (already smoothed)

    // ---- idle life (faded by motion so it never fights a travelling piece)
    const t = r.t, p = r.ph, f = r.fr, id = r.idle;
    const still = 1 / (1 + 0.8 * (r.vsx * r.vsx + r.vsz * r.vsz));
    const ia = cfg.idle * still;
    if (++r.idleTick >= 3) { // idle noise is slow (< 0.6 Hz): refresh every 3rd frame per rig
      r.idleTick = 0;
      id[0] = Math.sin(TAU * f[0] * t + p[0]);
      id[1] = noise(t, f[1], f[2], p[1], p[2]);
      id[2] = noise(t, f[2], f[4], p[3], p[4]);
      id[3] = noise(t, f[5], f[4], p[5], p[6]);
      id[4] = noise(t, f[3], f[1], p[7], p[0]);
      id[5] = noise(t, f[3], f[2], p[2], p[5]);
      id[6] = noise(t, f[4], f[0], p[6], p[1]);
    }
    const breath = id[0];
    const iBodyR = 0.008 * ia * id[1];
    const iBodyP = 0.006 * ia * id[2];
    const iHeadY = 0.05 * ia * id[3];
    const iHeadP = 0.02 * ia * id[4];
    const iTopP = 0.015 * ia * id[5];
    const iTopR = 0.015 * ia * id[6];

    // ---- write bones
    if (r.body) {
      const bp = g * (r.leanP.x + r.knockP.x + iBodyP + (r.spine ? 0 : 0.008 * ia * breath));
      const br = g * (r.leanR.x + r.knockR.x + iBodyR);
      const by = g * (r.leanT.x + lw * r.lookCur.bodyYaw);
      r.body.write(bp, by, br);
      const sq = r.squash.x * g;
      const sY = 1 + sq, sXZ = 1 - sq * 0.5;
      r.bodyScale!.write(sXZ, sY, sXZ);
      const hop = r.hop * g;
      const dy = hop + (r.jointH - PEDESTAL_HEIGHT) * (sY - 1);
      r.bodyPos!.write(0, dy, 0);
    }
    if (r.spine) r.spine.write(g * (0.012 * ia * breath), g * lw * c.spineYaw, 0);
    if (r.head) r.head.write(g * (r.headP.x + iHeadP + lw * c.headPitch + (r.knockP.x * 0.4)), g * (iHeadY + lw * c.headYaw), g * (r.headR.x - r.knockR.x * 0.4));
    if (r.mountHead) r.mountHead.write(g * (0.4 * iHeadP + lw * c.mountPitch), g * (0.4 * iHeadY + lw * c.mountYaw), 0);
    if (r.top) r.top.write(g * (r.topP.x + iTopP + r.knockP.x * 0.5 * cfg.top.sign), g * (r.topT.x + lw * c.topYaw), g * (r.topR.x + iTopR - r.knockR.x * 0.5 * cfg.top.sign));
  }
  const api: KinematicsApi & KinematicsExtras = {
    attach(actor) {
      if (byActor.has(actor)) return;
      const r = new Rig(actor);
      byActor.set(actor, r);
      rigs.push(r);
    },
    detach(actor) {
      const r = byActor.get(actor);
      if (!r) return;
      r.restore();
      byActor.delete(actor);
      const i = rigs.indexOf(r);
      if (i >= 0) { rigs[i] = rigs[rigs.length - 1]; rigs.pop(); }
    },
    lookAt(actor, target, weight = 1) {
      const r = byActor.get(actor);
      if (!r) return;
      if (!target) { r.lookWT = 0; return; }
      r.target.copy(target);
      r.hasTarget = true;
      r.lookWT = clamp(weight, 0, 1);
    },
    impulse(origin, strength, radius = 3) {
      if (!enabled || strength <= 0) return;
      for (let i = 0; i < rigs.length; i++) {
        const r = rigs[i], root = r.actor.root;
        const dx = root.position.x - origin.x, dz = root.position.z - origin.z;
        const d = Math.sqrt(dx * dx + dz * dz);
        const fall = impulseFalloff(d, radius);
        if (fall <= 0) continue;
        const mag = (strength * fall) / r.cfg.mass;
        const yaw = root.rotation.y + r.actor.model.rotation.y;
        const sy = Math.sin(yaw), cy = Math.cos(yaw);
        let ux = 0, uz = 0;
        if (d > 1e-3) { ux = dx / d; uz = dz / d; }
        const df = ux * sy + uz * cy, dl = ux * cy - uz * sy;
        const K = 1.8 * mag;
        r.knockP.kick(K * df);
        r.knockR.kick(-K * dl);
        r.topP.kick(r.cfg.top.sign * 2.2 * K * df * 0.6);
        r.topR.kick(-r.cfg.top.sign * 2.2 * K * dl * 0.6);
        r.headP.kick(-0.8 * K * df);
        r.headR.kick(0.8 * K * dl);
        if (mag >= 1 && r.cfg.mass <= 1 && r.hop <= 0) {
          r.hopV = Math.min(0.8 + 0.4 * (mag - 1), 1.5);
          r.hop = 1e-4;
        }
      }
    },
    setEnabled(on) {
      if (on === enabled) return;
      enabled = on;
      for (const r of rigs) { r.restore(); r.clear(); }
    },
    setCamera(c) { camera = c; },
    stats: () => ({ attached: rigs.length, active, culled }),
    update(dt) {
      if (!enabled || !(dt > 1e-5) || rigs.length === 0) return;
      const dtS = Math.min(dt, MAX_SIM_DT);
      const n = Math.max(1, Math.ceil(dtS / SUBSTEP));
      const h = dtS / n;
      const kv = 1 - Math.exp(-dtS / 0.035);
      const kLook = 1 - Math.exp(-dtS / 0.07);   // ~0.25 s to settle
      const kGate = 1 - Math.exp(-dtS / 0.1);
      let cx = 0, cy = 0, cz = 0, fx = 0, fy = 0, fz = 0;
      if (camera) {
        const e = camera.matrixWorld.elements;
        cx = e[12]; cy = e[13]; cz = e[14]; fx = -e[8]; fy = -e[9]; fz = -e[10];
      }
      active = 0; culled = 0;
      for (let i = 0; i < rigs.length; i++) {
        const r = rigs[i];
        if (!r.hasAnyBone()) continue;
        if (!r.actor.model.visible) { r.warm = false; culled++; continue; }
        let cull = false;
        if (camera) {
          const p = r.actor.root.position;
          const dx = p.x - cx, dy = p.y - cy, dz = p.z - cz;
          cull = dx * dx + dy * dy + dz * dz > CULL_DIST2 || dx * fx + dy * fy + dz * fz < -1.5;
        }
        if (cull) { r.warm = false; culled++; continue; }
        active++;
        stepRig(r, dt, dtS, n, h, kv, kLook, kGate);
      }
    },
  };
  return api;
}
