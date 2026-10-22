// Asset registry (architecture §6): GLTFLoader + MeshoptDecoder, preloads the 12 piece GLBs with
// progress, clones them per actor with SkeletonUtils, and loads fragment sets lazily into a pool.
import { type Material, type Mesh, type Object3D, type Quaternion, type Vector3 } from 'three';
import { GLTFLoader, type GLTF } from 'three/addons/loaders/GLTFLoader.js';
import { MeshoptDecoder } from 'three/addons/libs/meshopt_decoder.module.js';
import type { AssetId, AssetRegistry, Faction, PieceActor, Role, Square } from '../contracts';
import { ALL_ASSET_IDS, assetId, fragmentsRootName, fragmentsUrl, modelUrl } from '../contracts';
import { createPieceActor, type PieceActorImpl, type PieceTemplate } from './pieceActor';

export interface AssetRegistryImpl extends AssetRegistry {
  /** 0 = full-detail, 1 = reduced mesh; applied to actors created from now on. */
  lod: 0 | 1;
  createActor(faction: Faction, role: Role, square: Square): PieceActorImpl;
  /** Fetch all fragment sets in the background so the first capture does not hitch. */
  warmFragments(onProgress?: (done: number, total: number) => void): Promise<void>;
  readonly ready: boolean;
}

interface RestEntry { o: Object3D; p: Vector3; q: Quaternion; s: Vector3 }
interface FragTemplate { root: Object3D; mats: Material[] }
interface FragInstance { rest: RestEntry[]; mats: Array<{ live: Material; orig: Material }> }

const baseUrl = () => (typeof import.meta !== 'undefined' && import.meta.env?.BASE_URL) || './';

export function createAssetRegistry(): AssetRegistryImpl {
  const loader = new GLTFLoader();
  loader.setMeshoptDecoder(MeshoptDecoder);

  const templates = new Map<AssetId, PieceTemplate>();
  const fragTemplates = new Map<AssetId, Promise<FragTemplate>>();
  const fragPool = new Map<AssetId, Object3D[]>();
  const fragInfo = new WeakMap<Object3D, FragInstance>();
  let ready = false;

  const load = (url: string): Promise<GLTF> => loader.loadAsync(baseUrl() + url);

  async function loadFragTemplate(id: AssetId): Promise<FragTemplate> {
    const gltf = await load(fragmentsUrl(id));
    const root = gltf.scene.getObjectByName(fragmentsRootName(id)) ?? gltf.scene;
    const mats = new Set<Material>();
    root.traverse((o) => { const m = o as Mesh; if (m.isMesh) (Array.isArray(m.material) ? m.material : [m.material]).forEach((x) => mats.add(x)); });
    return { root, mats: [...mats] };
  }

  function instantiateFragments(tpl: FragTemplate): Object3D {
    const obj = tpl.root.clone(true);
    const map = new Map<Material, Material>();
    const mats: FragInstance['mats'] = [];
    const swap = (m: Material) => {
      let c = map.get(m);
      if (!c) { c = m.clone(); map.set(m, c); mats.push({ live: c, orig: m }); }
      return c;
    };
    const rest: RestEntry[] = [];
    obj.traverse((o) => {
      rest.push({ o, p: o.position.clone(), q: o.quaternion.clone(), s: o.scale.clone() });
      const m = o as Mesh;
      if (m.isMesh) {
        m.material = Array.isArray(m.material) ? m.material.map(swap) : swap(m.material);
        m.castShadow = true;
        m.receiveShadow = true;
      }
    });
    obj.position.set(0, 0, 0);
    obj.quaternion.identity();
    obj.scale.set(1, 1, 1);
    fragInfo.set(obj, { rest, mats });
    return obj;
  }

  const registry: AssetRegistryImpl = {
    lod: 0,
    get ready() { return ready; },

    async preload(onProgress) {
      let done = 0;
      const total = ALL_ASSET_IDS.length;
      onProgress?.(0, total);
      await Promise.all(ALL_ASSET_IDS.map(async (id) => {
        const gltf = await load(modelUrl(id));
        templates.set(id, { scene: gltf.scene, animations: gltf.animations });
        onProgress?.(++done, total);
      }));
      ready = true;
    },

    createActor(faction, role, square) {
      const id = assetId(faction, role);
      const template = templates.get(id);
      if (!template) throw new Error(`[assets] ${id} not loaded; call preload() first`);
      return createPieceActor({ id, faction, role, square, template, lod: registry.lod });
    },

    async acquireFragments(id) {
      let tplP = fragTemplates.get(id);
      if (!tplP) { tplP = loadFragTemplate(id); fragTemplates.set(id, tplP); tplP.catch(() => fragTemplates.delete(id)); }
      const tpl = await tplP;
      const pooled = fragPool.get(id)?.pop();
      const obj = pooled ?? instantiateFragments(tpl);
      obj.visible = true;
      return obj;
    },

    releaseFragments(id, obj) {
      const info = fragInfo.get(obj);
      obj.parent?.remove(obj);
      if (!info) return;
      for (const r of info.rest) { r.o.position.copy(r.p); r.o.quaternion.copy(r.q); r.o.scale.copy(r.s); r.o.visible = true; }
      for (const m of info.mats) m.live.copy(m.orig);
      obj.position.set(0, 0, 0);
      obj.quaternion.identity();
      obj.scale.set(1, 1, 1);
      let pool = fragPool.get(id);
      if (!pool) fragPool.set(id, (pool = []));
      pool.push(obj);
    },

    async warmFragments(onProgress) {
      let n = 0;
      for (const id of ALL_ASSET_IDS) {
        let p = fragTemplates.get(id);
        if (!p) { p = loadFragTemplate(id); fragTemplates.set(id, p); p.catch(() => fragTemplates.delete(id)); }
        try { await p; } catch { /* retried lazily on first capture */ }
        onProgress?.(++n, ALL_ASSET_IDS.length);
        if (!onProgress) await new Promise((r) => setTimeout(r, 60)); // background warm-up: stay out of the way
      }
    },
  };
  return registry;
}

export type { PieceActor };
