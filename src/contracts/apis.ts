// Module interfaces that let engine-core, cinematics, vfx, audio, ai and platform be built in
// parallel. Lead-owned: implementations live in their owners' folders and must satisfy these.
import type { AnimationAction, Mesh, Object3D, PerspectiveCamera, Scene, Vector3, WebGLRenderer } from 'three';
import type { AssetId, ClipName, PieceExtras, SocketName } from './assetContract';
import type { EventBus, GameModeKind } from './events';
import type { Faction, MoveResult, PromotionRole, Role, Side, Square } from './types';

/** GSAP timeline type (avoids relying on gsap's global namespace typings). */
export type Timeline = ReturnType<typeof import('gsap').gsap.timeline>;

// ---------------------------------------------------------------- settings
export type CameraMode = 'follow' | 'fixed' | 'free' | 'top';
export type CaptureMode = 'full' | 'quick' | 'off';
export type QualityTier = 'high' | 'medium' | 'low';
export type AiLevel = 'easy' | 'medium' | 'hard' | 'master';

export interface Settings {
  cameraMode: CameraMode;
  captureMode: CaptureMode;
  /** Global animation speed multiplier, 0.5–2. */
  animSpeed: number;
  quality: QualityTier | 'auto';
  musicEnabled: boolean;
  musicVolume: number; // 0–1
  sfxVolume: number; // 0–1
  colorBlind: boolean;
  showMoveList: boolean;
  aiLevel: AiLevel;
  /** Human side in vs-AI mode. */
  playerSide: Side;
}

export const DEFAULT_SETTINGS: Settings = {
  cameraMode: 'follow', captureMode: 'full', animSpeed: 1, quality: 'auto',
  musicEnabled: true, musicVolume: 0.55, sfxVolume: 0.8, colorBlind: false,
  showMoveList: true, aiLevel: 'medium', playerSide: 'w',
};

export interface SettingsStore {
  get(): Readonly<Settings>;
  set<K extends keyof Settings>(key: K, value: Settings[K]): void;
  subscribe(fn: (s: Readonly<Settings>, key: keyof Settings) => void): () => void;
}

// ---------------------------------------------------------------- assets
export interface PieceActor {
  readonly id: AssetId;
  readonly faction: Faction;
  readonly role: Role;
  readonly side: Side;
  /** Board-placed transform root (position on the square, yaw). Tween this, never `model`. */
  readonly root: Object3D;
  /** Loaded/cloned GLB scene under root. */
  readonly model: Object3D;
  readonly extras: PieceExtras;
  readonly sockets: Partial<Record<SocketName, Object3D>>;
  /** Invisible cylinder used for raycasting. */
  readonly collider: Mesh;
  /** Visible meshes (for material sweeps, dissolve, flash). */
  readonly meshes: Mesh[];
  square: Square;

  hasClip(clip: ClipName): boolean;
  clipDuration(clip: ClipName): number;
  /** Free-running playback via the mixer (Idle/Move loops). */
  play(clip: ClipName, opts?: { fade?: number; loop?: boolean }): AnimationAction | null;
  /** Scrub a clip to an absolute time (GSAP-driven playback). Weight 1, others faded out. */
  scrub(clip: ClipName, time: number): void;
  /** GSAP timeline that scrubs Attack; label "impact" at extras.impactTime. Fallback: procedural lunge. */
  attackTimeline(): Timeline;
  /** GSAP timeline that scrubs any once-clip (HitReact, Victory) for its duration. */
  clipTimeline(clip: ClipName): Timeline;
  socketWorld(name: SocketName, target: Vector3): Vector3;
  setYaw(yaw: number): void;
  getYaw(): number;
  /** 0 = normal, 1 = fully dimmed (board dim during captures). */
  setDim(amount: number): void;
  setHighlight(on: boolean): void;
  /** Occluder fade for cinematics: 1 = opaque, 0 = hidden (dithered/transparent, no shadow). */
  setFade(alpha: number): void;
  /** Queens: scale of weapon_summon node (0 hidden … 1 shown). */
  setWeaponSummon(scale: number): void;
  update(dt: number): void;
  dispose(): void;
}

export interface AssetRegistry {
  preload(onProgress?: (loaded: number, total: number) => void): Promise<void>;
  createActor(faction: Faction, role: Role, square: Square): PieceActor;
  /** Fragment set positioned at the origin in rest pose; caller places it. Lazily loaded, pooled. */
  acquireFragments(id: AssetId): Promise<Object3D>;
  releaseFragments(id: AssetId, obj: Object3D): void;
}

// ---------------------------------------------------------------- board / actors
export interface BoardApi {
  readonly scene: Scene;
  actorAt(sq: Square): PieceActor | undefined;
  allActors(): PieceActor[];
  /** Re-key an actor to a new square (does not tween). */
  setActorSquare(actor: PieceActor, sq: Square): void;
  /** Remove from scene + index (after shatter swap). */
  removeActor(actor: PieceActor): void;
  spawnActor(faction: Faction, role: Role, sq: Square): PieceActor;
  /** World-space top-centre of a square. */
  squareCenter(sq: Square, target: Vector3): Vector3;
  /** Tint a tile (check glow etc.). null clears. */
  tintSquare(sq: Square, color: number | null): void;
  /** Snap every actor to the given FEN placement (used after skip and for sync safety). */
  syncToFen(fen: string): void;
}

// ---------------------------------------------------------------- camera
export interface CinematicCameraHandle {
  readonly camera: PerspectiveCamera;
  /** Set pose directly each frame while borrowed. */
  set(position: Vector3, lookAt: Vector3, fov?: number): void;
}

export interface CameraRig {
  readonly camera: PerspectiveCamera;
  mode: CameraMode;
  setMode(mode: CameraMode): void;
  /** Swing to a side's seat (1.4 s power2.inOut, shorter arc). */
  toSeat(side: Side, opts?: { instant?: boolean }): Promise<void>;
  /** Hand control to the capture director; idle drift and orbit controls pause. */
  borrow(): CinematicCameraHandle;
  /** Tween back to the current seat and resume. */
  restore(duration?: number): Promise<void>;
  /** Trauma-model shake, 0–1. */
  shake(trauma: number): void;
  resize(width: number, height: number): void;
  update(dt: number): void;
}

// ---------------------------------------------------------------- fx
export type ParticlePreset = 'embers' | 'sparks' | 'smoke' | 'frostMist' | 'iceGlitter' | 'summonSpiral' | 'dustPuff' | 'fireWave' | 'frostBeam';

export interface EmitOptions {
  count?: number;
  direction?: Vector3;
  spread?: number;
  speed?: number;
  /** Seconds the emitter keeps spawning (0 = one burst). */
  duration?: number;
  /** Optional object to follow while emitting. */
  follow?: Object3D;
  scale?: number;
}

export interface ShatterOptions {
  actor: PieceActor;
  /** Fragment set already placed at the actor's world transform. */
  fragments: Object3D;
  impulseDir: Vector3;
  /** 0.5 (pawn) … 1.5 (queen/king/rook slam). */
  magnitude: number;
  /** Optional cut plane normal (queen sweeping cut splits fragments into two groups). */
  cutNormal?: Vector3;
  /** Called when fragments have dissolved; caller releases them to the pool. */
  onDone?: () => void;
}

export interface FxApi {
  init(scene: Scene, renderer: WebGLRenderer, camera: PerspectiveCamera): Promise<void>;
  setQuality(tier: QualityTier): void;
  emit(preset: ParticlePreset, position: Vector3, opts?: EmitOptions): void;
  shatter(opts: ShatterOptions): Promise<void>;
  shockwave(position: Vector3, faction: Faction, radius?: number): void;
  iceSpikes(position: Vector3, count?: number): Promise<void>;
  /** Ribbon trail following an object until stop(). */
  trail(follow: Object3D, faction: Faction): { stop(): void };
  /** Mask sweep over an actor's materials: frost (white freeze) or ember (glowing cracks). */
  sweep(actor: PieceActor, kind: 'frost' | 'ember', duration: number): Promise<void>;
  /** Noise dissolve with faction edge glow, then hides object. */
  dissolve(obj: Object3D, faction: Faction, duration: number): Promise<void>;
  decal(position: Vector3, kind: 'crack' | 'scorch' | 'frost'): void;
  /** Promotion column: fire pillar (emberhold) / ice cocoon (rime). */
  column(position: Vector3, faction: Faction, duration: number): Promise<void>;
  /** Check aura pulse at a point. */
  aura(position: Vector3, faction: Faction): void;
  /** 1-frame emissive flash on an actor + bloom pulse. */
  flash(actor: PieceActor): void;
  /** Grey mist across the board (stalemate/draw). */
  mist(): void;
  /** Advance simulation; dt already scaled by gsap.globalTimeline.timeScale(). */
  update(dt: number): void;
}

export interface PostPipeline {
  render(dt: number): void;
  setSize(width: number, height: number): void;
  setQuality(tier: QualityTier): void;
  bloomPulse(strength: number, duration: number): void;
}

/** Factory signature implemented by src/render/post.ts (vfx-shaders). */
export type CreatePost = (renderer: WebGLRenderer, scene: Scene, camera: PerspectiveCamera, tier: QualityTier) => PostPipeline;

// ---------------------------------------------------------------- sequences
export interface SequenceContext {
  move: MoveResult;
  board: BoardApi;
  camera: CameraRig;
  fx: FxApi;
  registry: AssetRegistry;
  bus: EventBus;
  settings: Readonly<Settings>;
}

/** Implemented by src/cinematics (cinematics agent). Every method resolves with the board in its final state. */
export interface SequencePlayer {
  /** Non-capture, non-castle move (walk/hop/leap to `to`). */
  move(ctx: SequenceContext): Promise<void>;
  capture(ctx: SequenceContext): Promise<void>;
  castle(ctx: SequenceContext): Promise<void>;
  /** Pawn already on the last rank (after move/capture sequence) → promoted actor revealed. */
  promote(ctx: SequenceContext, role: PromotionRole): Promise<void>;
  check(ctx: SequenceContext, kingSquare: Square): Promise<void>;
  checkmate(ctx: SequenceContext, kingSquare: Square): Promise<void>;
  stalemate(ctx: SequenceContext): Promise<void>;
  /** Finish the running sequence immediately (tl.progress(1), snap transforms). */
  skip(): void;
  readonly running: boolean;
}

// ---------------------------------------------------------------- audio
export type SfxName =
  | `move:step:${Faction}` | `attack:whoosh:${Role}` | `impact:${Faction}` | `shatter:${Faction}`
  | `summon:${Faction}` | `spell:${Faction}` | 'check' | 'mate' | 'ui:click' | 'ui:select' | 'castle' | 'promote';

export interface AudioBus {
  /** Must be called from a user gesture (autoplay policy). */
  unlock(): Promise<void>;
  sfx(name: SfxName, opts?: { volume?: number; pitch?: number }): void;
  setMusicEnabled(on: boolean): void;
  setVolumes(music: number, sfx: number): void;
  hasMusic(): boolean;
  /** User-supplied track (persisted in IndexedDB). */
  loadCustomTrack(file: File): Promise<void>;
  /** Subscribes to the event bus for automatic hooks. */
  attach(bus: EventBus): void;
}

// ---------------------------------------------------------------- ai
export interface AiMove { from: Square; to: Square; promotion?: PromotionRole }

export interface AiPlayer {
  init(): Promise<void>;
  getMove(fen: string, level: AiLevel): Promise<AiMove>;
  /** Abort a pending search (new game / undo); pending promise rejects with 'cancelled'. */
  cancel(): void;
  newGame(): void;
  dispose(): void;
}

// ---------------------------------------------------------------- platform
export interface PlatformApi {
  readonly isNative: boolean;
  readonly isMobile: boolean;
  init(): Promise<void>;
  /** Android back button → handler returns true if consumed. */
  onBack(handler: () => boolean): void;
  keepAwake?(on: boolean): void;
}

export interface GameModeConfig {
  kind: GameModeKind;
  /** vs-ai: human side. */
  playerSide: Side;
  aiLevel: AiLevel;
}
