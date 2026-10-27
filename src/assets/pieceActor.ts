// PieceActor implementation (architecture §6): one cloned, skinned GLB per piece on the board.
//   - root = board-placed transform (tween this), model = cloned GLB scene underneath.
//   - GSAP is the single clock for scripted clips: scrub() sets action time directly, so slow motion
//     and skip() work everywhere. Idle/Move loops run free through the mixer.
//   - Materials are cloned per actor, so dim / highlight / vfx sweeps never leak to other pieces.
//   - Missing clips or sockets are contract errors: logged once, then replaced by procedural fallbacks.
import { gsap } from 'gsap';
import {
  AnimationMixer, Color, CylinderGeometry, LoopOnce, LoopRepeat, Mesh, MeshBasicMaterial, Object3D,
  type AnimationAction, type AnimationClip, type Material,
} from 'three';
import { clone as cloneSkinned } from 'three/addons/utils/SkeletonUtils.js';
import type { AssetId, ClipName, Faction, PieceActor, PieceExtras, Role, Side, SocketName, Square, Timeline } from '../contracts';
import {
  CLIPS, OPTIONAL_CLIPS, DEFAULT_EXTRAS, DISPLAY_NAME, FACTION_SIDE, LOOPING_CLIPS, ROLE_HEIGHT, SOCKETS, WEAPON_SUMMON_NODE,
  CONTRACT_VERSION, BOARD_PIECE_SCALE, lodName, restYaw, squareToWorld,
} from '../contracts';

export interface PieceTemplate {
  scene: Object3D;
  animations: AnimationClip[];
}

export interface PieceActorImpl extends PieceActor {
  /** 'free' = mixer-driven (Idle/Move), 'scrub' = GSAP-driven (Attack/HitReact/Victory). */
  readonly mode: 'free' | 'scrub';
  setLod(lod: 0 | 1): void;
  /** Resting uniform scale on the board (BOARD_PIECE_SCALE); cinematics may enlarge fighters and the board restores it. */
  baseScale: number;
  /** Current fade alpha (1 = opaque). */
  readonly fade: number;
  /** Seconds of simulation time not yet fed to the mixer (idle mixers update at half rate). */
  pendingDt: number;
  /** True for the static graveyard variant (no mixer, no collider, frozen pose). */
  readonly isStatic: boolean;
  /** Return to a clean idle state: clears model offsets, dim, highlight and scrubbed poses. */
  resetPose(): void;
}

const loggedErrors = new Set<string>();
/** Contract violations are logged once per message and never throw: the game keeps running. */
export function contractError(msg: string): void {
  if (loggedErrors.has(msg)) return;
  loggedErrors.add(msg);
  console.error(`[contract] ${msg}`);
}

interface MatState {
  mat: Material & { color?: Color; emissive?: Color };
  color: Color | null;
  emissive: Color | null;
  transparent: boolean;
  opacity: number;
  depthWrite: boolean;
}

const HIGHLIGHT = new Color(0xffc060);
const DIM_COLOR = new Color(0x050608);
const _c = new Color();

export interface CreateActorOptions {
  id: AssetId;
  faction: Faction;
  role: Role;
  square: Square;
  template: PieceTemplate;
  lod: 0 | 1;
  /** 'graveyard': static kneeling display piece (end of the Surrender clip, LOD1, no collider / per-frame work). */
  variant?: 'board' | 'graveyard';
  /** Uniform scale of the root (default BOARD_PIECE_SCALE, or the graveyard scale when given). */
  scale?: number;
}

export function createPieceActor(opts: CreateActorOptions): PieceActorImpl {
  const { id, faction, role, template } = opts;
  const side: Side = FACTION_SIDE[faction];

  const root = new Object3D();
  root.name = `${id}@actor`;
  const model = cloneSkinned(template.scene);
  root.add(model);

  // ---- extras (glTF extras land in userData of the asset node)
  const assetNode = model.getObjectByName(id) ?? model;
  const rawExtras = (assetNode.userData ?? {}) as Partial<PieceExtras>;
  if (typeof rawExtras.impactTime !== 'number') contractError(`${id}: missing glTF extras (impactTime); using role defaults`);
  const extras: PieceExtras = {
    ...DEFAULT_EXTRAS[role], faction, role, displayName: DISPLAY_NAME[id], contractVersion: CONTRACT_VERSION,
    ...(rawExtras as object),
  } as PieceExtras;

  // ---- sockets
  const sockets: Partial<Record<SocketName, Object3D>> = {};
  for (const name of SOCKETS) {
    const n = model.getObjectByName(name);
    if (n) sockets[name] = n;
    // socket_cast is only required on bishops (validate_glb.py); other roles fall back to a height-based point silently.
    else if (name !== 'socket_cast' || role === 'bishop') contractError(`${id}: missing socket ${name}; using height-based fallback`);
  }

  // ---- per-actor materials + shadows
  const matMap = new Map<Material, Material>();
  const matStates: MatState[] = [];
  const meshesAll: Mesh[] = [];
  const cloneMat = (m: Material): Material => {
    let c = matMap.get(m);
    if (!c) {
      c = m.clone();
      matMap.set(m, c);
      const mm = c as MatState['mat'];
      matStates.push({ mat: mm, color: mm.color ? mm.color.clone() : null, emissive: mm.emissive ? mm.emissive.clone() : null, transparent: mm.transparent, opacity: mm.opacity, depthWrite: mm.depthWrite });
    }
    return c;
  };
  model.traverse((o) => {
    const mesh = o as Mesh;
    if (!mesh.isMesh) return;
    mesh.material = Array.isArray(mesh.material) ? mesh.material.map(cloneMat) : cloneMat(mesh.material);
    mesh.castShadow = true;
    mesh.receiveShadow = true;
    mesh.frustumCulled = false; // skinned bounds come from the bind pose
    meshesAll.push(mesh);
  });

  // ---- LOD
  const lodMeshes: [Object3D | undefined, Object3D | undefined] = [model.getObjectByName(lodName(id, 0)), model.getObjectByName(lodName(id, 1))];
  if (!lodMeshes[0] && !lodMeshes[1]) contractError(`${id}: no LOD meshes found`);
  let meshes: Mesh[] = meshesAll;
  const setLod = (lod: 0 | 1) => {
    const want = lodMeshes[lod] ? lod : lodMeshes[0] ? 0 : 1;
    lodMeshes.forEach((m, i) => { if (m) m.visible = i === want; });
    meshes = meshesAll.filter((m) => {
      for (let i = 0; i < 2; i++) {
        const l = lodMeshes[i];
        if (l && i !== want) { let p: Object3D | null = m; while (p) { if (p === l) return false; p = p.parent; } }
      }
      return true;
    });
  };
  setLod(opts.lod);

  // ---- weapon summon (queen)
  const summonNode = model.getObjectByName(WEAPON_SUMMON_NODE);
  if (summonNode) { summonNode.scale.setScalar(0); summonNode.visible = false; }
  if (role === 'queen' && !summonNode) contractError(`${id}: queen without ${WEAPON_SUMMON_NODE} node`);

  // ---- collider (raycast target; the skinned mesh is too slow and imprecise)
  const h = ROLE_HEIGHT[role];
  const isStatic = opts.variant === 'graveyard';
  // world radius ~0.41 at BOARD_PIECE_SCALE: generous but never overlapping a neighbour
  const collider = new Mesh(new CylinderGeometry(0.5, 0.5, h * 1.05, 12), new MeshBasicMaterial({ visible: false }));
  collider.name = `${id}@collider`;
  collider.position.y = (h * 1.05) / 2;
  collider.userData.isCollider = true;
  if (!isStatic) root.add(collider);
  const baseScale0 = opts.scale ?? (isStatic ? 1 : BOARD_PIECE_SCALE);
  root.scale.setScalar(baseScale0);

  // ---- animation
  const mixer = new AnimationMixer(model);
  const actions = new Map<ClipName, AnimationAction>();
  for (const name of [...CLIPS, ...OPTIONAL_CLIPS] as ClipName[]) {
    const clip = template.animations.find((c) => c.name === name);
    if (clip) actions.set(name, mixer.clipAction(clip));
    else if ((OPTIONAL_CLIPS as readonly string[]).includes(name)) continue; // optional clips: no error
    else contractError(`${id}: missing clip ${name}; using procedural fallback`);
  }
  let mode: 'free' | 'scrub' = 'free';
  let scrubbing: ClipName | null = null;
  let dim = 0;
  let highlight = false;
  let fade = 1;
  let baseScale = baseScale0;
  let disposed = false;

  const squareObj = { value: opts.square };
  const p0 = squareToWorld(opts.square);
  root.position.copy(p0);
  root.rotation.y = restYaw(side);

  function applyMaterials() {
    for (const s of matStates) {
      if (s.color && s.mat.color) {
        s.mat.color.copy(s.color).lerp(DIM_COLOR, dim * 0.72);
        // Atlas materials mask the emissive term, so the selection glow is a warm brightening of the albedo.
        if (highlight) s.mat.color.lerp(HIGHLIGHT, 0.22 * (1 - dim)).multiplyScalar(1.22);
      }
      if (s.emissive && s.mat.emissive) {
        s.mat.emissive.copy(s.emissive).multiplyScalar(1 - dim * 0.9);
        if (highlight && !(s.mat as { emissiveMap?: unknown }).emissiveMap) s.mat.emissive.add(_c.copy(HIGHLIGHT).multiplyScalar(0.32 * (1 - dim)));
      }
    }
  }

  function stopAllExcept(keep: AnimationAction | undefined, fade: number) {
    for (const a of actions.values()) {
      if (a === keep) continue;
      if (fade > 0 && a.isRunning()) a.fadeOut(fade); else a.stop();
    }
  }

  const actor: PieceActorImpl = {
    id, faction, role, side, root, model, extras, sockets, collider,
    get meshes() { return meshes; },
    get square() { return squareObj.value; },
    set square(v: Square) { squareObj.value = v; },
    get mode() { return mode; },
    get fade() { return fade; },
    get isStatic() { return isStatic; },
    get baseScale() { return baseScale; },
    set baseScale(v: number) { baseScale = v; },
    pendingDt: 0,

    hasClip: (c) => actions.has(c),
    clipDuration: (c) => actions.get(c)?.getClip().duration ?? 0,

    play(clip, o = {}) {
      const a = actions.get(clip);
      if (!a) { contractError(`${id}: play(${clip}) but the clip is missing`); return null; }
      const loop = o.loop ?? LOOPING_CLIPS.includes(clip);
      const fade = o.fade ?? 0.2;
      stopAllExcept(a, fade);
      a.reset();
      a.setLoop(loop ? LoopRepeat : LoopOnce, loop ? Infinity : 1);
      a.clampWhenFinished = !loop;
      a.enabled = true;
      a.setEffectiveTimeScale(1);
      a.setEffectiveWeight(1);
      if (fade > 0) a.fadeIn(fade);
      a.play();
      mode = 'free';
      scrubbing = null;
      return a;
    },

    scrub(clip, time) {
      const a = actions.get(clip);
      if (!a) return;
      const dur = a.getClip().duration;
      if (mode !== 'scrub' || scrubbing !== clip) {
        stopAllExcept(a, 0);
        a.reset();
        a.setLoop(LoopOnce, 1);
        a.clampWhenFinished = true;
        a.enabled = true;
        a.setEffectiveWeight(1);
        a.play();
        a.paused = true;
        mode = 'scrub';
        scrubbing = clip;
      }
      a.time = Math.min(Math.max(time, 0), dur);
      mixer.update(0);
    },

    attackTimeline(): Timeline {
      if (actions.has('Attack')) return scrubTimeline('Attack', extras.impactTime);
      // Procedural lunge: wind up, thrust forward on the model (root belongs to the choreography), recover.
      const tl = gsap.timeline();
      const t = Math.max(extras.impactTime, 0.4);
      tl.to(model.position, { z: -0.12, y: 0.04, duration: t * 0.6, ease: 'power2.out' }, 0);
      tl.to(model.position, { z: 0.35, y: 0, duration: t * 0.4, ease: 'power3.in' }, t * 0.6);
      tl.to(model.position, { z: 0, duration: 0.35, ease: 'power2.out' }, t);
      tl.addLabel('impact', t);
      return tl;
    },

    clipTimeline(clip): Timeline {
      if (actions.has(clip)) return scrubTimeline(clip);
      const tl = gsap.timeline();
      if (clip === 'HitReact') {
        tl.to(model.position, { x: 0.07, z: -0.08, duration: 0.05, ease: 'power1.out' })
          .to(model.position, { x: -0.05, duration: 0.07 })
          .to(model.position, { x: 0, z: 0, duration: 0.18, ease: 'power2.out' });
      } else if (clip === 'Victory') {
        tl.to(model.position, { y: 0.25, duration: 0.25, ease: 'power2.out' })
          .to(model.position, { y: 0, duration: 0.25, ease: 'bounce.out' })
          .to(model.position, { y: 0.18, duration: 0.2, ease: 'power2.out' })
          .to(model.position, { y: 0, duration: 0.2, ease: 'bounce.out' });
      } else {
        tl.to({}, { duration: 0.5 });
      }
      return tl;
    },

    socketWorld(name, target) {
      const s = sockets[name];
      if (s) { s.updateWorldMatrix(true, false); return s.getWorldPosition(target); }
      const frac: Record<SocketName, number> = { socket_weapon_R: 0.6, socket_cast: 0.75, socket_impact: 0.5, socket_head: 1 };
      root.updateWorldMatrix(true, false);
      return target.set(0, h * frac[name], 0).applyMatrix4(root.matrixWorld);
    },

    setYaw(yaw) { root.rotation.y = yaw; },
    getYaw: () => root.rotation.y,

    setDim(amount) { dim = Math.min(Math.max(amount, 0), 1); applyMaterials(); },
    setHighlight(on) { highlight = on; applyMaterials(); },

    setFade(alpha) {
      const a = Math.min(Math.max(alpha, 0), 1);
      if (a === fade) return;
      const wasShadow = fade >= 0.6;
      fade = a;
      model.visible = a > 0.001;
      if (a >= 1) {
        for (const s of matStates) { s.mat.transparent = s.transparent; s.mat.opacity = s.opacity; s.mat.depthWrite = s.depthWrite; }
      } else {
        for (const s of matStates) { s.mat.transparent = true; s.mat.opacity = s.opacity * a; s.mat.depthWrite = a >= 0.5 ? s.depthWrite : false; }
      }
      const shadow = a >= 0.6;
      if (shadow !== wasShadow) for (const m of meshesAll) m.castShadow = shadow;
    },

    setWeaponSummon(scale) {
      if (!summonNode) return;
      summonNode.scale.setScalar(Math.max(scale, 0));
      summonNode.visible = scale > 0.001;
    },

    update(dt) {
      if (disposed) return;
      mixer.update(dt);
    },

    setLod,

    resetPose() {
      model.position.set(0, 0, 0);
      model.rotation.set(0, 0, 0);
      dim = 0; highlight = false; applyMaterials(); actor.setFade(1);
      actor.setWeaponSummon(0);
      if (mode === 'scrub' || !actions.get('Idle')?.isRunning()) {
        if (actions.has('Idle')) actor.play('Idle', { fade: 0.15 });
        else { mode = 'free'; scrubbing = null; }
      }
    },

    dispose() {
      if (disposed) return;
      disposed = true;
      mixer.stopAllAction();
      mixer.uncacheRoot(model);
      root.parent?.remove(root);
      for (const s of matStates) s.mat.dispose();
      collider.geometry.dispose();
      (collider.material as Material).dispose();
    },
  };

  function scrubTimeline(clip: ClipName, impactTime?: number): Timeline {
    const dur = Math.max(actions.get(clip)!.getClip().duration, 0.01);
    const tl = gsap.timeline();
    const proxy = { t: 0 };
    tl.call(() => actor.scrub(clip, 0), [], 0);
    tl.to(proxy, { t: dur, duration: dur, ease: 'none', onUpdate: () => actor.scrub(clip, proxy.t) }, 0);
    if (impactTime !== undefined) tl.addLabel('impact', impactTime);
    return tl;
  }

  if (isStatic) {
    // Graveyard display: pose once at the end of Surrender (kneeling, weapon on the ground), then freeze. No mixer updates after this.
    const sur = actions.get('Surrender');
    if (sur) {
      sur.reset(); sur.setLoop(LoopOnce, 1); sur.clampWhenFinished = true; sur.enabled = true; sur.play();
      sur.time = sur.getClip().duration;
      sur.paused = true;
      mixer.update(0);
    } else {
      contractError(`${id}: no Surrender clip; graveyard piece uses a procedural kneel`);
      actions.get('Idle')?.play();
      mixer.update(0);
      model.position.y = -0.18 * h; model.rotation.x = 0.38; model.scale.y = 0.88;
    }
    setLod(1);
    dim = 0.3;
    root.updateMatrixWorld(true);
    model.traverse((o) => { o.matrixAutoUpdate = false; });
    collider.visible = false;
    for (const m of meshesAll) m.castShadow = true;
  } else {
    // start idling at a random phase so a board of pieces does not breathe in lockstep
    const idle = actions.get('Idle');
    if (idle) {
      actor.play('Idle', { fade: 0 });
      idle.time = Math.random() * idle.getClip().duration;
    } else {
      contractError(`${id}: no Idle clip; actor will stand still`);
    }
  }
  applyMaterials();
  return actor;
}
