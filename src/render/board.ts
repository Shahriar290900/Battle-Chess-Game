// The board: an original procedural build, entirely in code. Dark carved stone with bronze inlay on the
// Emberhold side that transitions to frosted obsidian on the Rime side, set in a thick labelled frame on
// a round dais. Tiles are one 64-instance InstancedMesh (used for picking). Also implements BoardApi.
import {
  AdditiveBlending, BoxGeometry, Color, CylinderGeometry, ExtrudeGeometry, Group, InstancedMesh, Matrix4,
  Mesh, MeshBasicMaterial, MeshStandardMaterial, Object3D, PlaneGeometry, Raycaster, Shape, Path, Sprite, SpriteMaterial, TorusGeometry, Vector3,
  type Intersection, type Scene,
} from 'three';
import type { BoardApi, Faction, PieceActor, Role, Square } from '../contracts';
import { FILES, SIDE_FACTION, isLightSquare, squareToWorld, restYaw } from '../contracts';
import { parsePlacement } from '../core/rules';
import type { AssetRegistryImpl } from '../assets/registry';
import type { PieceActorImpl } from '../assets/pieceActor';
import { FRAME_SIZE, makeFrameTexture, makeGlowTexture, makeInlayTexture, makeMarbleTexture, makeSlabTexture, makeTileGlowTexture } from './boardTextures';

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
  setLod(lod: 0 | 1): void;
  /** Per-frame update (actor mixers). dt already scaled by gsap time scale. */
  update(dt: number): void;
}

export interface BoardOptions {
  scene: Scene;
  registry: AssetRegistryImpl;
  /** Inlay/frame texture resolution (1024 on mobile). */
  textureSize?: number;
}

// Bone marble / pale cool marble on light squares; basalt / blue slate on dark squares.
const TILE_LIGHT_EMBER = new Color(0xb9a98c), TILE_DARK_EMBER = new Color(0x38332e);
const TILE_LIGHT_RIME = new Color(0xaab7c0), TILE_DARK_RIME = new Color(0x26303b);

const idx = (sq: Square) => (Number(sq[1]) - 1) * 8 + FILES.indexOf(sq[0]);
const sqOfIndex = (i: number): Square => FILES[i % 8] + String(Math.floor(i / 8) + 1);

export function createBoard(opts: BoardOptions): BoardImpl {
  const { scene, registry } = opts;
  const texSize = opts.textureSize ?? 2048;
  const root = new Group();
  root.name = 'board';
  scene.add(root);

  // ---------- base: dark body + a metal grid plate (bronze → frosted silver) that shows through the tile gaps
  const body = new Mesh(new BoxGeometry(8.1, 0.3, 8.1), new MeshStandardMaterial({ color: 0x14110e, roughness: 0.8, metalness: 0.2 }));
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
  const tileMat = new MeshStandardMaterial({ map: makeMarbleTexture(Math.min(texSize, 2048)), roughness: 0.34, metalness: 0.06, envMapIntensity: 1.4 });
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

  // ---------- tint glow quads (one per tile, scaled to 0 when idle)
  const glowTex = makeTileGlowTexture(128);
  const glowMat = new MeshBasicMaterial({ map: glowTex, transparent: true, depthWrite: false, blending: AdditiveBlending, opacity: 0.85 });
  const glow = new InstancedMesh(new PlaneGeometry(0.97, 0.97).rotateX(-Math.PI / 2), glowMat, 64);
  glow.position.y = 0.006;
  glow.renderOrder = 2;
  glow.frustumCulled = false;
  glow.raycast = () => undefined;
  const zero = new Matrix4().makeScale(0, 0, 0);
  for (let i = 0; i < 64; i++) { glow.setMatrixAt(i, zero); glow.setColorAt(i, tmpC.set(0)); }
  glow.instanceMatrix.needsUpdate = true;
  glow.instanceColor!.needsUpdate = true;
  root.add(glow);

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

  // ---------- corner braziers: small bronze (Emberhold) / silver (Rime) cups with a low flame
  const flames: Array<{ s: Sprite; base: number; phase: number }> = [];
  {
    const glowTex = makeGlowTexture(64);
    const cupBronze = new MeshStandardMaterial({ color: 0x6a4a28, roughness: 0.4, metalness: 0.85 });
    const cupSilver = new MeshStandardMaterial({ color: 0x6d7f8c, roughness: 0.35, metalness: 0.85 });
    const cupGeo = new CylinderGeometry(0.14, 0.08, 0.15, 12);
    const rimGeo = new TorusGeometry(0.14, 0.02, 6, 16).rotateX(Math.PI / 2);
    for (const mx of [-1, 1]) for (const mz of [-1, 1]) {
      const warm = mz > 0;
      const g = new Group();
      g.position.set(mx * 4.72, 0.09, mz * 4.72);
      const cup = new Mesh(cupGeo, warm ? cupBronze : cupSilver);
      cup.position.y = 0.075;
      cup.castShadow = true;
      const rim = new Mesh(rimGeo, warm ? cupBronze : cupSilver);
      rim.position.y = 0.15;
      const coal = new Mesh(new CylinderGeometry(0.11, 0.11, 0.02, 12), new MeshBasicMaterial({ color: warm ? 0xff7a1a : 0x6fd3ff }));
      coal.position.y = 0.14;
      g.add(cup, rim, coal);
      for (const [size, y, op, ph] of [[0.28, 0.3, 0.9, 0], [0.55, 0.36, 0.22, 1.9]] as const) {
        const sp = new Sprite(new SpriteMaterial({ map: glowTex, color: warm ? 0xff8a30 : 0x7fd8ff, transparent: true, opacity: op, blending: AdditiveBlending, depthWrite: false, fog: false }));
        sp.scale.set(size, size * 1.3, 1);
        sp.position.y = y;
        g.add(sp);
        flames.push({ s: sp, base: size, phase: ph + mx + mz * 2 });
      }
      root.add(g);
    }
  }

  // ---------- dais
  const daisMat = new MeshStandardMaterial({ color: 0x0e0b09, roughness: 0.8, metalness: 0.2 });
  const dais = new Mesh(new CylinderGeometry(7.9, 8.3, 0.55, 64), daisMat);
  dais.position.y = -0.36 - 0.275;
  dais.receiveShadow = true;
  dais.castShadow = true;
  root.add(dais);
  const daisRing = new Mesh(new CylinderGeometry(8.6, 8.9, 0.3, 64), new MeshStandardMaterial({ color: 0x0a0807, roughness: 0.85, metalness: 0.15 }));
  daisRing.position.y = -0.95 - 0.1;
  daisRing.receiveShadow = true;
  root.add(daisRing);

  // ---------- actors
  const bySquare = new Map<Square, PieceActorImpl>();
  const actors = new Set<PieceActorImpl>();
  const tints = new Map<Square, number>();
  let clock = 0;

  const board: BoardImpl = {
    scene, root, tiles,

    actorAt: (sq) => bySquare.get(sq),
    allActors: () => [...actors],

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
      if (!actors.delete(a)) return;
      a.dispose();
    },

    spawnActor(faction, role, sq) {
      const existing = bySquare.get(sq);
      if (existing) board.removeActor(existing);
      const a = registry.createActor(faction, role, sq);
      root.add(a.root);
      actors.add(a);
      bySquare.set(sq, a);
      return a;
    },

    squareCenter: (sq, target) => squareToWorld(sq, target),

    tintSquare(sq, color) {
      const i = idx(sq);
      if (color === null) {
        tints.delete(sq);
        glow.setMatrixAt(i, zero);
        tiles.setColorAt(i, baseColors[i]);
      } else {
        tints.set(sq, color);
        const p = squareToWorld(sq);
        glow.setMatrixAt(i, m4.makeTranslation(p.x, 0, p.z));
        glow.setColorAt(i, tmpC.set(color));
        tiles.setColorAt(i, tmpC.copy(baseColors[i]).lerp(new Color(color), 0.28));
      }
      glow.instanceMatrix.needsUpdate = true;
      glow.instanceColor!.needsUpdate = true;
      tiles.instanceColor!.needsUpdate = true;
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
          actors.add(spawned);
          bySquare.set(sq, spawned);
          a = spawned;
        }
        claimed.add(a);
      }
      for (const a of spare) { actors.delete(a); a.dispose(); }
      // 3. snap transforms and clean up leftover pose state (safety net after skipped sequences)
      const p = new Vector3();
      for (const a of claimed) {
        squareToWorld(a.square, p);
        const r = a.root;
        if (Math.abs(r.position.x - p.x) > 1e-3 || Math.abs(r.position.z - p.z) > 1e-3 || Math.abs(r.position.y) > 1e-3) r.position.set(p.x, 0, p.z);
        const yaw = restYaw(a.side);
        if (Math.abs(Math.atan2(Math.sin(r.rotation.y - yaw), Math.cos(r.rotation.y - yaw))) > 0.02) r.rotation.y = yaw;
        if (r.scale.x !== 1) r.scale.setScalar(1);
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
      registry.lod = lod;
      for (const a of actors) a.setLod(lod);
    },

    update(dt) {
      for (const a of actors) a.update(dt);
      clock += dt;
      for (const f of flames) {
        const k = 1 + Math.sin(clock * 9 + f.phase) * 0.12 + Math.sin(clock * 15 + f.phase * 2) * 0.06;
        f.s.scale.set(f.base * (1 + (k - 1) * 0.5), f.base * 1.3 * k, 1);
      }
    },
  };

  return board;
}
