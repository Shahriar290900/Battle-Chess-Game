// Tiny particle/mesh mock of FxApi for the sandbox (enough to judge timing and framing; the real fx comes from vfx).
import {
  AdditiveBlending, BufferAttribute, BufferGeometry, CircleGeometry, Color, ConeGeometry, CylinderGeometry, Mesh, MeshBasicMaterial,
  Object3D, Points, PointsMaterial, RingGeometry, Scene, Vector3,
} from 'three';
import type { WebGLRenderer, PerspectiveCamera } from 'three';
import type { EmitOptions, Faction, FxApi, ParticlePreset, PieceActor, QualityTier, ShatterOptions } from '../../src/contracts';
import type { SandboxActor } from './actor';

const MAX = 1500;
const STYLE: Record<ParticlePreset, { color: number; size: number; life: number; gravity: number; count: number; speed: number }> = {
  embers: { color: 0xff8a2a, size: 0.09, life: 1.1, gravity: -1.5, count: 20, speed: 2 },
  sparks: { color: 0xffd27a, size: 0.06, life: 0.6, gravity: 6, count: 20, speed: 5 },
  smoke: { color: 0x555555, size: 0.3, life: 1.6, gravity: -0.6, count: 8, speed: 0.8 },
  frostMist: { color: 0xcfeaff, size: 0.28, life: 1.4, gravity: -0.2, count: 10, speed: 0.8 },
  iceGlitter: { color: 0x9fefff, size: 0.07, life: 1.0, gravity: 1.5, count: 20, speed: 3 },
  summonSpiral: { color: 0xffffff, size: 0.1, life: 0.8, gravity: -2, count: 30, speed: 1.2 },
  dustPuff: { color: 0xb8a58a, size: 0.22, life: 0.7, gravity: -0.2, count: 6, speed: 1 },
  fireWave: { color: 0xff5a12, size: 0.2, life: 0.7, gravity: -0.5, count: 40, speed: 4 },
  frostBeam: { color: 0x66e6ff, size: 0.16, life: 0.5, gravity: 0, count: 40, speed: 8 },
};
const FC: Record<Faction, number> = { emberhold: 0xff7a1a, rime: 0x6ff3ff };

interface Emitter { preset: ParticlePreset; pos: Vector3; opts: EmitOptions; left: number; follow?: Object3D; acc: number }
interface Frag { obj: Object3D; v: Vector3; w: Vector3; age: number; onDone?: () => void; done: (v: void) => void; group: boolean }
interface Anim { t: number; dur: number; fn: (p: number) => void; end?: () => void }

export class SandboxFx implements FxApi {
  private pos = new Float32Array(MAX * 3); private col = new Float32Array(MAX * 3);
  private vel = new Float32Array(MAX * 3); private life = new Float32Array(MAX); private age = new Float32Array(MAX);
  private grav = new Float32Array(MAX); private next = 0;
  private points!: Points;
  private emitters: Emitter[] = [];
  private frags: Frag[] = [];
  private anims: Anim[] = [];
  private scene!: Scene;
  private trails = new Set<{ follow: Object3D; faction: Faction }>();
  log: string[] = [];

  async init(scene: Scene, _r: WebGLRenderer, _c: PerspectiveCamera) {
    this.scene = scene;
    const g = new BufferGeometry();
    g.setAttribute('position', new BufferAttribute(this.pos, 3));
    g.setAttribute('color', new BufferAttribute(this.col, 3));
    this.points = new Points(g, new PointsMaterial({ size: 0.14, vertexColors: true, transparent: true, depthWrite: false, blending: AdditiveBlending, sizeAttenuation: true }));
    this.points.frustumCulled = false;
    for (let i = 0; i < MAX; i++) { this.age[i] = 9; this.life[i] = 1; this.pos[i * 3 + 1] = -100; }
    scene.add(this.points);
  }
  setQuality(_t: QualityTier) {}

  private spawn(preset: ParticlePreset, p: Vector3, dir: Vector3 | undefined, spread: number, speed: number, scale: number) {
    const st = STYLE[preset];
    const i = this.next; this.next = (this.next + 1) % MAX;
    const d = new Vector3((Math.random() - 0.5), (Math.random() - 0.2), (Math.random() - 0.5)).normalize();
    if (dir) d.multiplyScalar(spread).add(dir.clone().normalize()).normalize();
    const s = speed * (0.4 + Math.random() * 0.8);
    this.pos.set([p.x, p.y, p.z], i * 3); this.vel.set([d.x * s, d.y * s, d.z * s], i * 3);
    const c = new Color(st.color).multiplyScalar(0.5 + scale * 0.5);
    this.col.set([c.r, c.g, c.b], i * 3);
    this.age[i] = 0; this.life[i] = st.life * (0.7 + Math.random() * 0.6); this.grav[i] = st.gravity;
  }
  emit(preset: ParticlePreset, position: Vector3, opts: EmitOptions = {}) {
    this.log.push('emit:' + preset);
    const st = STYLE[preset];
    if (opts.duration && opts.duration > 0) { this.emitters.push({ preset, pos: position.clone(), opts, left: opts.duration, follow: opts.follow, acc: 0 }); return; }
    const n = opts.count ?? st.count;
    for (let k = 0; k < n; k++) this.spawn(preset, position, opts.direction, opts.spread ?? 1, opts.speed ?? st.speed, opts.scale ?? 1);
  }
  private anim(dur: number, fn: (p: number) => void, end?: () => void) { this.anims.push({ t: 0, dur, fn, end }); }
  private disc<T extends Object3D>(m: T, dur: number, fade?: (p: number) => void) {
    this.scene.add(m); this.anim(dur, (p) => fade?.(p), () => this.scene.remove(m));
  }

  shatter(o: ShatterOptions): Promise<void> {
    this.log.push('shatter');
    this.scene.add(o.fragments);
    return new Promise((done) => {
      const kids = o.fragments.children.length ? [...o.fragments.children] : [o.fragments];
      for (const k of kids) {
        const out = k.position.clone().setY(0).normalize();
        const v = o.impulseDir.clone().multiplyScalar(2.5 * o.magnitude).addScaledVector(out, 1.5).add(new Vector3((Math.random() - 0.5) * 2, 2 + Math.random() * 3, (Math.random() - 0.5) * 2));
        if (o.cutNormal) v.addScaledVector(o.cutNormal, (k.position.dot(o.cutNormal) > 0 ? 1 : -1) * 1.5);
        this.frags.push({ obj: k, v, w: new Vector3(Math.random() * 8, Math.random() * 8, Math.random() * 8), age: 0, done, onDone: undefined, group: kids.length > 1 });
      }
      this.frags[this.frags.length - 1].onDone = () => { o.onDone?.(); };
    });
  }
  shockwave(position: Vector3, f: Faction, radius = 2) {
    const m = new Mesh(new RingGeometry(0.85, 1, 48), new MeshBasicMaterial({ color: FC[f], transparent: true, side: 2, depthWrite: false, blending: AdditiveBlending }));
    m.rotation.x = -Math.PI / 2; m.position.copy(position).setY(0.06);
    this.disc(m, 0.6, (p) => { m.scale.setScalar(0.2 + p * radius); (m.material as MeshBasicMaterial).opacity = 1 - p; });
  }
  async iceSpikes(position: Vector3, count = 6) {
    for (let i = 0; i < count; i++) {
      const c = new Mesh(new ConeGeometry(0.12, 1, 6), new MeshBasicMaterial({ color: 0x9fefff, transparent: true, opacity: 0.85 }));
      const a = (i / count) * Math.PI * 2;
      c.position.set(position.x + Math.cos(a) * 0.35, 0, position.z + Math.sin(a) * 0.35);
      this.scene.add(c);
      this.anim(1.4, (p) => { const s = p < 0.25 ? p / 0.25 : 1 - (p - 0.25) / 0.75; c.scale.set(1, 0.1 + s * 1.4, 1); c.position.y = c.scale.y * 0.5; }, () => this.scene.remove(c));
    }
  }
  trail(follow: Object3D, faction: Faction) {
    const t = { follow, faction }; this.trails.add(t);
    return { stop: () => { this.trails.delete(t); } };
  }
  async sweep(actor: PieceActor, kind: 'frost' | 'ember', duration: number) {
    const a = actor as SandboxActor; const c = new Color(kind === 'frost' ? 0xbfefff : 0xff6a10);
    await new Promise<void>((r) => this.anim(duration, (p) => a.tint(c, p), r));
  }
  async dissolve(obj: Object3D, _f: Faction, duration: number) {
    const s0 = obj.scale.x;
    await new Promise<void>((r) => this.anim(duration, (p) => obj.scale.setScalar(s0 * (1 - p)), r));
    obj.visible = false;
  }
  decal(position: Vector3, kind: 'crack' | 'scorch' | 'frost') {
    const m = new Mesh(new CircleGeometry(0.6, 24), new MeshBasicMaterial({ color: kind === 'scorch' ? 0x120a06 : kind === 'frost' ? 0xbfefff : 0x000000, transparent: true, opacity: 0.8, depthWrite: false }));
    m.rotation.x = -Math.PI / 2; m.position.copy(position).setY(0.03);
    this.disc(m, 4, (p) => { (m.material as MeshBasicMaterial).opacity = 0.8 * (1 - p); });
  }
  async column(position: Vector3, faction: Faction, duration: number) {
    const m = new Mesh(new CylinderGeometry(0.4, 0.5, 4, 16, 1, true), new MeshBasicMaterial({ color: FC[faction], transparent: true, opacity: 0.6, blending: AdditiveBlending, depthWrite: false, side: 2 }));
    m.position.set(position.x, 2, position.z);
    this.scene.add(m);
    await new Promise<void>((r) => this.anim(duration, (p) => { m.scale.set(1 + p * 0.3, 1, 1 + p * 0.3); (m.material as MeshBasicMaterial).opacity = 0.7 * (1 - p * p); }, r));
    this.scene.remove(m);
  }
  aura(position: Vector3, f: Faction) {
    const m = new Mesh(new RingGeometry(0.3, 0.38, 32), new MeshBasicMaterial({ color: FC[f], transparent: true, side: 2, blending: AdditiveBlending, depthWrite: false }));
    m.position.copy(position);
    this.disc(m, 0.9, (p) => { m.scale.setScalar(1 + p * 2.5); (m.material as MeshBasicMaterial).opacity = 1 - p; });
  }
  flash(actor: PieceActor) { (actor as SandboxActor).flash(); }
  mist() { for (let i = 0; i < 120; i++) this.spawn('smoke', new Vector3((Math.random() - 0.5) * 8, 0.2, (Math.random() - 0.5) * 8), undefined, 1, 0.6, 1); }

  update(dt: number) {
    // emitters
    for (const e of this.emitters) {
      e.left -= dt; e.acc += dt * 60;
      const p = e.follow ? e.follow.getWorldPosition(new Vector3()) : e.pos;
      const st = STYLE[e.preset];
      while (e.acc >= 1) { e.acc -= 1; this.spawn(e.preset, p, e.opts.direction, e.opts.spread ?? 1, e.opts.speed ?? st.speed, e.opts.scale ?? 1); if (Math.random() < 0.5) this.spawn(e.preset, p, e.opts.direction, e.opts.spread ?? 1, e.opts.speed ?? st.speed, e.opts.scale ?? 1); }
      if (!e.follow && e.opts.direction && e.opts.speed) e.pos.addScaledVector(e.opts.direction, e.opts.speed * dt);
    }
    this.emitters = this.emitters.filter((e) => e.left > 0);
    for (const t of this.trails) { const p = t.follow.getWorldPosition(new Vector3()); this.spawn(t.faction === 'emberhold' ? 'embers' : 'iceGlitter', p, undefined, 1, 0.3, 1); }
    // particles
    for (let i = 0; i < MAX; i++) {
      if (this.age[i] >= this.life[i]) { this.pos[i * 3 + 1] = -100; continue; }
      this.age[i] += dt;
      this.vel[i * 3 + 1] -= this.grav[i] * dt;
      this.pos[i * 3] += this.vel[i * 3] * dt; this.pos[i * 3 + 1] += this.vel[i * 3 + 1] * dt; this.pos[i * 3 + 2] += this.vel[i * 3 + 2] * dt;
    }
    (this.points.geometry.attributes.position as BufferAttribute).needsUpdate = true;
    (this.points.geometry.attributes.color as BufferAttribute).needsUpdate = true;
    // anims
    for (const a of this.anims) { a.t += dt; a.fn(Math.min(1, a.t / a.dur)); }
    this.anims = this.anims.filter((a) => { if (a.t >= a.dur) { a.end?.(); return false; } return true; });
    // fragments
    for (const f of this.frags) {
      f.age += dt;
      f.v.y -= 9 * dt;
      f.obj.position.addScaledVector(f.v, dt);
      if (f.obj.position.y < 0.05 && f.v.y < 0) { f.obj.position.y = 0.05; f.v.multiplyScalar(0.35); f.v.y = Math.abs(f.v.y) * 0.4; }
      f.obj.rotation.x += f.w.x * dt; f.obj.rotation.y += f.w.y * dt;
      if (f.age > 1.6) f.obj.scale.multiplyScalar(Math.max(0, 1 - dt * 3));
    }
    const dead = this.frags.filter((f) => f.age > 2.2);
    if (dead.length) {
      this.frags = this.frags.filter((f) => f.age <= 2.2);
      for (const f of dead) { f.onDone?.(); f.done(); }
    }
  }
}
