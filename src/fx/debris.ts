import RAPIER from '@dimforge/rapier3d-compat';
import { Box3, Material, Matrix4, Mesh, Object3D, Quaternion, Scene, Vector3 } from 'three';
import { bus, ROLE_HEIGHT, type Faction, type GraphicsSettings, type PieceActor, type ShatterOptions } from '../contracts';
import type { ParticleSystem } from './particles';
import { makeDissolveMaterial, type DissolveHandle } from './shaders/dissolve';
import { fxState, rand } from './common';
import { triggerBloomPulse } from './bloomBus';

// Rapier debris. Fixed 1/120 s steps driven by the (already time-scaled) dt through an accumulator, with pose
// interpolation so hit-stop / slow-mo stay smooth. Convex-hull colliders per fragment (cached per fragment set),
// density/friction/restitution by faction material. 'full' adds standing-piece kinematic colliders, fragment-fragment
// collisions, the board frame, and impacts that wake nearby sleeping debris. 'simple' is floor-only with merged shards.

const STEP = 1 / 120;
const MAX_SUBSTEPS = 6;
const MIN_LIFE = 1.1;     // earliest dissolve (after everyone is at rest)
const MAX_LIFE = 2.4;     // latest dissolve
const DISSOLVE = 0.6;
const SINK = 0.2;
const GRAVITY = -16;

// collision layers
const L_FLOOR = 0x1, L_FRAG = 0x2, L_PIECE = 0x4, L_EDGE = 0x8;
const groups = (member: number, filter: number) => (member << 16) | filter;

const MATERIAL: Record<Faction, { density: number; friction: number; restitution: number; speed: number; drag: number }> = {
  emberhold: { density: 2.6, friction: 0.85, restitution: 0.16, speed: 0.92, drag: 0.35 }, // bronze / stone: heavy, thuds
  rime: { density: 0.95, friction: 0.22, restitution: 0.42, speed: 1.12, drag: 0.15 },     // ice: light, slides and bounces
};

interface Merged { unit: Object3D; parent: Object3D | null; pos: Vector3; quat: Quaternion; scale: Vector3; visible: boolean }
interface Frag {
  unit: Object3D; meshes: Mesh[]; origMats: Mesh['material'][]; body: RAPIER.RigidBody; collider: RAPIER.Collider;
  origParent: Object3D | null; origPos: Vector3; origQuat: Quaternion; origScale: Vector3; origVisible: boolean;
  merged: Merged[]; sinkY0: number;
  p0: Vector3; q0: Quaternion; p1: Vector3; q1: Quaternion; lastVy: number; asleepFor: number;
}
interface Kin { actor: PieceActor; body: RAPIER.RigidBody }
interface DebrisGroup {
  frags: Frag[]; t: number; faction: Faction; dissolving: boolean; handles: DissolveHandle[]; kin: Kin[];
  full: boolean; fragFragOn: boolean; dissolveStart?: number; onDone?: () => void; resolve: () => void;
}

const _q = new Quaternion();

export class Debris {
  private world: RAPIER.World | null = null;
  private scene!: Scene;
  private groups: DebrisGroup[] = [];
  private ready = false;
  private acc = 0;
  private mode: GraphicsSettings['physics'] = 'full';
  private statics: PieceActor[] = [];
  private hullCache = new Map<string, Float32Array | null>();
  private lastImpact = -1;
  onBeforeShatter?: (actor: PieceActor) => void;

  constructor(private particles: ParticleSystem) {}

  setMode(m: GraphicsSettings['physics']): void { this.mode = m; }
  setStaticActors(a: PieceActor[]): void { this.statics = a; }
  get activeBodies(): number { return this.groups.reduce((n, g) => n + (g.dissolving ? 0 : g.frags.length), 0); }

  async init(scene: Scene): Promise<void> {
    this.scene = scene;
    await RAPIER.init();
    const w = new RAPIER.World({ x: 0, y: GRAVITY, z: 0 });
    w.timestep = STEP;
    const fixed = (x: number, y: number, z: number, hx: number, hy: number, hz: number, member: number, filter: number, fr = 0.6, re = 0.25) => {
      const b = w.createRigidBody(RAPIER.RigidBodyDesc.fixed().setTranslation(x, y, z));
      w.createCollider(RAPIER.ColliderDesc.cuboid(hx, hy, hz).setFriction(fr).setRestitution(re).setCollisionGroups(groups(member, filter)), b);
    };
    fixed(0, -0.5, 0, 5, 0.5, 5, L_FLOOR, 0xffff, 0.9, 0.2);                    // floor, top at y = 0
    // board frame / lip (8x8 board centred at origin)
    fixed(0, 0.18, 4.25, 4.5, 0.18, 0.25, L_EDGE, L_FRAG); fixed(0, 0.18, -4.25, 4.5, 0.18, 0.25, L_EDGE, L_FRAG);
    fixed(4.25, 0.18, 0, 0.25, 0.18, 4.0, L_EDGE, L_FRAG); fixed(-4.25, 0.18, 0, 0.25, 0.18, 4.0, L_EDGE, L_FRAG);
    this.world = w;
    this.ready = true;
  }

  // ------------------------------------------------------------------ shatter
  shatter(o: ShatterOptions): Promise<void> {
    const { actor, fragments, impulseDir, magnitude, cutNormal, onDone } = o;
    this.onBeforeShatter?.(actor);
    const faction = actor.faction;
    const world = this.world;
    const full = this.mode === 'full';
    const mat = MATERIAL[faction];
    actor.root.visible = false;

    const centre = new Vector3(); actor.root.getWorldPosition(centre);
    const burstPos = centre.clone(); burstPos.y += 0.6;
    const dir = impulseDir.clone().normalize();
    if (faction === 'emberhold') {
      this.particles.emit('sparks', burstPos, { count: 44, direction: dir.clone().setY(0.5).normalize(), spread: 1.1, speed: 5.5 });
      this.particles.emit('smoke', burstPos, { count: 14, scale: 1.1 });
      this.particles.emit('embers', burstPos, { count: 28 });
    } else {
      this.particles.emit('frostMist', burstPos, { count: 24, scale: 1.1 });
      this.particles.emit('iceGlitter', burstPos, { count: 54, spread: 1.4, speed: 3 });
    }
    triggerBloomPulse(0.6 + magnitude * 0.3, 0.3);

    fragments.updateWorldMatrix(true, true);
    let units: Object3D[] = [];
    fragments.traverse((c) => { if (c !== fragments && /^frag_\d+$/.test(c.name)) units.push(c); });
    if (!units.length) fragments.traverse((c) => { if ((c as Mesh).isMesh) units.push(c); });
    const meshesOf = (u: Object3D): Mesh[] => { const r: Mesh[] = []; u.traverse((c) => { if ((c as Mesh).isMesh) r.push(c as Mesh); }); return r; };

    return new Promise<void>((resolve) => {
      if (!this.ready || !world || !units.length) { onDone?.(); resolve(); return; }
      const g: DebrisGroup = { frags: [], t: 0, faction, dissolving: false, handles: [], kin: [], full, fragFragOn: !full, onDone, resolve };
      const wp = new Vector3(), ws = new Vector3(), wq = new Quaternion();
      const box = new Box3(), mb = new Box3(), inv = new Matrix4(), rel = new Matrix4(), bc = new Vector3(), bs = new Vector3();

      // 'simple': merge the smallest shards into their nearest big neighbour (fewer bodies)
      const mergedInto = new Map<Object3D, Merged[]>();
      if (!full && units.length > 8) {
        const vol = (u: Object3D) => { const b = new Box3().setFromObject(u); const s = b.getSize(new Vector3()); return s.x * s.y * s.z; };
        const sorted = units.map((u) => ({ u, v: vol(u) })).sort((a, b) => b.v - a.v);
        const keep = sorted.slice(0, Math.ceil(units.length * 0.55)).map((x) => x.u);
        const keepC = keep.map((u) => new Box3().setFromObject(u).getCenter(new Vector3()));
        for (const { u } of sorted.slice(keep.length)) {
          const c = new Box3().setFromObject(u).getCenter(new Vector3());
          let bi = 0, bd = Infinity;
          keepC.forEach((k, i) => { const d = k.distanceToSquared(c); if (d < bd) { bd = d; bi = i; } });
          const host = keep[bi];
          const rec: Merged = { unit: u, parent: u.parent, pos: u.position.clone(), quat: u.quaternion.clone(), scale: u.scale.clone(), visible: u.visible };
          host.attach(u);
          (mergedInto.get(host) ?? mergedInto.set(host, []).get(host)!).push(rec);
        }
        units = keep;
      }

      const cacheKey = `${actor.id}|${units.length}|${full ? 'f' : 's'}`;
      const burstP = burstPos;
      const n = cutNormal ? cutNormal.clone().normalize() : null;
      const fragFilter = full ? (L_FLOOR | L_PIECE | L_EDGE) : (L_FLOOR | L_EDGE * 0); // frag-frag enabled shortly after spawn in full mode

      for (const m of units) {
        m.updateWorldMatrix(true, true);
        m.matrixWorld.decompose(wp, wq, ws);
        const sub = meshesOf(m);
        const f: Frag = {
          unit: m, meshes: sub, origMats: sub.map((x) => x.material), body: null as unknown as RAPIER.RigidBody, collider: null as unknown as RAPIER.Collider,
          origParent: m.parent, origPos: m.position.clone(), origQuat: m.quaternion.clone(), origScale: m.scale.clone(), origVisible: m.visible,
          merged: mergedInto.get(m) ?? [], sinkY0: 0, p0: new Vector3(), q0: new Quaternion(), p1: new Vector3(), q1: new Quaternion(), lastVy: 0, asleepFor: 0,
        };
        // hull points in the unit's local (scaled) frame
        const key = `${cacheKey}|${m.name}`;
        let pts = this.hullCache.get(key);
        if (pts === undefined) {
          inv.copy(m.matrixWorld).invert();
          pts = this.hullPoints(sub, inv, ws, rel);
          this.hullCache.set(key, pts);
        }
        box.makeEmpty();
        for (const sm of sub) {
          if (!sm.geometry.boundingBox) sm.geometry.computeBoundingBox();
          inv.copy(m.matrixWorld).invert(); rel.multiplyMatrices(inv, sm.matrixWorld);
          box.union(mb.copy(sm.geometry.boundingBox!).applyMatrix4(rel));
        }
        if (box.isEmpty()) box.set(new Vector3(-0.05, -0.05, -0.05), new Vector3(0.05, 0.05, 0.05));
        box.getCenter(bc); box.getSize(bs); bc.multiply(ws); bs.multiply(ws);

        this.scene.attach(m);
        m.visible = true;
        const body = world.createRigidBody(
          RAPIER.RigidBodyDesc.dynamic().setTranslation(wp.x, wp.y, wp.z).setRotation({ x: wq.x, y: wq.y, z: wq.z, w: wq.w })
            .setLinearDamping(mat.drag).setAngularDamping(0.5).setCcdEnabled(true));
        let desc: RAPIER.ColliderDesc | null = pts ? RAPIER.ColliderDesc.convexHull(pts) : null;
        if (!desc) desc = RAPIER.ColliderDesc.cuboid(Math.max(0.012, Math.abs(bs.x) / 2), Math.max(0.012, Math.abs(bs.y) / 2), Math.max(0.012, Math.abs(bs.z) / 2)).setTranslation(bc.x, bc.y, bc.z);
        const collider = world.createCollider(
          desc.setDensity(mat.density).setFriction(mat.friction).setRestitution(mat.restitution)
            .setCollisionGroups(groups(L_FRAG, full ? fragFilter : L_FLOOR)), body);
        f.body = body; f.collider = collider;

        const fc = bc.clone().applyQuaternion(wq).add(wp);
        const radial = fc.clone().sub(burstP);
        if (radial.lengthSq() > 1e-6) radial.normalize();
        const v = dir.clone().multiplyScalar(magnitude * rand(3.4, 6.6) * mat.speed)
          .addScaledVector(radial, rand(0.6, 1.8) * (0.7 + magnitude * 0.3));
        v.y += rand(0.5, 1.8);
        if (Math.random() < 0.18) v.y += rand(2.5, 4.5) * (0.7 + magnitude * 0.4);
        if (n) v.addScaledVector(n, (radial.dot(n) >= 0 ? 1 : -1) * (2.2 + magnitude * 1.4));
        body.setLinvel({ x: v.x, y: v.y, z: v.z }, true);
        const tq = 6 + magnitude * 4;
        body.setAngvel({ x: rand(-tq, tq), y: rand(-tq, tq), z: rand(-tq, tq) }, true);
        f.p0.copy(wp); f.p1.copy(wp); f.q0.copy(wq); f.q1.copy(wq);
        g.frags.push(f);
      }

      if (full) {
        this.addKinematics(g, actor, centre);
        this.wakeNearby(burstP, magnitude);
      }
      this.groups.push(g);
    });
  }

  /** Extreme points along 26 directions plus strided fill, in the unit's scaled local frame. */
  private hullPoints(sub: Mesh[], inv: Matrix4, ws: Vector3, rel: Matrix4): Float32Array | null {
    const all: Vector3[] = [];
    for (const sm of sub) {
      const pa = sm.geometry.getAttribute('position');
      if (!pa) continue;
      rel.multiplyMatrices(inv, sm.matrixWorld);
      const stride = Math.max(1, Math.floor(pa.count / 400));
      for (let i = 0; i < pa.count; i += stride) all.push(new Vector3().fromBufferAttribute(pa, i).applyMatrix4(rel).multiply(ws));
    }
    if (all.length < 4) return null;
    const dirs: Vector3[] = [];
    for (let x = -1; x <= 1; x++) for (let y = -1; y <= 1; y++) for (let z = -1; z <= 1; z++) if (x || y || z) dirs.push(new Vector3(x, y, z).normalize());
    const picked = new Set<number>();
    for (const d of dirs) { let bi = 0, bv = -Infinity; all.forEach((p, i) => { const v = p.dot(d); if (v > bv) { bv = v; bi = i; } }); picked.add(bi); }
    const fill = Math.max(1, Math.floor(all.length / 24));
    for (let i = 0; i < all.length; i += fill) picked.add(i);
    const out = new Float32Array(picked.size * 3);
    let k = 0;
    picked.forEach((i) => { out[k++] = all[i].x; out[k++] = all[i].y; out[k++] = all[i].z; });
    return out;
  }

  private addKinematics(g: DebrisGroup, self: PieceActor, centre: Vector3): void {
    const w = this.world!;
    const p = new Vector3();
    for (const a of this.statics) {
      if (a === self || !a.root.visible || !a.root.parent) continue;
      a.root.getWorldPosition(p);
      if (p.distanceTo(centre) > 3.6) continue;
      const h = ROLE_HEIGHT[a.role] ?? 1.2;
      const body = w.createRigidBody(RAPIER.RigidBodyDesc.kinematicPositionBased().setTranslation(p.x, h / 2, p.z));
      w.createCollider(RAPIER.ColliderDesc.cylinder(h / 2, 0.34).setFriction(0.6).setRestitution(0.3).setCollisionGroups(groups(L_PIECE, L_FRAG)), body);
      g.kin.push({ actor: a, body });
    }
  }

  /** The new burst shoves nearby resting debris from earlier shatters. */
  private wakeNearby(pos: Vector3, magnitude: number): void {
    for (const g of this.groups) {
      if (g.dissolving) continue;
      for (const f of g.frags) {
        const t = f.body.translation();
        const dx = t.x - pos.x, dy = t.y - pos.y, dz = t.z - pos.z;
        const d = Math.hypot(dx, dy, dz);
        if (d > 1.8 || d < 1e-3) continue;
        const k = (1 - d / 1.8) * (1.5 + magnitude * 1.5) * f.body.mass();
        f.body.applyImpulse({ x: (dx / d) * k, y: (dy / d) * k + 0.6 * k, z: (dz / d) * k }, true);
      }
    }
  }

  // ------------------------------------------------------------------ simulation
  update(dt: number): void {
    const w = this.world;
    if (!w || !this.groups.length || dt <= 0) return;
    this.acc = Math.min(this.acc + dt, STEP * MAX_SUBSTEPS);
    while (this.acc >= STEP) {
      for (const g of this.groups) {
        for (const f of g.frags) if (!g.dissolving) { f.p0.copy(f.p1); f.q0.copy(f.q1); }
        for (const k of g.kin) { k.actor.root.getWorldPosition(_p); k.body.setNextKinematicTranslation({ x: _p.x, y: k.body.translation().y, z: _p.z }); }
      }
      w.step();
      this.acc -= STEP;
      for (const g of this.groups) {
        g.t += STEP; // group time advances in simulated time
        if (g.dissolving) continue;
        if (g.full && !g.fragFragOn && g.t > 0.14) { g.fragFragOn = true; for (const f of g.frags) f.collider.setCollisionGroups(groups(L_FRAG, L_FLOOR | L_FRAG | L_PIECE | L_EDGE)); }
        for (const f of g.frags) {
          const tr = f.body.translation(), r = f.body.rotation();
          f.p1.set(tr.x, tr.y, tr.z); f.q1.set(r.x, r.y, r.z, r.w);
          const vy = f.body.linvel().y;
          if (f.lastVy < -1.6 && vy > f.lastVy + 1.2) this.impact(g.faction, Math.min(1, -f.lastVy / 8), f.p1);
          f.lastVy = vy;
        }
      }
    }
    const alpha = this.acc / STEP;
    for (let gi = this.groups.length - 1; gi >= 0; gi--) {
      const g = this.groups[gi];
      if (!g.dissolving) {
        let allSleep = true;
        for (const f of g.frags) {
          f.unit.position.lerpVectors(f.p0, f.p1, alpha);
          f.unit.quaternion.slerpQuaternions(f.q0, f.q1, alpha);
          if (!f.body.isSleeping()) allSleep = false;
        }
        if ((allSleep && g.t >= MIN_LIFE) || g.t >= MAX_LIFE) this.beginDissolve(g);
      } else {
        const p = Math.min(1, (g.t - (g.dissolveStart ?? 0)) / DISSOLVE);
        for (const f of g.frags) f.unit.position.y = f.sinkY0 - SINK * p * p * (3 - 2 * p);
        for (const h of g.handles) h.uniforms.uFxP.value = p;
        if (p >= 1) { this.finish(g); this.groups.splice(gi, 1); }
      }
    }
  }

  private impact(faction: Faction, strength: number, p: Vector3): void {
    const now = fxState.time;
    if (now - this.lastImpact < 1 / 12) return;
    this.lastImpact = now;
    bus.emit('debris:impact', { faction, strength });
    if (strength > 0.45) this.particles.emit(faction === 'emberhold' ? 'dustPuff' : 'iceGlitter', _p.set(p.x, 0.03, p.z), { count: faction === 'emberhold' ? 3 : 6, scale: 0.5 });
  }

  private beginDissolve(g: DebrisGroup): void {
    g.dissolving = true;
    g.dissolveStart = g.t;
    const cache = new Map<Material, DissolveHandle>();
    for (const f of g.frags) {
      const tr = f.body.translation();
      f.sinkY0 = tr.y;
      f.unit.position.set(tr.x, tr.y, tr.z);
      this.world!.removeRigidBody(f.body);
      f.meshes.forEach((mesh, i) => {
        const orig = f.origMats[i];
        mesh.material = Array.isArray(orig) ? orig.map((m) => this.dissolveFor(m, g, cache)) : this.dissolveFor(orig, g, cache);
      });
    }
    for (const k of g.kin) this.world!.removeRigidBody(k.body);
    g.kin = [];
  }

  private dissolveFor(m: Material, g: DebrisGroup, cache: Map<Material, DissolveHandle>): Material {
    let h = cache.get(m);
    if (!h) { h = makeDissolveMaterial(m, g.faction); cache.set(m, h); g.handles.push(h); }
    return h.material;
  }

  private finish(g: DebrisGroup): void {
    for (const h of g.handles) h.material.dispose();
    for (const f of g.frags) {
      f.meshes.forEach((mesh, i) => { mesh.material = f.origMats[i]; });
      for (const m of f.merged) { // merged shards go back first (they are children of the host unit)
        if (m.parent) m.parent.add(m.unit); else m.unit.removeFromParent();
        m.unit.position.copy(m.pos); m.unit.quaternion.copy(m.quat); m.unit.scale.copy(m.scale); m.unit.visible = m.visible;
      }
      if (f.origParent) {
        f.origParent.add(f.unit);
        f.unit.position.copy(f.origPos); f.unit.quaternion.copy(f.origQuat); f.unit.scale.copy(f.origScale);
      } else f.unit.removeFromParent();
      f.unit.visible = f.origVisible;
    }
    g.onDone?.();
    g.resolve();
  }
}

const _p = new Vector3();
void _q;
