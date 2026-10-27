// The board: an original procedural build, entirely in code. Dark carved stone with bronze inlay on the
// Emberhold side that transitions to frosted obsidian on the Rime side, set in a thick labelled frame on
// a round dais. Tiles are one 64-instance InstancedMesh (used for picking). Also implements BoardApi.
import { gsap } from 'gsap';
import {
  BoxGeometry, Color, CylinderGeometry, ExtrudeGeometry, Group, InstancedMesh, Matrix4,
  Mesh, MeshBasicMaterial, MeshStandardMaterial, Object3D, PlaneGeometry, Raycaster, Shape, Path, Vector3,
  type Intersection, type Scene,
} from 'three';
import type { BoardApi, EventBus, Faction, KinematicsApi, PieceActor, Role, Square } from '../contracts';
import { BOARD_PIECE_SCALE, FILES, SIDE_FACTION, isLightSquare, squareToWorld, restYaw } from '../contracts';
import { createGraveyard, type CapturedPiece, type Graveyard } from './graveyard';
import { parsePlacement } from '../core/rules';
import type { AssetRegistryImpl } from '../assets/registry';
import type { PieceActorImpl } from '../assets/pieceActor';
import { FRAME_SIZE, makeContactShadowTexture, makeFrameTexture, makeInlayTexture, makeMarbleTexture, makeSlabTexture } from './boardTextures';

export interface BoardImpl extends BoardApi {
  readonly root: Group;
  readonly tiles: InstancedMesh;
  /** Raycast the tile mesh → square (null if the ray misses the playing surface). */
  pickSquare(ray: Raycaster): Square | null;
  /** Raycast the piece colliders → nearest actor. */
  pickActor(ray: Raycaster, exclude?: PieceActor): PieceActorImpl | null;
  allActors(): PieceActorImpl[];
  actorAt(sq: Square): PieceActorImpl | undefined;
  spawnActor(faction: Faction, role: Role, sq: Square): PieceActorImpl;
  /** Default LOD of pieces standing on the board (fighters of a capture are always upgraded to LOD0 while it plays). */
  setLod(lod: 0 | 1): void;
  /** Live presenter hint: the next capture is `from` x `to` (exact attacker/defender; otherwise inferred from the capture:begin event). */
  hintFight(from: Square, victimSquare: Square): void;
  /** Captured-pieces ledges: show these pieces (kneeling). A single added piece fades in; anything else rebuilds instantly. */
  syncGraveyard(captured: CapturedPiece[]): void;
  /** Ledge layout follows the camera aspect: beside the board in landscape, at the board ends in portrait. */
  setGraveyardLayout(layout: 'sides' | 'ends'): void;
  readonly graveyard: Graveyard;
  /** Notified on every tintSquare call so the markers can draw the tint in the active highlight style. */
  tintListener: ((sq: Square, color: number | null) => void) | null;
  /** Loading-time warm-up: renders once with every LOD0 mesh, hidden queen weapon and fade (transparent) variant visible so nothing compiles or uploads mid-game. */
  prewarm(render: () => void): void;
  /** Per-frame update (actor mixers). dt already scaled by gsap time scale. */
  update(dt: number): void;
}

export interface BoardOptions {
  scene: Scene;
  registry: AssetRegistryImpl;
  /** Inlay/frame texture resolution (1024 on mobile). */
  textureSize?: number;
  /** Procedural animation layer: actors are attached on spawn and detached on removal. */
  kinematics?: KinematicsApi;
  /** Event bus (capture:begin / capture:end drive the LOD0 upgrade of the two fighters). */
  bus?: EventBus;
  /** Idle mixers update every other frame when true (CPU saver on weak devices). */
  halfRateIdle?: boolean;
}

// Bone marble / pale cool marble on light squares; basalt / blue slate on dark squares.
const TILE_LIGHT_EMBER = new Color(0xcdbd9c), TILE_DARK_EMBER = new Color(0x54453a);
const TILE_LIGHT_RIME = new Color(0xb9cbd9), TILE_DARK_RIME = new Color(0x364760);

const idx = (sq: Square) => (Number(sq[1]) - 1) * 8 + FILES.indexOf(sq[0]);
const sqOfIndex = (i: number): Square => FILES[i % 8] + String(Math.floor(i / 8) + 1);

export function createBoard(opts: BoardOptions): BoardImpl {
  const { scene, registry } = opts;
  const texSize = opts.textureSize ?? 2048;
  const root = new Group();
  root.name = 'board';
  scene.add(root);

  // ---------- base: dark body + a metal grid plate (bronze → frosted silver) that shows through the tile gaps
  const body = new Mesh(new BoxGeometry(8.1, 0.3, 8.1), new MeshStandardMaterial({ color: 0x2c241d, roughness: 0.8, metalness: 0.2 }));
  body.position.y = -0.1 - 0.15 - 0.02;
  body.receiveShadow = true;
  root.add(body);
  const plate = new Mesh(
    new PlaneGeometry(8.06, 8.06).rotateX(-Math.PI / 2),
    new MeshStandardMaterial({ map: makeSlabTexture(256), metalness: 0.95, roughness: 0.28 }),
  );
  plate.position.y = -0.1;
  plate.receiveShadow = true;
  plate.raycast = () => undefined;
  root.add(plate);

  // ---------- tiles: bevelled stone slabs, one continuous marble texture sampled by world position
  const TILE = 0.93, BEVEL = 0.025, DEPTH = 0.14;
  const sq = new Shape();
  sq.moveTo(-TILE / 2, -TILE / 2); sq.lineTo(TILE / 2, -TILE / 2); sq.lineTo(TILE / 2, TILE / 2); sq.lineTo(-TILE / 2, TILE / 2); sq.closePath();
  const tileGeo = new ExtrudeGeometry(sq, { depth: DEPTH, bevelEnabled: true, bevelThickness: BEVEL, bevelSize: BEVEL, bevelSegments: 1, curveSegments: 1 });
  tileGeo.rotateX(-Math.PI / 2);
  tileGeo.translate(0, -(DEPTH + BEVEL), 0); // top surface at y = 0
  const tileMat = new MeshStandardMaterial({ map: makeMarbleTexture(Math.min(texSize, 2048)), roughness: 0.36, metalness: 0.06, envMapIntensity: 0.9 });
  tileMat.onBeforeCompile = (shader) => {
    // Sample the board-sized marble map by world x/z instead of per-tile UVs.
    shader.vertexShader = shader.vertexShader.replace('#include <uv_vertex>', `#include <uv_vertex>
#ifdef USE_MAP
  vec4 bcWorld = modelMatrix * instanceMatrix * vec4(position, 1.0);
  vMapUv = vec2(bcWorld.x / 8.0 + 0.5, 0.5 - bcWorld.z / 8.0);
#endif`);
  };
  const tiles = new InstancedMesh(tileGeo, tileMat, 64);
  tiles.name = 'tiles';
  tiles.receiveShadow = true;
  const baseColors: Color[] = [];
  const m4 = new Matrix4();
  const tmpC = new Color();
  for (let i = 0; i < 64; i++) {
    const sqn = sqOfIndex(i);
    const p = squareToWorld(sqn);
    tiles.setMatrixAt(i, m4.makeTranslation(p.x, 0, p.z));
    const rank = Math.floor(i / 8);
    const t = Math.min(Math.max((rank - 1.5) / 4, 0), 1); // Emberhold → Rime transition across the middle ranks
    const light = isLightSquare(sqn);
    const col = (light
      ? tmpC.copy(TILE_LIGHT_EMBER).lerp(TILE_LIGHT_RIME, t)
      : tmpC.copy(TILE_DARK_EMBER).lerp(TILE_DARK_RIME, t)).clone();
    col.multiplyScalar(0.94 + ((i * 7919) % 13) / 13 * 0.12); // slight per-slab variation
    baseColors.push(col);
    tiles.setColorAt(i, col);
  }
  tiles.instanceMatrix.needsUpdate = true;
  tiles.instanceColor!.needsUpdate = true;
  root.add(tiles);

  // ---------- inlay overlay (transparent): bronze rules near White, rime frost near Black
  const inlayTex = makeInlayTexture(texSize);
  const inlay = new Mesh(
    new PlaneGeometry(8, 8).rotateX(-Math.PI / 2),
    new MeshStandardMaterial({
      map: inlayTex, transparent: true, depthWrite: false, roughness: 0.45, metalness: 0.5,
      polygonOffset: true, polygonOffsetFactor: -2, polygonOffsetUnits: -2,
    }),
  );
  inlay.position.y = 0.003;
  inlay.receiveShadow = true;
  inlay.renderOrder = 1;
  inlay.raycast = () => undefined;
  root.add(inlay);

  // ---------- frame (thick, bevelled, labelled)
  const outer = FRAME_SIZE / 2, inner = 4.06;
  const shape = new Shape();
  shape.moveTo(-outer, -outer); shape.lineTo(outer, -outer); shape.lineTo(outer, outer); shape.lineTo(-outer, outer); shape.closePath();
  const hole = new Path();
  hole.moveTo(-inner, -inner); hole.lineTo(-inner, inner); hole.lineTo(inner, inner); hole.lineTo(inner, -inner); hole.closePath();
  shape.holes.push(hole);
  const frameGeo = new ExtrudeGeometry(shape, { depth: 0.3, bevelEnabled: true, bevelThickness: 0.07, bevelSize: 0.07, bevelSegments: 2, curveSegments: 1 });
  frameGeo.rotateX(-Math.PI / 2);
  frameGeo.translate(0, 0.08 - (0.3 + 0.07), 0);
  const frameTex = makeFrameTexture(texSize);
  frameTex.repeat.set(1 / FRAME_SIZE, 1 / FRAME_SIZE);
  frameTex.offset.set(0.5, 0.5);
  const frame = new Mesh(frameGeo, [
    new MeshStandardMaterial({ map: frameTex, roughness: 0.5, metalness: 0.15 }),
    new MeshStandardMaterial({ color: 0x24170e, roughness: 0.55, metalness: 0.3 }),
  ]);
  frame.castShadow = true;
  frame.receiveShadow = true;
  frame.raycast = () => undefined;
  root.add(frame);

  // ---------- dais
  const daisMat = new MeshStandardMaterial({ color: 0x5a4d41, roughness: 0.72, metalness: 0.15 });
  const dais = new Mesh(new CylinderGeometry(9.0, 9.4, 0.55, 64), daisMat);
  dais.position.y = -0.36 - 0.275;
  dais.receiveShadow = true;
  dais.castShadow = true;
  root.add(dais);
  const daisRing = new Mesh(new CylinderGeometry(9.8, 10.2, 0.3, 64), new MeshStandardMaterial({ color: 0x40362e, roughness: 0.8, metalness: 0.15 }));
  daisRing.position.y = -0.95 - 0.1;
  daisRing.receiveShadow = true;
  root.add(daisRing);

  // ---------- actors
  const bySquare = new Map<Square, PieceActorImpl>();
  const actors = new Set<PieceActorImpl>();
  const actorList: PieceActorImpl[] = []; // iteration without allocating each frame
  const tints = new Map<Square, number>();
  const tintC = new Color();
  let clock = 0;
  let defaultLod: 0 | 1 = 1;
  let frameNo = 0;
  const addActor = (a: PieceActorImpl) => { actors.add(a); actorList.push(a); a.setLod(defaultLod); };
  const dropActor = (a: PieceActorImpl): boolean => {
    if (!actors.delete(a)) return false;
    actorList.splice(actorList.indexOf(a), 1);
    fighting.delete(a);
    return true;
  };

  // ---------- contact shadows: one instanced draw for every piece (cheap AO that also carries the Low tier)
  const BLOB_CAP = 48;
  const blobTex = makeContactShadowTexture(64);
  const blobs = new InstancedMesh(
    new PlaneGeometry(1, 1).rotateX(-Math.PI / 2),
    new MeshBasicMaterial({ map: blobTex, transparent: true, depthWrite: false, fog: false, polygonOffset: true, polygonOffsetFactor: -3, polygonOffsetUnits: -3 }),
    BLOB_CAP,
  );
  blobs.frustumCulled = false;
  blobs.renderOrder = 3;
  blobs.raycast = () => undefined;
  blobs.count = 0;
  root.add(blobs);
  const blobMat = blobs.instanceMatrix.array as Float32Array;
  const blobPrev = new Float32Array(BLOB_CAP * 4).fill(-1);
  let blobDirty = false;
  const writeBlob = (i: number, x: number, y: number, z: number, s: number) => {
    const k = i * 4;
    if (blobPrev[k] === x && blobPrev[k + 1] === y && blobPrev[k + 2] === z && blobPrev[k + 3] === s) return;
    blobPrev[k] = x; blobPrev[k + 1] = y; blobPrev[k + 2] = z; blobPrev[k + 3] = s;
    const o = i * 16;
    blobMat[o] = s; blobMat[o + 1] = 0; blobMat[o + 2] = 0; blobMat[o + 3] = 0;
    blobMat[o + 4] = 0; blobMat[o + 5] = s; blobMat[o + 6] = 0; blobMat[o + 7] = 0;
    blobMat[o + 8] = 0; blobMat[o + 9] = 0; blobMat[o + 10] = s; blobMat[o + 11] = 0;
    blobMat[o + 12] = x; blobMat[o + 13] = y; blobMat[o + 14] = z; blobMat[o + 15] = 1;
    blobDirty = true;
  };
  const BLOB_RADIUS = 1.15 / BOARD_PIECE_SCALE; // texture footprint in model units; scaled with the actor

  // ---------- fights: the two fighters of a capture are upgraded to LOD0 and full size while it plays
  const fighting = new Set<PieceActorImpl>();
  let hint: { attacker: PieceActorImpl; victim: PieceActorImpl; at: number } | null = null;
  const upgrade = (a: PieceActorImpl) => {
    if (fighting.has(a)) return;
    fighting.add(a);
    a.setLod(0);
    gsap.to(a.root.scale, { x: 1, y: 1, z: 1, duration: 0.3, ease: 'power2.out', overwrite: true });
  };
  const downgrade = (a: PieceActorImpl, animate: boolean) => {
    if (!fighting.delete(a)) return;
    gsap.killTweensOf(a.root.scale);
    const done = () => { if (!fighting.has(a)) a.setLod(defaultLod); };
    if (animate && actors.has(a)) gsap.to(a.root.scale, { x: a.baseScale, y: a.baseScale, z: a.baseScale, duration: 0.45, ease: 'power2.inOut', onComplete: done });
    else { a.root.scale.setScalar(a.baseScale); done(); }
  };
  const nearest = (faction: Faction, role: Role, to: Vector3, not: PieceActorImpl | undefined) => {
    let best: PieceActorImpl | undefined, bd = Infinity;
    for (const a of actorList) {
      if (a === not || a.faction !== faction || a.role !== role) continue;
      const d = Math.hypot(a.root.position.x - to.x, a.root.position.z - to.z);
      if (d < bd) { bd = d; best = a; }
    }
    return best;
  };
  const offBus = [
    opts.bus?.on('capture:begin', (e) => {
      let victim: PieceActorImpl | undefined, attacker: PieceActorImpl | undefined;
      if (hint && performance.now() - hint.at < 2000 && hint.victim.faction === e.defenderFaction && hint.victim.role === e.defender) { victim = hint.victim; attacker = hint.attacker; }
      hint = null;
      victim ??= bySquare.get(e.square);
      if (!victim || victim.role !== e.defender) victim = nearest(e.defenderFaction, e.defender, squareToWorld(e.square), undefined);
      attacker ??= nearest(e.attackerFaction, e.attacker, victim ? victim.root.position : squareToWorld(e.square), victim);
      if (victim) upgrade(victim);
      if (attacker) upgrade(attacker);
    }),
    opts.bus?.on('capture:end', () => { for (const a of [...fighting]) downgrade(a, true); }),
  ];

  // ---------- captured-pieces ledges
  const graveyard = createGraveyard({ root, registry, bus: opts.bus });

  const board: BoardImpl = {
    scene, root, tiles,

    actorAt: (sq) => bySquare.get(sq),
    allActors: () => actorList.slice(),

    setActorSquare(actor, sq) {
      const a = actor as PieceActorImpl;
      if (bySquare.get(a.square) === a) bySquare.delete(a.square);
      a.square = sq;
      bySquare.set(sq, a);
    },

    removeActor(actor) {
      // Idempotent: cinematics removes the defender before re-keying the attacker, and skip paths may call twice.
      const a = actor as PieceActorImpl;
      if (bySquare.get(a.square) === a) bySquare.delete(a.square);
      if (!dropActor(a)) return;
      opts.kinematics?.detach(a);
      a.dispose();
    },

    spawnActor(faction, role, sq) {
      const existing = bySquare.get(sq);
      if (existing) board.removeActor(existing);
      const a = registry.createActor(faction, role, sq);
      root.add(a.root);
      addActor(a);
      bySquare.set(sq, a);
      opts.kinematics?.attach(a);
      return a;
    },

    squareCenter: (sq, target) => squareToWorld(sq, target),

    tintSquare(sq, color) {
      const i = idx(sq);
      if (color === null) {
        tints.delete(sq);
        tiles.setColorAt(i, baseColors[i]);
      } else {
        tints.set(sq, color);
        tiles.setColorAt(i, tmpC.copy(baseColors[i]).lerp(tintC.set(color), 0.2));
      }
      tiles.instanceColor!.needsUpdate = true;
      board.tintListener?.(sq, color);
    },

    syncToFen(fen) {
      const want = parsePlacement(fen);
      const claimed = new Set<PieceActorImpl>();
      // 1. keep actors already on a square that expects exactly them
      for (const a of actors) {
        const w = want.get(a.square);
        if (w && w.side === a.side && w.role === a.role && bySquare.get(a.square) === a && !claimed.has(a)) claimed.add(a);
      }
      // 2. drop unclaimed actors from the index; reuse them for missing squares, else dispose
      const spare = [...actors].filter((a) => !claimed.has(a));
      for (const a of spare) if (bySquare.get(a.square) === a) bySquare.delete(a.square);
      for (const [sq, w] of want) {
        const have = bySquare.get(sq);
        if (have && claimed.has(have)) continue;
        const i = spare.findIndex((a) => a.side === w.side && a.role === w.role);
        let a: PieceActorImpl;
        if (i >= 0) { a = spare.splice(i, 1)[0]; a.square = sq; bySquare.set(sq, a); }
        else {
          const spawned = registry.createActor(SIDE_FACTION[w.side], w.role, sq);
          root.add(spawned.root);
          addActor(spawned);
          bySquare.set(sq, spawned);
          opts.kinematics?.attach(spawned);
          a = spawned;
        }
        claimed.add(a);
      }
      for (const a of spare) { dropActor(a); opts.kinematics?.detach(a); a.dispose(); }
      // 3. snap transforms and clean up leftover pose state (safety net after skipped sequences)
      const p = new Vector3();
      for (const a of claimed) {
        squareToWorld(a.square, p);
        const r = a.root;
        if (Math.abs(r.position.x - p.x) > 1e-3 || Math.abs(r.position.z - p.z) > 1e-3 || Math.abs(r.position.y) > 1e-3) r.position.set(p.x, 0, p.z);
        const yaw = restYaw(a.side);
        if (Math.abs(Math.atan2(Math.sin(r.rotation.y - yaw), Math.cos(r.rotation.y - yaw))) > 0.02) r.rotation.y = yaw;
        if (fighting.has(a)) downgrade(a, false);
        else if (r.scale.x !== a.baseScale) r.scale.setScalar(a.baseScale);
        r.visible = true;
        if (a.mode === 'scrub' || a.model.position.lengthSq() > 1e-6 || Math.abs(a.model.rotation.x) > 1e-4 || Math.abs(a.model.rotation.z) > 1e-4) a.resetPose();
        else { a.setDim(0); a.setHighlight(false); }
      }
    },

    pickSquare(ray) {
      const hits = ray.intersectObject(tiles, false);
      const id = hits[0]?.instanceId;
      return id === undefined ? null : sqOfIndex(id);
    },

    pickActor(ray, exclude) {
      const colliders: Object3D[] = [];
      for (const a of actors) if (a !== exclude) colliders.push(a.collider);
      const hits: Intersection[] = ray.intersectObjects(colliders, false);
      if (!hits.length) return null;
      const hit = hits[0].object;
      for (const a of actors) if (a.collider === hit) return a;
      return null;
    },

    setLod(lod) {
      defaultLod = lod;
      registry.lod = lod;
      for (const a of actorList) if (!fighting.has(a)) a.setLod(lod);
    },

    hintFight(from, victimSquare) {
      const attacker = bySquare.get(from), victim = bySquare.get(victimSquare);
      hint = attacker && victim ? { attacker, victim, at: performance.now() } : null;
    },

    prewarm(render) {
      const seen = new Set<string>();
      for (const a of actorList) {
        a.setLod(0);
        if (a.role === 'queen') a.setWeaponSummon(0.01);
        if (!seen.has(a.id)) { seen.add(a.id); a.setFade(0.5); }
      }
      try { render(); } finally {
        for (const a of actorList) {
          a.setLod(fighting.has(a) ? 0 : defaultLod);
          if (a.role === 'queen') a.setWeaponSummon(0);
          if (a.fade < 1) a.setFade(1);
        }
      }
    },

    tintListener: null,
    syncGraveyard(captured) { graveyard.sync(captured); },
    setGraveyardLayout(layout) { graveyard.setLayout(layout); },
    graveyard,

    update(dt) {
      frameNo++;
      const half = !!opts.halfRateIdle;
      for (let i = 0; i < actorList.length; i++) {
        const a = actorList[i];
        a.pendingDt += dt;
        // Idle (free-running) mixers on weak devices update every other frame, staggered per actor.
        if (half && a.mode === 'free' && ((frameNo + i) & 1)) continue;
        a.update(a.pendingDt);
        a.pendingDt = 0;
      }
      // contact shadows (one instanced draw)
      let n = 0;
      for (let i = 0; i < actorList.length && n < BLOB_CAP; i++) {
        const a = actorList[i];
        const r = a.root;
        const lift = Math.max(r.position.y, 0);
        const vis = r.visible && a.fade > 0.02;
        const sc = vis ? BLOB_RADIUS * r.scale.x * (1 - 0.4 * Math.min(lift / 1.6, 1)) * (a.fade < 0.5 ? a.fade * 2 : 1) : 0;
        writeBlob(n++, r.position.x, 0.008, r.position.z, sc);
      }
      if (blobs.count !== n) { blobs.count = n; blobDirty = true; }
      if (blobDirty) { blobs.instanceMatrix.needsUpdate = true; blobDirty = false; }
      clock += dt;
    },
  };
  void offBus;

  return board;
}
