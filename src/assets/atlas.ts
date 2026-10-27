// Draw-call reduction for piece templates. Every piece GLB ships each LOD as ~10 skinned primitives with ~10 PBR materials
// (3-4 small textures each). At load we bake those textures into one atlas set (base colour, occlusion/roughness/metal,
// normal, emissive), remap the UVs, and merge the primitives into at most two skinned meshes per LOD: one single-sided
// and one double-sided (cloth). Same skeleton, same skin weights - clones via SkeletonUtils keep working unchanged.
// Transmission (ice) is dropped: the transmission pass renders the whole scene a second time.
// Falls back to the untouched template (returns false) if anything is unexpected (UVs outside 0..1, mismatched attributes).
import {
  CanvasTexture, Color, LinearFilter, LinearMipmapLinearFilter, Material, Mesh, MeshStandardMaterial, SRGBColorSpace, SkinnedMesh,
  BufferAttribute, type BufferGeometry, type Object3D, type Texture,
} from 'three';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';
import { lodName } from '../contracts';

type StdLike = Material & {
  color?: Color; map?: Texture | null; aoMap?: Texture | null; roughnessMap?: Texture | null; metalnessMap?: Texture | null;
  normalMap?: Texture | null; emissiveMap?: Texture | null; emissive?: Color; emissiveIntensity?: number;
  roughness?: number; metalness?: number; vertexColors?: boolean;
};

export interface AtlasOptions {
  /** Pixel size of one material cell in the base / ORM atlas (normal + emissive use half). */
  cell: number;
  /** Anisotropy for the atlas textures. */
  anisotropy?: number;
}

const COLS = 4;
const PAD = 0.06; // fraction of a cell kept as gutter on every side (mip bleeding)

type Drawable = CanvasImageSource & { width: number; height: number };
const imageOf = (t: Texture | null | undefined): Drawable | null => {
  const img = t?.image as Drawable | undefined;
  return img && img.width ? img : null;
};

function makeCanvas(w: number, h: number): [HTMLCanvasElement, CanvasRenderingContext2D] {
  const c = document.createElement('canvas');
  c.width = w; c.height = h;
  return [c, c.getContext('2d', { willReadFrequently: false })!];
}

/** Draw `img` into a cell, tiled rx x ry times inside the padded area; the gutter shows the wrapped continuation (the source uses REPEAT). */
function drawCell(g: CanvasRenderingContext2D, img: Drawable | null, x: number, y: number, s: number, fill: string, mul?: string, rx = 1, ry = 1) {
  g.save();
  g.beginPath(); g.rect(x, y, s, s); g.clip();
  if (img) {
    const p = Math.round(s * PAD), tw = (s - 2 * p) / rx, th = (s - 2 * p) / ry;
    for (let j = -1; j <= ry; j++) for (let i = -1; i <= rx; i++) g.drawImage(img, x + p + i * tw, y + p + j * th, tw, th);
  } else {
    g.fillStyle = fill;
    g.fillRect(x, y, s, s);
  }
  if (mul) {
    g.globalCompositeOperation = 'multiply';
    g.fillStyle = mul;
    g.fillRect(x, y, s, s);
  }
  g.restore();
}

const css = (r: number, g: number, b: number) => `rgb(${Math.round(Math.min(r, 1) * 255)},${Math.round(Math.min(g, 1) * 255)},${Math.round(Math.min(b, 1) * 255)})`;
const isWhite = (c?: Color) => !c || (c.r > 0.995 && c.g > 0.995 && c.b > 0.995);
// canvas multiply happens in the stored (sRGB) space; factors are linear colours
const srgbCss = (c: Color) => { const s = c.clone().convertLinearToSRGB(); return css(s.r, s.g, s.b); };

function atlasTexture(canvas: HTMLCanvasElement, srgb: boolean, aniso: number): CanvasTexture {
  const t = new CanvasTexture(canvas);
  t.flipY = false; // UVs are glTF-convention (origin top-left)
  t.colorSpace = srgb ? SRGBColorSpace : '' as never;
  t.generateMipmaps = true;
  t.minFilter = LinearMipmapLinearFilter;
  t.magFilter = LinearFilter;
  t.anisotropy = aniso;
  return t;
}

function collectMeshes(root: Object3D | undefined): Mesh[] {
  const out: Mesh[] = [];
  root?.traverse((o) => { if ((o as Mesh).isMesh) out.push(o as Mesh); });
  return out;
}

const matOf = (m: Mesh): StdLike => (Array.isArray(m.material) ? m.material[0] : m.material) as StdLike;

/** Returns true when the template was merged. Safe to call once per template scene. */
export function bakePieceAtlas(scene: Object3D, id: string, opts: AtlasOptions): boolean {
  try { return bake(scene, id, opts); } catch (e) { console.warn(`[assets] atlas merge failed for ${id}; using original materials`, e); return false; }
}

function bake(scene: Object3D, id: string, opts: AtlasOptions): boolean {
  const lodRoots = [scene.getObjectByName(lodName(id as never, 0)), scene.getObjectByName(lodName(id as never, 1))];
  const perLod = lodRoots.map((r) => collectMeshes(r).filter((m) => (m as SkinnedMesh).isSkinnedMesh));
  const all = perLod.flat();
  const bail = (why: string) => { console.warn(`[assets] ${id}: atlas merge skipped (${why})`); return false; };
  if (!all.length) return bail('no skinned LOD meshes');
  const mats: StdLike[] = [];
  for (const m of all) { const mat = matOf(m); if (!mats.includes(mat)) mats.push(mat); }
  const rows = Math.ceil(mats.length / COLS);
  const cell = opts.cell, half = Math.max(16, Math.round(opts.cell / 2));
  const aniso = opts.anisotropy ?? 4;

  // ---- validate UV range (atlas cells assume 0..1) and attribute compatibility before touching anything
  // Per-material UV range: tiled textures (UVs beyond 0..1) are shifted by whole tiles to start at 0, uniformly shrunk so at most 4 tiles
  // per axis remain (coarser tiling, same proportions), and baked repeated into the material's cell.
  const ext = new Map<StdLike, { minU: number; minV: number; maxU: number; maxV: number }>();
  for (const m of all) {
    const uv = m.geometry.getAttribute('uv');
    if (!uv) return bail('missing uv');
    const e = ext.get(matOf(m)) ?? { minU: Infinity, minV: Infinity, maxU: -Infinity, maxV: -Infinity };
    for (let i = 0; i < uv.count; i++) {
      const u = uv.getX(i), v = uv.getY(i);
      if (u < e.minU) e.minU = u; if (u > e.maxU) e.maxU = u;
      if (v < e.minV) e.minV = v; if (v > e.maxV) e.maxV = v;
    }
    ext.set(matOf(m), e);
    if (Array.isArray(m.material) && m.material.length > 1) return bail('multi-material mesh');
  }
  const rep = new Map<StdLike, { ox: number; oy: number; f: number; x: number; y: number }>();
  for (const [mat, e] of ext) {
    const ox = -Math.floor(e.minU + 0.001), oy = -Math.floor(e.minV + 0.001);
    const su = e.maxU + ox, sv = e.maxV + oy;
    const f = Math.min(1, 4 / Math.max(su, sv, 1));
    rep.set(mat, { ox, oy, f, x: Math.max(1, Math.ceil(su * f - 0.02)), y: Math.max(1, Math.ceil(sv * f - 0.02)) });
  }
  const attrKey = (g: BufferGeometry) => Object.keys(g.attributes).sort().map((k) => { const a = g.attributes[k]; return `${k}:${a.itemSize}:${a.normalized}:${(a.array as { constructor: { name: string } }).constructor.name}`; }).join('|');
  const keys = new Set(all.map((m) => attrKey(m.geometry)));
  if (keys.size !== 1) {
    // Normalise colour/skin attributes to float where the array types differ.
    for (const m of all) normaliseAttributes(m.geometry);
    if (new Set(all.map((m) => attrKey(m.geometry))).size !== 1) return bail(`attribute mismatch: ${[...new Set(all.map((m) => attrKey(m.geometry)))].join(' ;; ')}`);
  }

  // ---- atlases
  const [bC, bG] = makeCanvas(COLS * cell, rows * cell);
  const [oC, oG] = makeCanvas(COLS * cell, rows * cell);
  const [nC, nG] = makeCanvas(COLS * half, rows * half);
  const hasEmissive = mats.some((m) => m.emissiveMap || (m.emissive && (m.emissive.r + m.emissive.g + m.emissive.b) > 0.01));
  const [eC, eG] = makeCanvas(COLS * half, rows * half);
  bG.fillStyle = '#fff'; bG.fillRect(0, 0, bC.width, bC.height);
  oG.fillStyle = '#fff'; oG.fillRect(0, 0, oC.width, oC.height);
  nG.fillStyle = 'rgb(128,128,255)'; nG.fillRect(0, 0, nC.width, nC.height);
  eG.fillStyle = '#000'; eG.fillRect(0, 0, eC.width, eC.height);
  const maxI = Math.max(1, ...mats.map((m) => (m.emissive && (m.emissive.r + m.emissive.g + m.emissive.b) > 0.01 ? m.emissiveIntensity ?? 1 : 0)));

  mats.forEach((m, i) => {
    const cx = (i % COLS), cy = Math.floor(i / COLS);
    const R = rep.get(m) ?? { ox: 0, oy: 0, f: 1, x: 1, y: 1 };
    drawCell(bG, imageOf(m.map), cx * cell, cy * cell, cell, srgbCss(m.color ?? new Color(1, 1, 1)), m.map && !isWhite(m.color) ? srgbCss(m.color!) : undefined, R.x, R.y);
    const orm = imageOf(m.aoMap) ?? imageOf(m.roughnessMap) ?? imageOf(m.metalnessMap);
    const rough = m.roughness ?? 1, metal = m.metalness ?? 0;
    drawCell(oG, orm, cx * cell, cy * cell, cell, css(1, rough, metal), orm && (rough < 0.995 || metal < 0.995) ? css(1, rough, metal) : undefined, R.x, R.y);
    drawCell(nG, imageOf(m.normalMap), cx * half, cy * half, half, 'rgb(128,128,255)', undefined, R.x, R.y);
    if (hasEmissive) {
      const e = m.emissive;
      const on = !!e && e.r + e.g + e.b > 0.01;
      if (on) {
        const k = (m.emissiveIntensity ?? 1) / maxI;
        drawCell(eG, imageOf(m.emissiveMap), cx * half, cy * half, half, srgbCss(e!), css(k * e!.r, k * e!.g, k * e!.b), R.x, R.y);
      }
    }
  });

  const baseTex = atlasTexture(bC, true, aniso);
  const ormTex = atlasTexture(oC, false, aniso);
  const normTex = atlasTexture(nC, false, aniso);
  const emisTex = hasEmissive ? atlasTexture(eC, true, aniso) : null;

  const uvRect = (mat: StdLike) => {
    const i = mats.indexOf(mat);
    const R = rep.get(mat) ?? { ox: 0, oy: 0, f: 1, x: 1, y: 1 };
    return { ox: (i % COLS + PAD) / COLS, oy: (Math.floor(i / COLS) + PAD) / rows, sx: (1 - 2 * PAD) / COLS / R.x, sy: (1 - 2 * PAD) / rows / R.y, f: R.f, shx: R.ox, shy: R.oy };
  };

  const vertexColors = mats.some((m) => m.vertexColors) || all.some((m) => !!m.geometry.getAttribute('color'));
  const makeMat = (side: number) => {
    const m = new MeshStandardMaterial({
      map: baseTex, aoMap: ormTex, roughnessMap: ormTex, metalnessMap: ormTex, normalMap: normTex, roughness: 1, metalness: 1,
      vertexColors, side: side as never,
    });
    if (emisTex) { m.emissiveMap = emisTex; m.emissive.setRGB(1, 1, 1); m.emissiveIntensity = maxI; }
    m.name = `${id}_atlas`;
    return m;
  };
  const singleMat = makeMat(0), doubleMat = makeMat(2);
  if (!all.some((m) => matOf(m).side === 2)) doubleMat.dispose();

  // ---- merge per LOD
  perLod.forEach((meshes, lod) => {
    const root = lodRoots[lod];
    if (!meshes.length || !root) return;
    const first = meshes[0] as SkinnedMesh;
    for (const side of [0, 2]) {
      const group = meshes.filter((m) => (matOf(m).side === 2) === (side === 2));
      if (!group.length) continue;
      const geos = group.map((m) => {
        const g = m.geometry.clone();
        const uv = g.getAttribute('uv') as BufferAttribute;
        const r = uvRect(matOf(m));
        const arr = new Float32Array(uv.count * 2);
        for (let i = 0; i < uv.count; i++) { arr[i * 2] = r.ox + (uv.getX(i) + r.shx) * r.f * r.sx; arr[i * 2 + 1] = r.oy + (uv.getY(i) + r.shy) * r.f * r.sy; }
        g.setAttribute('uv', new BufferAttribute(arr, 2));
        return g;
      });
      const merged = mergeGeometries(geos, false);
      geos.forEach((g) => g.dispose());
      if (!merged) throw new Error('mergeGeometries returned null');
      const sm = new SkinnedMesh(merged, side === 2 ? doubleMat : singleMat);
      sm.name = `${lodName(id as never, lod as 0 | 1)}_${side === 2 ? 'dbl' : 'sgl'}`;
      sm.bind(first.skeleton, first.bindMatrix);
      sm.bindMode = first.bindMode;
      sm.castShadow = true; sm.receiveShadow = true;
      sm.frustumCulled = false;
      (group[0].parent ?? root).add(sm);
    }
    for (const m of meshes) { m.parent?.remove(m); m.geometry.dispose(); }
  });

  // ---- release the originals (textures are now in the atlases), except materials still used by other meshes (e.g. the queen's summoned weapon)
  const stillUsed = new Set<Material>();
  scene.traverse((o) => {
    const mesh = o as Mesh;
    if (!mesh.isMesh) return;
    for (const mm of Array.isArray(mesh.material) ? mesh.material : [mesh.material]) stillUsed.add(mm);
  });
  for (const m of mats) {
    if (stillUsed.has(m)) continue;
    for (const t of [m.map, m.aoMap, m.roughnessMap, m.metalnessMap, m.normalMap, m.emissiveMap]) {
      if (!t) continue;
      t.dispose();
      (t.image as { close?: () => void } | undefined)?.close?.();
    }
    m.dispose();
  }
  return true;
}

/** Make colour/skin attributes uniform (Float32 colour, same skin index type) so geometries can be merged. */
function normaliseAttributes(g: BufferGeometry) {
  const c = g.getAttribute('color');
  if (c && !(c.array instanceof Float32Array)) {
    const out = new Float32Array(c.count * 3);
    for (let i = 0; i < c.count; i++) { out[i * 3] = c.getX(i); out[i * 3 + 1] = c.getY(i); out[i * 3 + 2] = c.getZ(i); }
    g.setAttribute('color', new (c.constructor as new (a: Float32Array, n: number) => BufferAttribute)(out, 3));
  }
  const w = g.getAttribute('skinWeight');
  if (w && !(w.array instanceof Float32Array)) {
    const out = new Float32Array(w.count * 4);
    for (let i = 0; i < w.count; i++) { out[i * 4] = w.getX(i); out[i * 4 + 1] = w.getY(i); out[i * 4 + 2] = w.getZ(i); out[i * 4 + 3] = w.getW(i); }
    g.setAttribute('skinWeight', new (w.constructor as new (a: Float32Array, n: number) => BufferAttribute)(out, 4));
  }
}
