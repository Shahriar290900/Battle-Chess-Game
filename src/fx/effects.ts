import {
  AdditiveBlending, BufferAttribute, BufferGeometry, Color, ConeGeometry, DoubleSide, DynamicDrawUsage,
  IcosahedronGeometry, InstancedMesh, Matrix4, Mesh, NormalBlending, Object3D, PerspectiveCamera, PlaneGeometry,
  Quaternion, ShaderMaterial, SphereGeometry, Vector2, Vector3, CylinderGeometry, type IUniform,
} from 'three';
import type { Faction, PieceActor } from '../contracts';
import type { ParticleSystem } from './particles';
import { FX_COLORS, isLow, rand } from './common';
import { triggerBloomPulse } from './bloomBus';
import { NOISE_GLSL } from './shaders/glsl';

interface Active { update(dt: number): boolean; dispose(): void; }

const easeOutBack = (t: number, s = 2) => { t -= 1; return t * t * ((s + 1) * t + s) + 1; };
const easeOut = (t: number) => 1 - (1 - t) * (1 - t);
const smooth = (t: number) => t * t * (3 - 2 * t);
const clamp01 = (t: number) => Math.min(1, Math.max(0, t));

const RING_GEO = new PlaneGeometry(2, 2).rotateX(-Math.PI / 2);
const DOME_GEO = new SphereGeometry(1, 28, 12, 0, Math.PI * 2, 0, Math.PI / 2);
const SPIKE_GEO = new ConeGeometry(0.1, 1, 6, 1).translate(0, 0.5, 0);
const PILLAR_GEO = new CylinderGeometry(0.5, 0.58, 3.4, 28, 1, true).translate(0, 1.7, 0);
const COCOON_GEO = new IcosahedronGeometry(1, 1);
const MIST_GEO = new PlaneGeometry(10, 10).rotateX(-Math.PI / 2);
const DECAL_GEO = new PlaneGeometry(1, 1).rotateX(-Math.PI / 2);
for (const g of [RING_GEO, DOME_GEO, SPIKE_GEO, PILLAR_GEO, COCOON_GEO, MIST_GEO, DECAL_GEO]) g.userData.shared = true;

const col = (f: Faction) => (f === 'emberhold' ? FX_COLORS.emberhold.main : FX_COLORS.rime.hot);
const hot = (f: Faction) => (f === 'emberhold' ? FX_COLORS.emberhold.hot : FX_COLORS.rime.light);
const U = <T>(value: T): IUniform<T> => ({ value });

function fxMat(vs: string, fs: string, uniforms: Record<string, IUniform>, opts: { additive?: boolean; side?: number; depthWrite?: boolean } = {}): ShaderMaterial {
  return new ShaderMaterial({
    uniforms, vertexShader: vs, fragmentShader: fs, transparent: true,
    depthWrite: opts.depthWrite ?? false,
    blending: opts.additive === false ? NormalBlending : AdditiveBlending,
    side: (opts.side ?? DoubleSide) as any,
  });
}

// ---------------------------------------------------------------- shaders
const RING_VS = `varying vec2 vP; void main(){ vP = position.xz; gl_Position = projectionMatrix * modelViewMatrix * vec4(position,1.0); }`;
const RING_FS = `
varying vec2 vP; uniform float uP; uniform vec3 uCol; uniform vec3 uHot; uniform float uPow; uniform float uWidth;
void main(){
  float d = length(vP);
  float ringR = 1.0 - pow(1.0 - uP, 2.2);
  float w = mix(uWidth, uWidth * 2.2, uP);
  float band = exp(-pow((d - ringR) / w, 2.0));
  float tail = smoothstep(ringR, ringR - 0.45, d) * 0.22;
  float a = (band + tail) * pow(1.0 - uP, 1.4) * step(d, 1.0);
  vec3 c = mix(uCol, uHot, band * band);
  gl_FragColor = vec4(c * uPow, a);
}`;
const DOME_VS = `varying vec3 vN; varying vec3 vV; void main(){ vec4 mv = modelViewMatrix * vec4(position,1.0); vN = normalize(normalMatrix * normal); vV = normalize(-mv.xyz); gl_Position = projectionMatrix * mv; }`;
const DOME_FS = `
varying vec3 vN; varying vec3 vV; uniform float uP; uniform vec3 uCol; uniform float uPow;
void main(){ float f = pow(1.0 - abs(dot(normalize(vN), normalize(vV))), 2.2); float a = f * pow(1.0 - uP, 2.0) * 0.55; gl_FragColor = vec4(uCol * uPow, a); }`;
const SPIKE_VS = `
varying vec3 vN; varying vec3 vV; varying float vH;
void main(){
  mat4 im = mat4(1.0);
  #ifdef USE_INSTANCING
  im = instanceMatrix;
  #endif
  mat4 m = modelMatrix * im;
  vec4 mv = viewMatrix * m * vec4(position, 1.0);
  vN = normalize(mat3(viewMatrix) * mat3(m) * normal);
  vV = normalize(-mv.xyz);
  vH = position.y;
  gl_Position = projectionMatrix * mv;
}`;
const SPIKE_FS = `
varying vec3 vN; varying vec3 vV; varying float vH; uniform float uTime;
void main(){
  float f = pow(1.0 - abs(dot(normalize(vN), normalize(vV))), 1.6);
  vec3 deep = vec3(0.05, 0.28, 0.45); vec3 light = vec3(0.7, 0.93, 1.0);
  vec3 c = mix(deep, light, smoothstep(0.0, 1.0, vH) * 0.7 + f * 0.5);
  c += vec3(0.25, 0.95, 1.0) * (f * 1.1 + smoothstep(0.7, 1.0, vH) * 0.7);
  gl_FragColor = vec4(c, 0.92);
}`;
const TRAIL_VS = `varying float vV; varying float vU; void main(){ vU = uv.x; vV = uv.y; gl_Position = projectionMatrix * viewMatrix * vec4(position,1.0); }`;
const TRAIL_FS = `
varying float vV; varying float vU; uniform vec3 uHead; uniform vec3 uTail; uniform float uFade;
void main(){ float across = 1.0 - abs(vU * 2.0 - 1.0); float a = pow(1.0 - vV, 1.5) * (0.35 + 0.65 * across) * uFade; vec3 c = mix(uHead, uTail, smoothstep(0.0, 1.0, vV)); gl_FragColor = vec4(c, a); }`;
const DECAL_VS = `varying vec2 vUv; void main(){ vUv = uv * 2.0 - 1.0; gl_Position = projectionMatrix * modelViewMatrix * vec4(position,1.0); }`;
const DECAL_FS = `
varying vec2 vUv; uniform float uKind; uniform float uAge; uniform float uSeed;
${NOISE_GLSL}
void main(){
  vec2 p = vUv; float r = length(p);
  if (r > 1.0) discard;
  float edge = 1.0 - smoothstep(0.55, 1.0, r);
  float n1 = fxNoise(vec3(p * 4.5, uSeed)); float n2 = fxNoise(vec3(p * 10.0, uSeed + 7.0));
  float fade = 1.0 - smoothstep(0.5, 1.0, uAge);
  vec3 c; float a;
  if (uKind < 0.5) { // crack
    float l = max(1.0 - smoothstep(0.0, 0.05, abs(n1 - 0.5)), (1.0 - smoothstep(0.0, 0.035, abs(n2 - 0.5))) * 0.7);
    a = l * edge * 0.9; c = vec3(0.015, 0.012, 0.012) + vec3(0.9, 0.35, 0.08) * l * (1.0 - smoothstep(0.0, 0.2, uAge)) * 0.8;
  } else if (uKind < 1.5) { // scorch
    float blob = smoothstep(1.0, 0.1, r + (n1 - 0.5) * 0.5);
    float rim = smoothstep(0.55, 0.75, r + (n1 - 0.5) * 0.4) * (1.0 - smoothstep(0.75, 0.95, r + (n1 - 0.5) * 0.4));
    a = blob * 0.75; c = vec3(0.02, 0.016, 0.014) + vec3(3.0, 1.1, 0.2) * rim * (1.0 - smoothstep(0.0, 0.3, uAge));
  } else { // frost
    float ang = atan(p.y, p.x);
    float star = pow(abs(cos(ang * 3.0 + n1 * 1.4)), 6.0) * (1.0 - r);
    float fil = (1.0 - smoothstep(0.0, 0.08, abs(n2 - 0.5))) * 0.6;
    float m = clamp(star + fil * edge + smoothstep(0.8, 0.0, r) * 0.25 * n1, 0.0, 1.0);
    a = m * edge * 0.85; c = vec3(0.82, 0.94, 1.0) + vec3(0.1, 0.5, 0.6) * (1.0 - smoothstep(0.0, 0.25, uAge));
  }
  gl_FragColor = vec4(c, a * fade);
}`;
const PILLAR_VS = `varying vec3 vN; varying vec3 vV; varying vec3 vW; varying float vY; void main(){ vec4 w = modelMatrix * vec4(position,1.0); vW = w.xyz; vec4 mv = viewMatrix * w; vN = normalize(mat3(viewMatrix) * mat3(modelMatrix) * normal); vV = normalize(-mv.xyz); vY = position.y / 3.4; gl_Position = projectionMatrix * mv; }`;
const PILLAR_FS = `
varying vec3 vN; varying vec3 vV; varying vec3 vW; varying float vY; uniform float uTime; uniform float uGrow; uniform float uFade; uniform float uPow;
${NOISE_GLSL}
void main(){
  float fres = pow(abs(dot(normalize(vN), normalize(vV))), 0.8);
  float n = fxNoise(vec3(vW.x * 2.6, vW.y * 1.6 - uTime * 3.2, vW.z * 2.6)) * 0.65 + fxNoise(vec3(vW.x * 6.0, vW.y * 3.6 - uTime * 5.5, vW.z * 6.0)) * 0.35;
  float h = smoothstep(0.0, 0.08, vY) * pow(1.0 - vY, 0.7);
  float reveal = 1.0 - smoothstep(uGrow - 0.15, uGrow, vY);
  float a = smoothstep(0.25, 0.8, n + (1.0 - vY) * 0.25) * h * reveal * fres * uFade;
  vec3 c = mix(vec3(0.9, 0.18, 0.02), vec3(2.4, 1.35, 0.4), smoothstep(0.3, 0.9, n) * (1.0 - vY * 0.5));
  gl_FragColor = vec4(c * uPow, a);
}`;
const COCOON_VS = `varying vec3 vP; varying vec3 vN; void main(){ vec4 mv = modelViewMatrix * vec4(position,1.0); vP = mv.xyz; vN = normalize(normalMatrix * normal); gl_Position = projectionMatrix * mv; }`;
const COCOON_FS = `
varying vec3 vP; varying vec3 vN; uniform float uFade; uniform float uTime;
void main(){
  vec3 fn = normalize(cross(dFdx(vP), dFdy(vP)));
  vec3 V = normalize(-vP);
  float f = pow(1.0 - abs(dot(fn, V)), 1.7);
  float f2 = pow(1.0 - abs(dot(normalize(vN), V)), 2.0);
  vec3 c = mix(vec3(0.08, 0.32, 0.5), vec3(0.75, 0.95, 1.0), f * 0.55);
  c += vec3(0.25, 0.95, 1.0) * (f2 * 1.4 + 0.25 + 0.15 * sin(uTime * 4.0));
  gl_FragColor = vec4(c, (0.3 + f * 0.45 + f2 * 0.3) * uFade);
}`;
const MIST_VS = `varying vec2 vP; varying vec3 vW; void main(){ vec4 w = modelMatrix * vec4(position,1.0); vW = w.xyz; vP = position.xz / 5.0; gl_Position = projectionMatrix * viewMatrix * w; }`;
const MIST_FS = `
varying vec2 vP; varying vec3 vW; uniform float uTime; uniform float uFade; uniform vec2 uDir; uniform float uOct;
${NOISE_GLSL}
void main(){
  vec3 q = vec3(vW.xz * 0.45 + uDir * uTime, uTime * 0.12);
  float n = fxNoise(q) * 0.6 + fxNoise(q * 2.1 + 4.0) * 0.4;
  if (uOct > 2.5) n = n * 0.75 + fxNoise(q * 4.3 + 9.0) * 0.25;
  float edge = 1.0 - smoothstep(0.7, 1.0, length(vP));
  float a = smoothstep(0.32, 0.78, n) * 0.4 * edge * uFade;
  gl_FragColor = vec4(vec3(0.55, 0.58, 0.63), a);
}`;

// ---------------------------------------------------------------- manager
export class Effects {
  private active: Active[] = [];
  private decals: { mesh: Mesh; age: number; mat: ShaderMaterial }[] = [];
  private flashes: { mats: { m: any; emissive: Color; intensity: number }[]; frames: number }[] = [];
  private scene!: Object3D;
  camera!: PerspectiveCamera;
  private mistActive: { restart(): void } | null = null;

  constructor(private particles: ParticleSystem) {}

  init(root: Object3D, camera: PerspectiveCamera): void { this.scene = root; this.camera = camera; }

  update(dt: number): void {
    for (let i = this.active.length - 1; i >= 0; i--) {
      if (this.active[i].update(dt)) { this.active[i].dispose(); this.active.splice(i, 1); }
    }
    for (let i = this.decals.length - 1; i >= 0; i--) {
      const d = this.decals[i];
      d.age += dt / 4;
      d.mat.uniforms.uAge.value = d.age;
      if (d.age >= 1) { this.scene.remove(d.mesh); d.mat.dispose(); this.decals.splice(i, 1); }
    }
    for (let i = this.flashes.length - 1; i >= 0; i--) {
      const f = this.flashes[i];
      if (--f.frames <= 0) {
        for (const r of f.mats) { r.m.emissive.copy(r.emissive); r.m.emissiveIntensity = r.intensity; }
        this.flashes.splice(i, 1);
      }
    }
  }

  private run(a: Active): void { this.active.push(a); }

  // ---- ring / dome
  private ring(pos: Vector3, f: Faction, radius: number, duration: number, delay = 0, width = 0.07, pow = 2.1): void {
    const mat = fxMat(RING_VS, RING_FS, { uP: U(0), uCol: U(col(f).clone()), uHot: U(hot(f).clone()), uPow: U(pow), uWidth: U(width) });
    const mesh = new Mesh(RING_GEO, mat);
    mesh.position.set(pos.x, 0.04, pos.z); mesh.scale.setScalar(radius); mesh.renderOrder = 9; mesh.visible = delay <= 0;
    this.scene.add(mesh);
    let t = -delay;
    this.run({
      update: (dt) => { t += dt; mesh.visible = t >= 0; mat.uniforms.uP.value = clamp01(t / duration); return t >= duration; },
      dispose: () => { this.scene.remove(mesh); mat.dispose(); },
    });
  }

  shockwave(pos: Vector3, f: Faction, radius = 2.5): void {
    this.ring(pos, f, radius, 0.75);
    if (!isLow()) {
      const mat = fxMat(DOME_VS, DOME_FS, { uP: U(0), uCol: U(col(f).clone()), uPow: U(2.2) });
      const dome = new Mesh(DOME_GEO, mat);
      dome.position.set(pos.x, 0.02, pos.z); dome.renderOrder = 9;
      this.scene.add(dome);
      let t = 0;
      this.run({
        update: (dt) => { t += dt; const p = clamp01(t / 0.6); mat.uniforms.uP.value = p; dome.scale.set(radius * easeOut(p), radius * 0.4 * easeOut(p), radius * easeOut(p)); return p >= 1; },
        dispose: () => { this.scene.remove(dome); mat.dispose(); },
      });
    }
    triggerBloomPulse(0.5, 0.25);
  }

  aura(pos: Vector3, f: Faction): void {
    this.ring(pos, f, 1.35, 0.9, 0, 0.1, 3.2);
    this.ring(pos, f, 1.35, 0.9, 0.35, 0.1, 3.2);
    if (!isLow()) this.ring(pos, f, 1.35, 0.9, 0.7, 0.1, 3.2);
    triggerBloomPulse(0.35, 0.4);
  }

  // ---- ice spikes
  iceSpikes(pos: Vector3, count?: number): Promise<void> {
    const n = Math.max(1, Math.round((count ?? 7) * (isLow() ? 0.6 : 1)));
    const mat = fxMat(SPIKE_VS, SPIKE_FS, { uTime: U(0) }, { additive: false, depthWrite: true });
    const mesh = new InstancedMesh(SPIKE_GEO, mat, n);
    mesh.instanceMatrix.setUsage(DynamicDrawUsage);
    mesh.frustumCulled = false; mesh.renderOrder = 8;
    mesh.position.set(pos.x, 0, pos.z);
    this.scene.add(mesh);
    const cfg = Array.from({ length: n }, (_, i) => {
      const ang = i * 2.399 + Math.random() * 0.4;
      const r = i === 0 ? 0.05 : rand(0.2, 0.85);
      const h = i === 0 ? rand(1.3, 1.7) : rand(0.55, 1.25) * (1.1 - r * 0.4);
      return { x: Math.cos(ang) * r, z: Math.sin(ang) * r, ang, h, w: rand(0.9, 1.5), lean: i === 0 ? 0 : rand(0.15, 0.4), delay: i * 0.045 };
    });
    const GROW = 0.45, HOLD = 1.7, SHRINK = 0.3;
    const m = new Matrix4(), q = new Quaternion(), p = new Vector3(), s = new Vector3(), axis = new Vector3();
    let t = 0;
    this.particles.emit('iceGlitter', new Vector3(pos.x, 0.3, pos.z), { count: 26, scale: 1.2 });
    return new Promise<void>((resolve) => {
      let resolved = false;
      this.run({
        update: (dt) => {
          t += dt;
          for (let i = 0; i < n; i++) {
            const c = cfg[i];
            const g = clamp01((t - c.delay) / GROW);
            const sh = clamp01((t - HOLD - c.delay) / SHRINK);
            const k = (g > 0 ? easeOutBack(g, 2) : 0) * (1 - smooth(sh));
            axis.set(-Math.sin(c.ang + Math.PI / 2) * 0 + Math.cos(c.ang + Math.PI / 2), 0, Math.sin(c.ang + Math.PI / 2)).normalize();
            q.setFromAxisAngle(axis, c.lean);
            p.set(c.x, 0, c.z);
            s.set(c.w * Math.max(0.0001, k), c.h * Math.max(0.0001, k), c.w * Math.max(0.0001, k));
            m.compose(p, q, s);
            mesh.setMatrixAt(i, m);
          }
          mesh.instanceMatrix.needsUpdate = true;
          if (!resolved && t >= GROW + cfg[n - 1].delay) { resolved = true; resolve(); }
          return t >= HOLD + SHRINK + cfg[n - 1].delay;
        },
        dispose: () => { this.scene.remove(mesh); mat.dispose(); mesh.dispose(); if (!resolved) resolve(); },
      });
    });
  }

  // ---- trail
  trail(follow: Object3D, f: Faction): { stop(): void } {
    const N = 12;
    const geo = new BufferGeometry();
    const pos = new Float32Array(N * 2 * 3);
    const uv = new Float32Array(N * 2 * 2);
    const idx: number[] = [];
    for (let i = 0; i < N; i++) {
      uv.set([0, i / (N - 1), 1, i / (N - 1)], i * 4);
      if (i < N - 1) { const a = i * 2; idx.push(a, a + 1, a + 2, a + 1, a + 3, a + 2); }
    }
    const pa = new BufferAttribute(pos, 3); pa.setUsage(DynamicDrawUsage);
    geo.setAttribute('position', pa); geo.setAttribute('uv', new BufferAttribute(uv, 2)); geo.setIndex(idx);
    const head = f === 'emberhold' ? new Color(4.0, 2.2, 0.5) : new Color(2.6, 3.6, 3.9);
    const tail = f === 'emberhold' ? new Color(1.0, 0.18, 0.02) : new Color(0.2, 0.6, 1.3);
    const mat = fxMat(TRAIL_VS, TRAIL_FS, { uHead: U(head), uTail: U(tail), uFade: U(1) }, { side: DoubleSide });
    const mesh = new Mesh(geo, mat);
    mesh.frustumCulled = false; mesh.renderOrder = 13;
    this.scene.add(mesh);
    const hist: Vector3[] = [];
    const cur = new Vector3(); follow.getWorldPosition(cur);
    for (let i = 0; i < N; i++) hist.push(cur.clone());
    let stopping = false, fade = 1;
    const cam = new Vector3(), tan = new Vector3(), toCam = new Vector3(), side = new Vector3(), lastSide = new Vector3(0, 1, 0);
    const width = 0.1;
    this.run({
      update: (dt) => {
        if (!stopping) { follow.getWorldPosition(cur); hist.unshift(hist.pop()!.copy(cur)); }
        else { hist.unshift(hist.pop()!.copy(hist[0])); fade -= dt / 0.25; mat.uniforms.uFade.value = Math.max(0, fade); }
        this.camera.getWorldPosition(cam);
        for (let i = 0; i < N; i++) {
          const a = hist[Math.max(0, i - 1)], b = hist[Math.min(N - 1, i + 1)];
          tan.copy(a).sub(b);
          toCam.copy(cam).sub(hist[i]);
          side.crossVectors(tan, toCam);
          if (side.lengthSq() < 1e-10) side.copy(lastSide); else { side.normalize(); lastSide.copy(side); }
          const w = width * (1 - i / (N - 1)) * 0.5;
          const o = i * 6;
          pos[o] = hist[i].x - side.x * w; pos[o + 1] = hist[i].y - side.y * w; pos[o + 2] = hist[i].z - side.z * w;
          pos[o + 3] = hist[i].x + side.x * w; pos[o + 4] = hist[i].y + side.y * w; pos[o + 5] = hist[i].z + side.z * w;
        }
        pa.needsUpdate = true;
        return stopping && fade <= 0;
      },
      dispose: () => { this.scene.remove(mesh); geo.dispose(); mat.dispose(); },
    });
    return { stop() { stopping = true; } };
  }

  // ---- decal
  decal(pos: Vector3, kind: 'crack' | 'scorch' | 'frost'): void {
    const mat = fxMat(DECAL_VS, DECAL_FS, { uKind: U(kind === 'crack' ? 0 : kind === 'scorch' ? 1 : 2), uAge: U(0), uSeed: U(Math.random() * 50) }, { additive: false });
    mat.polygonOffset = true; mat.polygonOffsetFactor = -2; mat.polygonOffsetUnits = -2;
    const mesh = new Mesh(DECAL_GEO, mat);
    mesh.position.set(pos.x, 0.002, pos.z);
    mesh.rotation.y = Math.random() * 6.283;
    mesh.scale.setScalar(kind === 'scorch' ? 1.5 : kind === 'frost' ? 1.6 : 1.7);
    mesh.renderOrder = 2;
    this.scene.add(mesh);
    this.decals.push({ mesh, age: 0, mat });
    while (this.decals.length > 24) { const d = this.decals.shift()!; this.scene.remove(d.mesh); d.mat.dispose(); }
  }

  // ---- column
  column(pos: Vector3, f: Faction, duration: number): Promise<void> {
    const base = new Vector3(pos.x, 0, pos.z);
    this.ring(base, f, 2.0, 0.8);
    triggerBloomPulse(0.6, 0.5);
    if (f === 'emberhold') {
      const mats = [0, 1].map((i) => fxMat(PILLAR_VS, PILLAR_FS, { uTime: U(0), uGrow: U(0), uFade: U(0), uPow: U(i ? 1.4 : 1.0) }, { side: DoubleSide }));
      const outer = new Mesh(PILLAR_GEO, mats[0]); const inner = new Mesh(PILLAR_GEO, mats[1]);
      inner.scale.set(0.55, 1, 0.55);
      for (const m of [outer, inner]) { m.position.copy(base); m.renderOrder = 10; this.scene.add(m); }
      this.particles.emit('embers', new Vector3(base.x, 0.2, base.z), { count: 70, duration: Math.max(0.3, duration - 0.3), spread: 0.35, speed: 2.4, scale: 1.2 });
      let t = 0;
      return new Promise<void>((resolve) => this.run({
        update: (dt) => {
          t += dt;
          const grow = clamp01(t / 0.35), fade = Math.min(smooth(clamp01(t / 0.2)), 1 - smooth(clamp01((t - (duration - 0.45)) / 0.45)));
          for (const m of mats) { m.uniforms.uTime.value = t; m.uniforms.uGrow.value = easeOut(grow) * 1.2; m.uniforms.uFade.value = fade; }
          return t >= duration;
        },
        dispose: () => { this.scene.remove(outer, inner); mats.forEach((m) => m.dispose()); resolve(); },
      }));
    }
    const mat = fxMat(COCOON_VS, COCOON_FS, { uFade: U(0), uTime: U(0) }, { side: DoubleSide });
    const shell = new Mesh(COCOON_GEO, mat);
    shell.position.set(base.x, 0.85, base.z); shell.renderOrder = 10;
    this.scene.add(shell);
    void this.iceSpikes(base, 6);
    this.particles.emit('frostMist', new Vector3(base.x, 0.15, base.z), { count: 20, scale: 1.2 });
    let t = 0, burst = false;
    return new Promise<void>((resolve) => this.run({
      update: (dt) => {
        t += dt;
        const g = clamp01(t / 0.5);
        const brk = clamp01((t - (duration - 0.3)) / 0.3);
        const sc = (g > 0 ? easeOutBack(g, 1.6) : 0) * (1 + brk * 0.45);
        shell.scale.set(0.62 * sc, 1.05 * sc, 0.62 * sc);
        shell.rotation.y += dt * 0.6;
        mat.uniforms.uFade.value = smooth(clamp01(t / 0.25)) * (1 - brk);
        mat.uniforms.uTime.value = t;
        if (!burst && t >= duration - 0.3) {
          burst = true;
          this.particles.emit('iceGlitter', new Vector3(base.x, 0.9, base.z), { count: 60, spread: 1.6, speed: 4 });
          this.particles.emit('frostMist', new Vector3(base.x, 0.7, base.z), { count: 20, scale: 1.3 });
          triggerBloomPulse(0.8, 0.35);
        }
        return t >= duration;
      },
      dispose: () => { this.scene.remove(shell); mat.dispose(); resolve(); },
    }));
  }

  // ---- mist
  mist(): void {
    if (this.mistActive) { this.mistActive.restart(); return; }
    const layers = (isLow() ? [0.25] : [0.16, 0.42]).map((y, i) => {
      const mat = fxMat(MIST_VS, MIST_FS, { uTime: U(i * 7), uFade: U(0), uDir: U(new Vector2(0.07 * (i ? -1 : 1), 0.035)), uOct: U(isLow() ? 2 : 3) }, { additive: false });
      const mesh = new Mesh(MIST_GEO, mat); mesh.position.y = y; mesh.renderOrder = 7;
      this.scene.add(mesh);
      return { mat, mesh };
    });
    let t = 0; const TOTAL = 9;
    const self = { restart: () => { t = Math.min(t, 1.5); } };
    this.mistActive = self;
    this.run({
      update: (dt) => {
        t += dt;
        const fade = smooth(clamp01(t / 1.6)) * (1 - smooth(clamp01((t - (TOTAL - 1.6)) / 1.6)));
        layers.forEach((l) => { l.mat.uniforms.uTime.value += dt; l.mat.uniforms.uFade.value = fade; });
        return t >= TOTAL;
      },
      dispose: () => { layers.forEach((l) => { this.scene.remove(l.mesh); l.mat.dispose(); }); this.mistActive = null; },
    });
    this.particles.emit('dustPuff', new Vector3(0, 0.3, 0), { count: 10, scale: 3, speed: 1.2 });
  }

  // ---- flash
  flash(actor: PieceActor): void {
    const recs: { m: any; emissive: Color; intensity: number }[] = [];
    const seen = new Set<any>();
    const tint = actor.faction === 'emberhold' ? new Color(1.0, 0.6, 0.25) : new Color(0.55, 0.95, 1.0);
    for (const mesh of actor.meshes) {
      const list = Array.isArray(mesh.material) ? mesh.material : [mesh.material];
      for (const m of list as any[]) {
        if (!m || seen.has(m) || !m.emissive) continue;
        seen.add(m);
        recs.push({ m, emissive: m.emissive.clone(), intensity: m.emissiveIntensity ?? 1 });
        m.emissive.copy(tint); m.emissiveIntensity = 3.2;
      }
    }
    this.flashes.push({ mats: recs, frames: 3 });
    triggerBloomPulse(1.4, 0.35);
  }

  dispose(): void { this.active.forEach((a) => a.dispose()); this.active = []; }
}
