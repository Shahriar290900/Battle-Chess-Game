import {
  AdditiveBlending, Color, DynamicDrawUsage, Group, InstancedBufferAttribute, InstancedBufferGeometry,
  Mesh, NormalBlending, Object3D, PlaneGeometry, ShaderMaterial, Vector3,
} from 'three';
import type { EmitOptions, GraphicsSettings, ParticlePreset } from '../contracts';
import { COUNT_MUL, PARTICLE_CAP, rand } from './common';

// CPU-simulated, pooled, instanced billboards. Per-particle integration (gravity, buoyancy, drag, curl-noise turbulence,
// wind, floor collision with bounce/settle/hug, sub-emitters) in a tight loop over struct-of-arrays state; results are
// uploaded to four instanced attributes. Soft-particle depth fade is intentionally omitted (no depth texture in the
// composer); particles are alpha-faded by life instead.

const VERT = /* glsl */ `
attribute vec3 aPos; attribute vec3 aVel; attribute vec4 aCol; attribute vec4 aInfo;
varying vec2 vUv; varying vec4 vCol; varying float vShape; varying float vAge; varying float vSeed;
void main(){
  float size = aInfo.x;
  if (size <= 0.0) { gl_Position = vec4(2.0, 2.0, 2.0, 1.0); return; }
  vec4 mv = viewMatrix * vec4(aPos, 1.0);
  vec2 q = position.xy;
  if (aInfo.z > 0.5 && aInfo.z < 1.5) {
    vec2 d = (viewMatrix * vec4(aVel, 0.0)).xy;
    float sp = length(d);
    d = sp > 0.0001 ? d / sp : vec2(0.0, 1.0);
    vec2 pr = vec2(-d.y, d.x);
    mv.xy += (d * q.x * (1.0 + sp * 0.16) + pr * q.y * 0.45) * size;
  } else {
    float c = cos(aInfo.y), s = sin(aInfo.y);
    mv.xy += vec2(c * q.x - s * q.y, s * q.x + c * q.y) * size;
  }
  gl_Position = projectionMatrix * mv;
  vUv = position.xy * 2.0; vCol = aCol; vShape = aInfo.z; vAge = aInfo.w; vSeed = aInfo.y;
}`;

const FRAG = /* glsl */ `
varying vec2 vUv; varying vec4 vCol; varying float vShape; varying float vAge; varying float vSeed;
void main(){
  vec2 p = vUv; float r = length(p); float a;
  if (vShape < 0.5) { a = smoothstep(1.0, 0.0, r); a *= a; }
  else if (vShape < 1.5) { a = exp(-pow(abs(p.y) * 3.2, 2.0)) * (1.0 - smoothstep(0.2, 1.0, abs(p.x))); }
  else if (vShape < 2.5) {
    float d = abs(p.x) + abs(p.y);
    a = smoothstep(1.0, 0.45, d);
    a += 0.5 * exp(-abs(p.x * p.y) * 18.0) * (1.0 - r);
    a *= 0.55 + 0.45 * sin(vAge * 26.0 + vSeed * 40.0);
  } else {
    a = smoothstep(1.0, 0.0, r);
    float n = 0.5 + 0.5 * sin(p.x * 3.5 + vSeed * 17.0) * sin(p.y * 3.5 + vSeed * 9.0);
    a = pow(a, 1.3) * mix(0.55, 1.0, n);
  }
  float al = vCol.a * a;
  if (al < 0.004) discard;
  gl_FragColor = vec4(vCol.rgb, al);
}`;

type Shape = 0 | 1 | 2 | 3; // glow, spark streak, glitter diamond, smoke puff
const enum Floor { None = 0, Bounce = 1, Settle = 2, Hug = 3 }

class Layer {
  readonly mesh: Mesh;
  readonly mat: ShaderMaterial;
  readonly geo = new InstancedBufferGeometry();
  readonly aPos: InstancedBufferAttribute; readonly aVel: InstancedBufferAttribute;
  readonly aCol: InstancedBufferAttribute; readonly aInfo: InstancedBufferAttribute;
  // simulation state (struct of arrays)
  readonly pos: Float32Array; readonly vel: Float32Array; readonly c0: Float32Array; readonly c1: Float32Array;
  readonly life: Float32Array; readonly age: Float32Array; readonly alpha: Float32Array;
  readonly s0: Float32Array; readonly s1: Float32Array; readonly drag: Float32Array; readonly grav: Float32Array;
  readonly turb: Float32Array; readonly wind: Float32Array; readonly spin: Float32Array; readonly rot: Float32Array;
  readonly shape: Uint8Array; readonly floor: Uint8Array; readonly bounces: Uint8Array; readonly sub: Uint8Array;
  readonly orb: Float32Array; // orbit: speed, radius, rise, phase ; speed 0 => free flight
  readonly org: Float32Array; // orbit origin
  alive = 0;
  cursor = 0;
  ring = 1;
  constructor(readonly capacity: number, additive: boolean) {
    const plane = new PlaneGeometry(1, 1);
    this.geo.index = plane.index;
    this.geo.setAttribute('position', plane.getAttribute('position'));
    const mk = (n: number) => { const a = new InstancedBufferAttribute(new Float32Array(capacity * n), n); a.setUsage(DynamicDrawUsage); return a; };
    this.aPos = mk(3); this.aVel = mk(3); this.aCol = mk(4); this.aInfo = mk(4);
    this.geo.setAttribute('aPos', this.aPos); this.geo.setAttribute('aVel', this.aVel);
    this.geo.setAttribute('aCol', this.aCol); this.geo.setAttribute('aInfo', this.aInfo);
    this.geo.instanceCount = capacity;
    const f = (n: number) => new Float32Array(capacity * n);
    this.pos = f(3); this.vel = f(3); this.c0 = f(3); this.c1 = f(3);
    this.life = f(1); this.age = f(1); this.alpha = f(1); this.s0 = f(1); this.s1 = f(1); this.drag = f(1); this.grav = f(1);
    this.turb = f(1); this.wind = f(1); this.spin = f(1); this.rot = f(1); this.orb = f(4); this.org = f(3);
    this.shape = new Uint8Array(capacity); this.floor = new Uint8Array(capacity); this.bounces = new Uint8Array(capacity); this.sub = new Uint8Array(capacity);
    this.mat = new ShaderMaterial({
      vertexShader: VERT, fragmentShader: FRAG, transparent: true, depthWrite: false, depthTest: true,
      blending: additive ? AdditiveBlending : NormalBlending,
    });
    this.mesh = new Mesh(this.geo, this.mat);
    this.mesh.frustumCulled = false;
    this.mesh.renderOrder = additive ? 12 : 11;
  }
  setRing(n: number): void {
    this.ring = Math.max(1, Math.min(this.capacity, n));
    this.cursor = 0;
    this.life.fill(0); this.age.fill(0); this.aInfo.array.fill(0);
    this.aInfo.needsUpdate = true; this.alive = 0;
  }
}

interface Emitter {
  preset: ParticlePreset; origin: Vector3; dir: Vector3; opts: EmitOptions;
  total: number; remaining: number; elapsed: number; duration: number; accum: number;
  follow?: Object3D; followOffset: Vector3; tint?: Color;
}

const DEFAULTS: Record<ParticlePreset, { count: number; duration: number }> = {
  embers: { count: 24, duration: 0 }, sparks: { count: 36, duration: 0 }, smoke: { count: 12, duration: 0 },
  frostMist: { count: 18, duration: 0 }, iceGlitter: { count: 40, duration: 0 }, summonSpiral: { count: 64, duration: 1.2 },
  dustPuff: { count: 14, duration: 0 }, fireWave: { count: 90, duration: 0.8 }, frostBeam: { count: 80, duration: 0.6 },
};

const _p = new Vector3(), _v = new Vector3(), _d = new Vector3(), _u = new Vector3(), _w = new Vector3();
const C = (r: number, g: number, b: number) => new Color(r, g, b);

function cone(dir: Vector3, spread: number, out: Vector3): Vector3 {
  _u.set(Math.random() - 0.5, Math.random() - 0.5, Math.random() - 0.5).normalize();
  return out.copy(dir).addScaledVector(_u, spread).normalize();
}

export class ParticleSystem {
  readonly group = new Group();
  private add: Layer;
  private alpha: Layer;
  private emitters: Emitter[] = [];
  private time = 0;
  private countMul = 0.75;
  private ambient = false;
  private ambientAcc = 0;
  private activeUntil = 0;
  private needsClear = false;
  /** One-shot tint consumed by the next emit (see emitFaction in index.ts). */
  nextTint: Color | null = null;
  /** Wind in world units/s, slowly varying. */
  private wind = new Vector3();
  /** Invoked on a floor bounce of a spark (strength 0..1) — hooked for audio by index.ts. */
  onClink?: (strength: number) => void;

  constructor() {
    const max = PARTICLE_CAP.high;
    this.add = new Layer(max, true);
    this.alpha = new Layer(max, false);
    this.group.add(this.alpha.mesh, this.add.mesh);
    this.setGraphics({ particles: 'medium', ambient: false } as GraphicsSettings);
  }

  setGraphics(g: Pick<GraphicsSettings, 'particles' | 'ambient'>): void {
    const cap = PARTICLE_CAP[g.particles];
    this.countMul = COUNT_MUL[g.particles];
    const a = Math.ceil(cap * 0.62);
    this.add.setRing(a);
    this.alpha.setRing(cap - a);
    this.ambient = g.ambient;
  }

  emit(preset: ParticlePreset, position: Vector3, opts: EmitOptions = {}): void {
    const def = DEFAULTS[preset];
    const dur = opts.duration ?? def.duration;
    const total = Math.max(1, Math.round((opts.count ?? def.count) * this.countMul));
    const e: Emitter = {
      preset, origin: position.clone(), dir: (opts.direction ? opts.direction.clone() : new Vector3(0, 1, 0)).normalize(),
      opts, total, remaining: total, elapsed: 0, duration: dur, accum: 0, follow: opts.follow,
      followOffset: new Vector3(), tint: this.nextTint ?? undefined,
    };
    this.nextTint = null;
    if (opts.follow) { opts.follow.getWorldPosition(_p); e.followOffset.copy(position).sub(_p); }
    if (dur <= 0) { for (let i = 0; i < total; i++) this.spawnOne(e); } else this.emitters.push(e);
  }

  update(dt: number): void {
    if (dt <= 0) return;
    // zero cost when idle: nothing alive, nothing emitting, no ambient
    if (!this.emitters.length && !this.ambient && this.time >= this.activeUntil) {
      if (this.needsClear) { this.upload(this.add); this.upload(this.alpha); this.needsClear = false; }
      return;
    }
    this.needsClear = true;
    // sub-step long frames so integration stays stable
    const n = Math.min(4, Math.ceil(dt / (1 / 45)));
    const h = dt / n;
    for (let i = 0; i < n; i++) this.step(h);
    this.upload(this.add); this.upload(this.alpha);
  }

  private step(dt: number): void {
    this.time += dt;
    this.wind.set(Math.sin(this.time * 0.23) * 0.35 + 0.15, 0, Math.cos(this.time * 0.17) * 0.25);
    for (let i = this.emitters.length - 1; i >= 0; i--) {
      const e = this.emitters[i];
      if (e.follow) { e.follow.getWorldPosition(_p); e.origin.copy(_p).add(e.followOffset); }
      e.elapsed += dt;
      e.accum += (e.total / e.duration) * dt;
      let n = Math.min(Math.floor(e.accum), e.remaining);
      e.accum -= Math.floor(e.accum);
      e.remaining -= n;
      while (n-- > 0) this.spawnOne(e);
      if (e.elapsed >= e.duration || e.remaining <= 0) this.emitters.splice(i, 1);
    }
    if (this.ambient) {
      this.ambientAcc += dt;
      while (this.ambientAcc > 0.22) {
        this.ambientAcc -= 0.22;
        const ember = Math.random() < 0.5;
        _p.set(rand(-3.8, 3.8), rand(0.05, 0.4), ember ? rand(-3.8, -0.5) : rand(0.5, 3.8));
        _v.set(rand(-0.05, 0.05), ember ? rand(0.25, 0.5) : rand(0.05, 0.2), rand(-0.05, 0.05));
        const col = ember ? C(1.8, 0.8, 0.2) : C(0.5, 1.2, 1.5);
        this.put(this.add, _p, _v, rand(2.5, 4.5), 0.035, 0.012, col, 0.55, ember ? C(0.4, 0.08, 0.02) : C(0.2, 0.5, 0.8),
          0.4, ember ? -0.05 : 0.02, 0.2, 0.6, rand(-1, 1), 0, Floor.None, 0);
      }
    }
    this.sim(this.add, dt); this.sim(this.alpha, dt);
  }

  private sim(L: Layer, dt: number): void {
    const t = this.time;
    for (let i = 0; i < L.ring; i++) {
      if (L.life[i] <= 0) continue;
      const age = (L.age[i] += dt);
      const life = L.life[i];
      if (age >= life) { L.life[i] = 0; L.aInfo.array[i * 4] = 0; continue; }
      const k3 = i * 3;
      let x = L.pos[k3], y = L.pos[k3 + 1], z = L.pos[k3 + 2];
      let vx = L.vel[k3], vy = L.vel[k3 + 1], vz = L.vel[k3 + 2];
      const orbSpeed = L.orb[i * 4];
      if (orbSpeed !== 0) {
        const k = age / life;
        const a = L.orb[i * 4 + 3] + orbSpeed * age;
        const r = L.orb[i * 4 + 1] * (1 - k * 0.65);
        const nx = L.org[k3] + Math.cos(a) * r, ny = L.org[k3 + 1] + L.orb[i * 4 + 2] * age, nz = L.org[k3 + 2] + Math.sin(a) * r;
        vx = (nx - x) / dt; vy = (ny - y) / dt; vz = (nz - z) / dt;
        x = nx; y = ny; z = nz;
      } else {
        const drag = Math.exp(-L.drag[i] * dt);
        vx *= drag; vy *= drag; vz *= drag;
        const heat = L.grav[i] < 0 ? 1 - age / life : 1; // buoyancy fades as the particle cools
        vy -= L.grav[i] * (L.grav[i] < 0 ? heat : 1) * dt;
        const tb = L.turb[i];
        if (tb > 0) { // divergence-free (curl-like) field: each component depends only on the other axes
          vx += (Math.sin(1.7 * y + 0.9 * t + L.rot[i]) + Math.cos(2.3 * z - 0.7 * t)) * tb * dt * 3;
          vy += (Math.sin(1.3 * z + 0.8 * t) + Math.cos(2.1 * x + 0.6 * t + L.rot[i])) * tb * dt * 2;
          vz += (Math.sin(1.9 * x - 0.5 * t) + Math.cos(1.5 * y + 0.7 * t + L.rot[i])) * tb * dt * 3;
        }
        const wf = L.wind[i];
        if (wf > 0) { vx += (this.wind.x - vx * 0.2) * wf * dt; vz += (this.wind.z - vz * 0.2) * wf * dt; }
        x += vx * dt; y += vy * dt; z += vz * dt;
        const fl = L.floor[i];
        if (fl !== Floor.None && y < 0.012) {
          if (fl === Floor.Bounce) {
            if (vy < 0) {
              if (Math.abs(vy) > 0.8 && this.onClink && Math.random() < 0.25) this.onClink(Math.min(1, Math.abs(vy) / 8));
              y = 0.012; vy = -vy * 0.45; vx *= 0.72; vz *= 0.72;
              if (++L.bounces[i] > 3) { L.age[i] += life * 0.25; }
              if (L.sub[i] === 0 && Math.abs(vy) > 1 && Math.random() < 0.3) this.spawnSubEmber(x, y, z);
            }
          } else if (fl === Floor.Settle) { y = 0.015; vx *= 0.3; vz *= 0.3; vy = 0; L.age[i] += dt * 1.5; } // embers rest and fade faster
          else { y = Math.max(y, 0.06); if (vy < 0) vy *= -0.2; vx *= 0.98; vz *= 0.98; } // mist hugs the floor
        }
      }
      L.pos[k3] = x; L.pos[k3 + 1] = y; L.pos[k3 + 2] = z;
      L.vel[k3] = vx; L.vel[k3 + 1] = vy; L.vel[k3 + 2] = vz;
      L.rot[i] += L.spin[i] * dt;
    }
  }

  private upload(L: Layer): void {
    const P = L.aPos.array as Float32Array, V = L.aVel.array as Float32Array, Cc = L.aCol.array as Float32Array, I = L.aInfo.array as Float32Array;
    for (let i = 0; i < L.ring; i++) {
      const life = L.life[i];
      if (life <= 0) { I[i * 4] = 0; continue; }
      const k = Math.min(1, L.age[i] / life);
      const k3 = i * 3;
      P[k3] = L.pos[k3]; P[k3 + 1] = L.pos[k3 + 1]; P[k3 + 2] = L.pos[k3 + 2];
      V[k3] = L.vel[k3]; V[k3 + 1] = L.vel[k3 + 1]; V[k3 + 2] = L.vel[k3 + 2];
      const m = k * k * (3 - 2 * k);
      Cc[i * 4] = L.c0[k3] + (L.c1[k3] - L.c0[k3]) * m;
      Cc[i * 4 + 1] = L.c0[k3 + 1] + (L.c1[k3 + 1] - L.c0[k3 + 1]) * m;
      Cc[i * 4 + 2] = L.c0[k3 + 2] + (L.c1[k3 + 2] - L.c0[k3 + 2]) * m;
      const fadeIn = Math.min(1, k / 0.08);
      Cc[i * 4 + 3] = L.alpha[i] * fadeIn * Math.pow(1 - k, 1.4);
      I[i * 4] = L.s0[i] + (L.s1[i] - L.s0[i]) * k;
      I[i * 4 + 1] = L.shape[i] === 1 ? 0 : L.rot[i];
      I[i * 4 + 2] = L.shape[i];
      I[i * 4 + 3] = L.age[i];
    }
    L.aPos.needsUpdate = L.aVel.needsUpdate = L.aCol.needsUpdate = L.aInfo.needsUpdate = true;
  }

  private spawnSubEmber(x: number, y: number, z: number): void {
    _p.set(x, y + 0.02, z); _v.set(rand(-0.4, 0.4), rand(0.5, 1.2), rand(-0.4, 0.4));
    this.put(this.add, _p, _v, rand(0.5, 1.0), 0.04, 0.01, C(3, 1.3, 0.3), 1, C(0.6, 0.1, 0.02), 0.8, 2, 0.1, 0.2, 0, 0, Floor.Settle, 1);
  }

  private put(layer: Layer, p: Vector3, v: Vector3, life: number, s0: number, s1: number, c: Color, alpha: number, e: Color,
    drag: number, grav: number, turb: number, wind: number, spin: number, shape: Shape, floor: Floor, sub: number,
    orbit?: [number, number, number, number]): void {
    const i = layer.cursor;
    layer.cursor = (layer.cursor + 1) % layer.ring;
    if (this.time + life > this.activeUntil) this.activeUntil = this.time + life;
    const k3 = i * 3;
    layer.pos[k3] = p.x; layer.pos[k3 + 1] = p.y; layer.pos[k3 + 2] = p.z;
    layer.vel[k3] = v.x; layer.vel[k3 + 1] = v.y; layer.vel[k3 + 2] = v.z;
    layer.c0[k3] = c.r; layer.c0[k3 + 1] = c.g; layer.c0[k3 + 2] = c.b;
    layer.c1[k3] = e.r; layer.c1[k3 + 1] = e.g; layer.c1[k3 + 2] = e.b;
    layer.life[i] = life; layer.age[i] = 0; layer.alpha[i] = alpha; layer.s0[i] = s0; layer.s1[i] = s1;
    layer.drag[i] = drag; layer.grav[i] = grav; layer.turb[i] = turb; layer.wind[i] = wind; layer.spin[i] = spin;
    layer.rot[i] = Math.random() * 6.283;
    layer.shape[i] = shape; layer.floor[i] = floor; layer.bounces[i] = 0; layer.sub[i] = sub;
    if (orbit) {
      layer.orb[i * 4] = orbit[0]; layer.orb[i * 4 + 1] = orbit[1]; layer.orb[i * 4 + 2] = orbit[2]; layer.orb[i * 4 + 3] = orbit[3];
      layer.org[k3] = p.x; layer.org[k3 + 1] = p.y; layer.org[k3 + 2] = p.z;
    } else layer.orb[i * 4] = 0;
  }

  private spawnOne(e: Emitter): void {
    const o = e.opts, s = o.scale ?? 1, sp = o.speed, o3 = e.origin, dir = e.dir, spread = o.spread;
    switch (e.preset) {
      case 'embers': {
        cone(dir, spread ?? 0.9, _v).multiplyScalar((sp ?? 1.3) * rand(0.5, 1.4));
        _p.copy(o3).add(_w.set(rand(-0.15, 0.15), rand(0, 0.2), rand(-0.15, 0.15)).multiplyScalar(s));
        this.put(this.add, _p, _v, rand(1.2, 2.6), 0.09 * s, 0.025 * s, C(3.2, 1.5, 0.35), 1, C(0.7, 0.12, 0.02), 0.7, -0.9, 0.5, 0.8, rand(-2, 2), 0, Floor.Settle, 0);
        break;
      }
      case 'sparks': {
        cone(dir, spread ?? 1.1, _v).multiplyScalar((sp ?? 5) * rand(0.4, 1.3));
        _p.copy(o3);
        this.put(this.add, _p, _v, rand(0.5, 1.1), 0.11 * s, 0.05 * s, C(4.0, 2.6, 0.9), 1, C(1.2, 0.3, 0.05), 0.9, 9.5, 0, 0, 0, 1, Floor.Bounce, 0);
        break;
      }
      case 'smoke': {
        cone(dir, spread ?? 0.7, _v).multiplyScalar((sp ?? 0.7) * rand(0.4, 1.2));
        _p.copy(o3).add(_w.set(rand(-0.2, 0.2), rand(0, 0.2), rand(-0.2, 0.2)).multiplyScalar(s));
        this.put(this.alpha, _p, _v, rand(1.8, 3.0), 0.3 * s, 1.1 * s, C(0.2, 0.18, 0.16), 0.55, C(0.07, 0.07, 0.07), 1.0, -0.45, 0.7, 1.4, rand(-0.6, 0.6), 3, Floor.None, 0);
        break;
      }
      case 'frostMist': {
        _d.set(rand(-1, 1), rand(-0.1, 0.25), rand(-1, 1)).normalize();
        _v.copy(_d).multiplyScalar((sp ?? 1.2) * rand(0.3, 1));
        _p.copy(o3).addScaledVector(_d, 0.1 * s);
        this.put(this.alpha, _p, _v, rand(1.6, 2.8), 0.4 * s, 1.15 * s, C(0.62, 0.84, 0.95), 0.4, C(0.82, 0.95, 1.0), 1.3, 0.05, 0.45, 0.8, rand(-0.5, 0.5), 3, Floor.Hug, 0);
        break;
      }
      case 'iceGlitter': {
        cone(dir, spread ?? 1.4, _v).multiplyScalar((sp ?? 2.8) * rand(0.3, 1.2));
        _p.copy(o3).add(_w.set(rand(-0.25, 0.25), rand(0, 0.3), rand(-0.25, 0.25)).multiplyScalar(s));
        this.put(this.add, _p, _v, rand(0.9, 1.9), 0.08 * s, 0.04 * s, C(2.2, 3.0, 3.2), 1, C(0.4, 1.0, 1.6), 1.0, 3.0, 0.2, 0.3, rand(-4, 4), 2, Floor.Bounce, 1);
        break;
      }
      case 'summonSpiral': {
        const tint = e.tint ?? C(1.8, 1.5, 0.9);
        const a = Math.random() * 6.283;
        _p.copy(o3); _v.set(0, 0, 0);
        this.put(this.add, _p, _v, rand(0.9, 1.4), 0.09 * s, 0.03 * s, tint.clone().multiplyScalar(1.7), 1, tint.clone().multiplyScalar(0.35),
          0, 0, 0, 0, 0, 0, Floor.None, 0, [rand(5.5, 8.5), rand(0.45, 0.8) * s, rand(1.2, 2.2) * s, a]);
        break;
      }
      case 'dustPuff': {
        _d.set(rand(-1, 1), rand(0.05, 0.3), rand(-1, 1)).normalize();
        _v.copy(_d).multiplyScalar((sp ?? 1.4) * rand(0.4, 1));
        _p.copy(o3).add(_w.set(rand(-0.2, 0.2), 0.03, rand(-0.2, 0.2)).multiplyScalar(s));
        this.put(this.alpha, _p, _v, rand(0.7, 1.3), 0.25 * s, 0.75 * s, C(0.42, 0.37, 0.32), 0.42, C(0.3, 0.27, 0.24), 3, -0.2, 0.3, 1.0, rand(-0.8, 0.8), 3, Floor.Hug, 0);
        break;
      }
      case 'fireWave': {
        const speed = sp ?? 6;
        const front = speed * e.elapsed;
        _d.set(-dir.z, 0, dir.x).normalize().multiplyScalar(rand(-0.55, 0.55) * s * (spread ?? 1));
        _p.copy(o3).addScaledVector(dir, front).add(_d).y += 0.05;
        if (Math.random() < 0.22) {
          _v.set(rand(-0.3, 0.3), rand(0.8, 1.6), rand(-0.3, 0.3)).addScaledVector(dir, speed * 0.25);
          this.put(this.alpha, _p, _v, rand(0.9, 1.4), 0.3 * s, 0.85 * s, C(0.14, 0.1, 0.08), 0.5, C(0.05, 0.05, 0.05), 1, -0.5, 0.5, 1.2, 0, 3, Floor.None, 0);
        } else {
          _v.set(rand(-0.3, 0.3), rand(0.9, 2.0), rand(-0.3, 0.3)).addScaledVector(dir, speed * 0.3);
          this.put(this.add, _p, _v, rand(0.45, 0.85), 0.42 * s, 0.14 * s, C(3.2, 1.7, 0.4), 0.75, C(0.8, 0.12, 0.02), 1.3, -2.6, 0.4, 0.5, rand(-3, 3), 0, Floor.None, 0);
        }
        break;
      }
      case 'frostBeam': {
        const L = 4 * s, f = Math.random(), R = 0.5 * s * (1 - f * 0.85), ang = Math.random() * 6.283;
        _u.set(-dir.z, 0, dir.x); if (_u.lengthSq() < 1e-4) _u.set(1, 0, 0); _u.normalize();
        _w.crossVectors(dir, _u).normalize();
        _d.copy(_u).multiplyScalar(Math.cos(ang) * R).addScaledVector(_w, Math.sin(ang) * R);
        const life = rand(0.3, 0.55);
        _p.copy(o3).addScaledVector(dir, f * L).add(_d);
        _v.copy(dir).multiplyScalar((sp ?? 9) * rand(0.7, 1.2)).addScaledVector(_d, -1 / life);
        this.put(this.add, _p, _v, life, 0.09 * s, 0.025 * s, C(2.6, 3.4, 3.6), 1, C(0.3, 0.75, 1.4), 0, 0, 0, 0, rand(-3, 3), 0, Floor.None, 0);
        break;
      }
    }
  }
}
