// Sandbox PieceActor: real placeholder GLB + AnimationMixer, GSAP-driven clip scrubbing (like the real one will be).
import { gsap } from 'gsap';
import {
  AnimationAction, AnimationMixer, Color, CylinderGeometry, LoopOnce, LoopRepeat, Mesh, MeshStandardMaterial, Object3D, Vector3,
} from 'three';
import type { GLTF } from 'three/examples/jsm/loaders/GLTFLoader.js';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';
import { MeshoptDecoder } from 'three/examples/jsm/libs/meshopt_decoder.module.js';
import { clone } from 'three/examples/jsm/utils/SkeletonUtils.js';
import type {
  AssetId, AssetRegistry, ClipName, Faction, PieceActor, PieceExtras, Role, Side, SocketName, Square, Timeline,
} from '../../src/contracts';
import { ALL_ASSET_IDS, assetId, DEFAULT_EXTRAS, FACTION_SIDE, fragmentsUrl, LOOPING_CLIPS, modelUrl, restYaw, squareToWorld, WEAPON_SUMMON_NODE } from '../../src/contracts';

const SOCKETS: SocketName[] = ['socket_weapon_R', 'socket_cast', 'socket_impact', 'socket_head'];

export class SandboxActor implements PieceActor {
  readonly id: AssetId;
  readonly side: Side;
  readonly root = new Object3D();
  readonly model: Object3D;
  readonly extras: PieceExtras;
  readonly sockets: Partial<Record<SocketName, Object3D>> = {};
  readonly collider: Mesh;
  readonly meshes: Mesh[] = [];
  square: Square;
  private mixer: AnimationMixer;
  private actions = new Map<ClipName, AnimationAction>();
  private base = new Map<MeshStandardMaterial, { c: Color; e: Color }>();
  private flashT = 0;

  constructor(gltf: GLTF, readonly faction: Faction, readonly role: Role, square: Square) {
    this.id = assetId(faction, role);
    this.side = FACTION_SIDE[faction];
    this.square = square;
    this.model = clone(gltf.scene);
    this.root.add(this.model);
    let ex: Partial<PieceExtras> | undefined;
    this.model.traverse((o) => { if (ex === undefined && o.userData && typeof o.userData.impactTime === 'number') ex = o.userData as Partial<PieceExtras>; });
    this.extras = { ...DEFAULT_EXTRAS[role], faction, displayName: this.id, contractVersion: 1, ...(ex ?? {}) } as PieceExtras;
    this.model.traverse((o) => {
      if (o.name.endsWith('_LOD1')) o.visible = false;
      if ((o as Mesh).isMesh) {
        const m = o as Mesh;
        m.castShadow = true;
        const mat = (m.material as MeshStandardMaterial).clone();
        m.material = mat;
        this.base.set(mat, { c: mat.color.clone(), e: mat.emissive.clone() });
        this.meshes.push(m);
      }
    });
    for (const s of SOCKETS) { const n = this.model.getObjectByName(s); if (n) this.sockets[s] = n; }
    this.collider = new Mesh(new CylinderGeometry(0.4, 0.4, 1.2), undefined);
    this.collider.visible = false;
    this.root.add(this.collider);
    this.mixer = new AnimationMixer(this.model);
    for (const clip of gltf.animations) this.actions.set(clip.name as ClipName, this.mixer.clipAction(clip));
    const w = this.model.getObjectByName(WEAPON_SUMMON_NODE);
    if (w) w.scale.setScalar(0);
    squareToWorld(square, this.root.position);
    this.root.rotation.y = restYaw(this.side);
    this.play('Idle', { fade: 0 });
  }

  hasClip(c: ClipName) { return this.actions.has(c); }
  clipDuration(c: ClipName) { return this.actions.get(c)?.getClip().duration ?? 0; }

  play(clip: ClipName, opts: { fade?: number; loop?: boolean } = {}) {
    const a = this.actions.get(clip);
    if (!a) return null;
    const fade = opts.fade ?? 0.2;
    for (const [n, o] of this.actions) if (n !== clip) o.fadeOut(fade);
    a.reset(); a.paused = false; a.enabled = true;
    a.setLoop(opts.loop ?? LOOPING_CLIPS.includes(clip) ? LoopRepeat : LoopOnce, Infinity);
    a.setEffectiveWeight(1);
    if (fade > 0) a.fadeIn(fade);
    a.play();
    return a;
  }

  scrub(clip: ClipName, time: number) {
    const a = this.actions.get(clip);
    if (!a) return;
    for (const [n, o] of this.actions) if (n !== clip) { o.setEffectiveWeight(0); o.paused = true; }
    a.enabled = true; a.setEffectiveWeight(1); a.setLoop(LoopRepeat, Infinity);
    if (!a.isRunning()) a.play();
    a.paused = true;
    a.time = Math.min(Math.max(0, time), a.getClip().duration - 1e-4);
    this.mixer.update(0);
  }

  private clipTl(clip: ClipName): Timeline {
    const dur = this.clipDuration(clip);
    const tl = gsap.timeline();
    const o = { t: 0 };
    tl.to(o, { t: dur, duration: Math.max(1e-3, dur), ease: 'none', onUpdate: () => this.scrub(clip, o.t) });
    return tl;
  }
  attackTimeline(): Timeline {
    const tl = this.hasClip('Attack') ? this.clipTl('Attack') : gsap.timeline().to(this.root.position, { duration: this.extras.impactTime + 0.4 });
    tl.addLabel('impact', this.extras.impactTime);
    return tl;
  }
  clipTimeline(clip: ClipName) { return this.clipTl(clip); }

  socketWorld(name: SocketName, target: Vector3) {
    const s = this.sockets[name];
    if (!s) throw new Error(`missing ${name}`);
    return s.getWorldPosition(target);
  }
  setYaw(y: number) { this.root.rotation.y = y; }
  getYaw() { return this.root.rotation.y; }
  setDim(a: number) {
    for (const [m, b] of this.base) { m.color.copy(b.c).multiplyScalar(1 - a * 0.75); }
  }
  setHighlight() {}
  /** Occluder fade: translucent + no shadow (the real engine may use dithering). */
  setFade(a: number) {
    const faded = a < 0.999;
    for (const m of this.base.keys()) {
      const was = m.transparent;
      m.transparent = faded; m.opacity = a; m.depthWrite = !faded;
      if (was !== faded) m.needsUpdate = true;
    }
    for (const mesh of this.meshes) mesh.castShadow = a > 0.5;
  }
  setWeaponSummon(s: number) { this.model.getObjectByName(WEAPON_SUMMON_NODE)?.scale.setScalar(s); }
  /** Emissive spike used by fx.flash. */
  flash() { this.flashT = 1; }
  tint(color: Color | null, k: number) {
    for (const [m, b] of this.base) { if (color) m.emissive.copy(b.e).lerp(color, k); else m.emissive.copy(b.e); }
  }
  update(dt: number) {
    this.mixer.update(dt);
    if (this.flashT > 0) {
      this.flashT = Math.max(0, this.flashT - dt * 6);
      for (const [m, b] of this.base) m.emissive.copy(b.e).lerp(new Color(1, 1, 1), this.flashT);
    }
  }
  dispose() { this.mixer.stopAllAction(); }
}

export class SandboxRegistry implements AssetRegistry {
  private loader = new GLTFLoader().setMeshoptDecoder(MeshoptDecoder);
  private gltfs = new Map<AssetId, GLTF>();
  private frags = new Map<AssetId, Promise<GLTF>>();
  outstanding = 0;
  async preload(onProgress?: (l: number, t: number) => void) {
    let n = 0;
    await Promise.all(ALL_ASSET_IDS.map(async (id) => {
      this.gltfs.set(id, await this.loader.loadAsync('/' + modelUrl(id)));
      onProgress?.(++n, ALL_ASSET_IDS.length);
    }));
  }
  createActor(faction: Faction, role: Role, square: Square) {
    return new SandboxActor(this.gltfs.get(assetId(faction, role))!, faction, role, square);
  }
  async acquireFragments(id: AssetId) {
    let p = this.frags.get(id);
    if (!p) { p = this.loader.loadAsync('/' + fragmentsUrl(id)); this.frags.set(id, p); }
    const g = await p;
    this.outstanding++;
    return clone(g.scene);
  }
  releaseFragments(_id: AssetId, obj: Object3D) { obj.parent?.remove(obj); this.outstanding--; }
}
