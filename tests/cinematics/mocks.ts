// Lightweight mocks of PieceActor / BoardApi / CameraRig / FxApi / AssetRegistry built on plain three.js
// Object3Ds (no WebGL, no GLB loading).
import { Mesh, Object3D, PerspectiveCamera, Quaternion, Scene, Vector3, CylinderGeometry } from 'three';
import type {
  AssetRegistry, BoardApi, CameraRig, CinematicCameraHandle, FxApi, PieceActor, SequenceContext, Settings, Timeline,
} from '../../src/contracts';
import {
  assetId, DEFAULT_EXTRAS, DEFAULT_SETTINGS, EventBus, restYaw, squareToWorld, WEAPON_SUMMON_NODE,
} from '../../src/contracts';
import type {
  AssetId, ClipName, EmitOptions, Faction, MoveResult, ParticlePreset, QualityTier, Role, ShatterOptions, Side, SocketName, Square,
} from '../../src/contracts';
import { gsap } from './harness';

const CLIP_LEN: Record<ClipName, number> = { Idle: 2, Move: 0.8, Attack: 1.9, HitReact: 0.6, Victory: 1.4 };
const FACTION_SIDE: Record<Faction, Side> = { emberhold: 'w', rime: 'b' };

export interface ActorOpts { noSocketCast?: boolean; noClips?: boolean; noImpactLabel?: boolean }

export class MockActor implements PieceActor {
  readonly id: AssetId;
  readonly side: Side;
  readonly root = new Object3D();
  readonly model = new Object3D();
  readonly collider: Mesh;
  readonly meshes: Mesh[] = [];
  readonly sockets: Partial<Record<SocketName, Object3D>> = {};
  readonly extras;
  square: Square;
  dim = 0;
  fade = 1;
  minFade = 1;
  fadeCalls = 0;
  summon = 0;
  maxSummon = 0;
  playing = 'Idle';
  scrubs: Array<[ClipName, number]> = [];
  clipsPlayed: ClipName[] = [];
  disposed = false;

  constructor(readonly faction: Faction, readonly role: Role, square: Square, private opts: ActorOpts = {}) {
    this.id = assetId(faction, role);
    this.side = FACTION_SIDE[faction];
    this.square = square;
    this.extras = { ...DEFAULT_EXTRAS[role], faction, displayName: this.id, contractVersion: 1 };
    this.root.add(this.model);
    this.collider = new Mesh(new CylinderGeometry(0.4, 0.4, 1.2));
    this.root.add(this.collider);
    const mk = (name: SocketName, y: number, x = 0) => { const o = new Object3D(); o.name = name; o.position.set(x, y, 0.2); this.model.add(o); this.sockets[name] = o; };
    mk('socket_weapon_R', 0.9, 0.3); mk('socket_impact', 0.7); mk('socket_head', 1.1);
    if (!opts.noSocketCast) mk('socket_cast', 1.0, -0.2);
    if (role === 'queen') { const w = new Object3D(); w.name = WEAPON_SUMMON_NODE; this.model.add(w); }
    squareToWorld(square, this.root.position);
    this.root.rotation.y = restYaw(this.side);
  }

  hasClip(clip: ClipName) { return !this.opts.noClips && clip in CLIP_LEN; }
  clipDuration(clip: ClipName) { return CLIP_LEN[clip]; }
  play(clip: ClipName) { this.playing = clip; return null; }
  scrub(clip: ClipName, time: number) { this.scrubs.push([clip, time]); this.playing = clip; }
  attackTimeline(): Timeline {
    const tl = gsap.timeline();
    const o = { t: 0 };
    tl.to(o, { t: 1, duration: this.extras.impactTime + 0.55, ease: 'none', onUpdate: () => this.scrub('Attack', o.t) });
    if (!this.opts.noImpactLabel) tl.addLabel('impact', this.extras.impactTime);
    return tl;
  }
  clipTimeline(clip: ClipName): Timeline {
    const tl = gsap.timeline();
    const o = { t: 0 };
    this.clipsPlayed.push(clip);
    tl.to(o, { t: 1, duration: CLIP_LEN[clip], ease: 'none', onUpdate: () => this.scrub(clip, o.t * CLIP_LEN[clip]) });
    return tl;
  }
  socketWorld(name: SocketName, target: Vector3) {
    const s = this.sockets[name];
    if (!s) throw new Error(`no socket ${name}`);
    return s.getWorldPosition(target);
  }
  setYaw(yaw: number) { this.root.rotation.y = yaw; }
  getYaw() { return this.root.rotation.y; }
  setDim(a: number) { this.dim = a; }
  setHighlight() {}
  setFade(a: number) { this.fade = a; this.minFade = Math.min(this.minFade, a); this.fadeCalls++; }
  setWeaponSummon(s: number) { this.summon = s; this.maxSummon = Math.max(this.maxSummon, s); }
  update() {}
  dispose() { this.disposed = true; }
}

export class MockBoard implements BoardApi {
  readonly scene = new Scene();
  private map = new Map<Square, MockActor>();
  removed: MockActor[] = [];
  spawned: MockActor[] = [];
  tints: Array<[Square, number | null]> = [];
  syncCalls: string[] = [];
  setSquareCalls: Array<[MockActor, Square]> = [];
  constructor(readonly actorOpts: ActorOpts = {}) {}

  add(faction: Faction, role: Role, sq: Square): MockActor {
    const a = new MockActor(faction, role, sq, this.actorOpts);
    this.map.set(sq, a); this.scene.add(a.root);
    return a;
  }
  actorAt(sq: Square) { return this.map.get(sq); }
  allActors() { return [...this.map.values()]; }
  setActorSquare(actor: PieceActor, sq: Square) {
    const a = actor as MockActor;
    this.setSquareCalls.push([a, sq]);
    for (const [k, v] of this.map) if (v === a) this.map.delete(k);
    a.square = sq; this.map.set(sq, a);
  }
  removeActor(actor: PieceActor) {
    const a = actor as MockActor;
    // like a square-keyed index: only drops the entry if it still points at this actor
    if (this.map.get(a.square) === a) this.map.delete(a.square);
    for (const [k, v] of this.map) if (v === a) this.map.delete(k);
    this.scene.remove(a.root); this.removed.push(a);
  }
  spawnActor(faction: Faction, role: Role, sq: Square) {
    const a = this.add(faction, role, sq); this.spawned.push(a); return a;
  }
  squareCenter(sq: Square, target: Vector3) { return squareToWorld(sq, target); }
  tintSquare(sq: Square, color: number | null) { this.tints.push([sq, color]); }
  syncToFen(fen: string) { this.syncCalls.push(fen); }
}

export interface PoseSample { position: Vector3; lookAt: Vector3; fov: number; t: number }

export class MockCamera implements CameraRig {
  readonly camera = new PerspectiveCamera(40, 16 / 9, 0.1, 100);
  mode: 'follow' = 'follow';
  state: 'seat' | 'borrowed' | 'restoring' = 'seat';
  poses: PoseSample[] = [];
  shakes: number[] = [];
  borrows = 0;
  restores: number[] = [];
  hangRestore = false;
  constructor(seatZ: 1 | -1 = 1) {
    this.camera.position.set(0, 9, 8 * seatZ);
    this.camera.lookAt(0, 0, 0);
    this.camera.updateMatrixWorld();
  }
  setMode() {}
  async toSeat() {}
  borrow(): CinematicCameraHandle {
    this.borrows++; this.state = 'borrowed';
    const self = this;
    return {
      camera: this.camera,
      set(position, lookAt, fov) {
        if (self.state !== 'borrowed') throw new Error(`camera.set while ${self.state}`);
        self.poses.push({ position: position.clone(), lookAt: lookAt.clone(), fov: fov ?? self.camera.fov, t: Date.now() });
        self.camera.position.copy(position); self.camera.lookAt(lookAt);
        if (fov) { self.camera.fov = fov; self.camera.updateProjectionMatrix(); }
        self.camera.updateMatrixWorld();
      },
    };
  }
  restore(duration = 1): Promise<void> {
    this.restores.push(duration);
    if (duration <= 0 && !this.hangRestore) { this.state = 'seat'; return Promise.resolve(); }
    this.state = 'restoring';
    if (this.hangRestore) return new Promise(() => {});
    return new Promise((r) => setTimeout(() => { this.state = 'seat'; r(); }, duration * 1000));
  }
  shake(t: number) { this.shakes.push(t); }
  resize() {}
  update() {}
}

export interface FxCall { name: string; args: unknown[] }

export class MockFx implements FxApi {
  calls: FxCall[] = [];
  trailsOpen = 0;
  constructor(public hang = false) {}
  private rec(name: string, ...args: unknown[]) { this.calls.push({ name, args }); }
  private p(): Promise<void> { return this.hang ? new Promise(() => {}) : Promise.resolve(); }
  count(name: string) { return this.calls.filter((c) => c.name === name).length; }
  async init() {}
  setQuality(_t: QualityTier) {}
  emit(preset: ParticlePreset, position: Vector3, opts?: EmitOptions) {
    if (!Number.isFinite(position.x + position.y + position.z)) throw new Error('emit with NaN position');
    this.rec('emit', preset, position, opts);
  }
  shatter(o: ShatterOptions) {
    this.rec('shatter', o);
    if (this.hang) return new Promise<void>(() => {});
    return new Promise<void>((r) => setTimeout(() => { o.onDone?.(); r(); }, 1600));
  }
  shockwave(p: Vector3, f: Faction, r?: number) { this.rec('shockwave', p, f, r); }
  iceSpikes(p: Vector3, c?: number) { this.rec('iceSpikes', p, c); return this.p(); }
  trail(follow: Object3D, faction: Faction) {
    this.rec('trail', follow, faction); this.trailsOpen++;
    let open = true;
    return { stop: () => { if (open) { open = false; this.trailsOpen--; } } };
  }
  sweep(a: PieceActor, kind: 'frost' | 'ember', d: number) { this.rec('sweep', a, kind, d); return this.p(); }
  dissolve(obj: Object3D, f: Faction, d: number) { this.rec('dissolve', obj, f, d); return this.p(); }
  decal(p: Vector3, kind: 'crack' | 'scorch' | 'frost') { this.rec('decal', p, kind); }
  column(p: Vector3, f: Faction, d: number) { this.rec('column', p, f, d); return this.p(); }
  aura(p: Vector3, f: Faction) { this.rec('aura', p, f); }
  flash(a: PieceActor) { this.rec('flash', a); }
  mist() { this.rec('mist'); }
  update() {}
}

export class MockRegistry implements AssetRegistry {
  outstanding = new Set<Object3D>();
  acquires = 0;
  releases = 0;
  constructor(public hang = false) {}
  async preload() {}
  createActor(): PieceActor { throw new Error('unused'); }
  acquireFragments(id: AssetId): Promise<Object3D> {
    this.acquires++;
    if (this.hang) return new Promise(() => {});
    const o = new Object3D(); o.name = `${id}_fragments`;
    this.outstanding.add(o);
    return Promise.resolve(o);
  }
  releaseFragments(_id: AssetId, obj: Object3D) { this.releases++; this.outstanding.delete(obj); }
}

export function mkMove(p: Partial<MoveResult> & Pick<MoveResult, 'from' | 'to' | 'side' | 'role'>): MoveResult {
  return {
    san: '', flags: '', isCastle: false, isEnPassant: false, check: false, mate: false, stalemate: false, draw: false,
    fenAfter: 'fen-after', ...p,
  };
}

export interface Rig {
  ctx: SequenceContext;
  board: MockBoard; camera: MockCamera; fx: MockFx; registry: MockRegistry; bus: EventBus;
  events: Array<{ name: string; payload: any }>;
  settings: Settings;
}

const EVENT_NAMES = ['capture:begin', 'capture:impact', 'capture:shatter', 'capture:end', 'attack:whoosh', 'summon', 'spell', 'move:step', 'castle', 'promotion'] as const;

export function makeRig(move: MoveResult, setup: (board: MockBoard) => void, over: Partial<Settings> = {}, extra: { actorOpts?: ActorOpts; hang?: boolean; seatZ?: 1 | -1 } = {}): Rig {
  const board = new MockBoard(extra.actorOpts);
  setup(board);
  const camera = new MockCamera(extra.seatZ ?? 1);
  const fx = new MockFx(extra.hang);
  const registry = new MockRegistry(extra.hang);
  const bus = new EventBus();
  const events: Rig['events'] = [];
  for (const n of EVENT_NAMES) bus.on(n, (payload) => events.push({ name: n, payload }));
  const settings: Settings = { ...DEFAULT_SETTINGS, ...over };
  if (extra.hang) camera.hangRestore = true;
  return { ctx: { move, board, camera, fx, registry, bus, settings }, board, camera, fx, registry, bus, events, settings };
}

export { Quaternion };
