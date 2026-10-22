#!/usr/bin/env node
// meshopt_pack.mjs - post-process a forge GLB with EXT_meshopt_compression (the game's GLTFLoader already has MeshoptDecoder).
//
//   node tools/forge/meshopt_pack.mjs in.glb out.glb          (or:  ... - -   to use stdin / stdout)
//
// What it does (and nothing else):
//   * reorders each primitive's vertices for cache / compression (meshopt reorderMesh) and drops unused vertices
//   * compresses every vertex / index / animation / inverse-bind bufferView with the meshopt codec
//   * float attributes use the EXPONENTIAL filter (fixed point with a shared exponent per component): positions 14 bit,
//     normals 10 bit, UVs 15 bit, animation outputs 14 bit  -> sub-0.1 mm positions, <0.1 deg normals
//   * accessor types / min / max are left exactly as written by gltf_writer.py, so the accessors stay float32 / ubyte
//     (no KHR_mesh_quantization needed, validate_glb.py reads the same min/max, three.js decodes back to the same layout)
//   * images stay in the BIN chunk (buffer 0) untouched; compressed views get a fallback-less buffer 1 as the spec requires
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const enc = path.resolve(here, '..', '..', 'node_modules', 'meshoptimizer', 'meshopt_encoder.js');
const { MeshoptEncoder } = await import(pathToFileURL(enc).href);
await MeshoptEncoder.ready;

const [, , inArg, outArg] = process.argv;
const readAll = () => { const chunks = []; const fd = 0; const buf = Buffer.alloc(1 << 20); let n; while ((n = fs.readSync(fd, buf, 0, buf.length, null)) > 0) chunks.push(Buffer.from(buf.subarray(0, n))); return Buffer.concat(chunks); };
const glb = inArg === '-' ? readAll() : fs.readFileSync(inArg);

// ---------------------------------------------------------------- parse
if (glb.readUInt32LE(0) !== 0x46546c67) throw new Error('not a GLB');
const jlen = glb.readUInt32LE(12);
const json = JSON.parse(glb.subarray(20, 20 + jlen).toString('utf8'));
const bstart = 20 + jlen + 8;
const bin = glb.subarray(bstart, bstart + glb.readUInt32LE(20 + jlen));

const CT = { 5120: Int8Array, 5121: Uint8Array, 5122: Int16Array, 5123: Uint16Array, 5125: Uint32Array, 5126: Float32Array };
const NC = { SCALAR: 1, VEC2: 2, VEC3: 3, VEC4: 4, MAT4: 16 };
const view = (bvIdx) => { const v = json.bufferViews[bvIdx]; return bin.subarray(v.byteOffset || 0, (v.byteOffset || 0) + v.byteLength); };
function accData(ai) {
  const a = json.accessors[ai]; const T = CT[a.componentType]; const n = a.count * NC[a.type];
  const b = view(a.bufferView);
  const copy = new Uint8Array(n * T.BYTES_PER_ELEMENT); copy.set(b.subarray((a.byteOffset || 0), (a.byteOffset || 0) + copy.length));
  return new T(copy.buffer);
}

// which accessor is used for what
const role = new Map();                 // accessor -> {kind, attr}
const prims = [];
for (const m of json.meshes || []) for (const p of m.primitives) prims.push(p);
for (const p of prims) {
  for (const [k, a] of Object.entries(p.attributes)) role.set(a, { kind: 'attr', attr: k });
  if (p.indices !== undefined) role.set(p.indices, { kind: 'index' });
}
for (const an of json.animations || []) for (const s of an.samplers) { role.set(s.input, { kind: 'anim_in' }); role.set(s.output, { kind: 'anim_out' }); }
for (const sk of json.skins || []) if (sk.inverseBindMatrices !== undefined) role.set(sk.inverseBindMatrices, { kind: 'ibm' });

// ---------------------------------------------------------------- vertex reorder per primitive
const newData = new Map();              // accessor index -> typed array (after reorder)
const newCount = new Map();
for (const p of prims) {
  if (p.indices === undefined || (p.mode ?? 4) !== 4) continue;
  const idx = accData(p.indices);
  const vcount = json.accessors[p.attributes.POSITION].count;
  const idx32 = Uint32Array.from(idx);
  const [remap, unique] = MeshoptEncoder.reorderMesh(idx32, true, false);   // remaps idx32 in place, returns old->new
  const nidx = idx.constructor === Uint16Array && unique < 65536 ? Uint16Array.from(idx32) : idx32;
  newData.set(p.indices, nidx);
  for (const a of Object.values(p.attributes)) {
    const acc = json.accessors[a]; const nc = NC[acc.type]; const src = accData(a);
    const dst = new src.constructor(unique * nc);
    for (let i = 0; i < vcount; i++) { const j = remap[i]; if (j === 0xffffffff || j >= unique) continue; for (let c = 0; c < nc; c++) dst[j * nc + c] = src[i * nc + c]; }
    newData.set(a, dst); newCount.set(a, unique);
  }
}

// ---------------------------------------------------------------- encode
const EXP_BITS = { POSITION: 14, NORMAL: 10, TEXCOORD_0: 15, TEXCOORD_1: 15 };
const out = [];                          // {bv index, bytes}
let fallbackOff = 0;
const newViews = [];
const imageViewIdx = new Set((json.images || []).map((i) => i.bufferView).filter((x) => x !== undefined));
const accView = new Map();
for (const [ai, r] of role) accView.set(json.accessors[ai].bufferView, ai);

const encodedBytes = new Map();          // bufferView -> {bytes, stride, count, mode, filter}
for (const [ai, r] of role) {
  const a = json.accessors[ai];
  if (a.bufferView === undefined || a.byteOffset) continue;       // writer makes one view per accessor
  let data = newData.get(ai) ?? accData(ai);
  const count = newCount.get(ai) ?? a.count;
  a.count = count;
  const nc = NC[a.type]; const esize = CT[a.componentType].BYTES_PER_ELEMENT; const stride = nc * esize;
  let bytes, mode = 'ATTRIBUTES', filter;
  if (r.kind === 'index') {
    bytes = MeshoptEncoder.encodeIndexBuffer(new Uint8Array(data.buffer, data.byteOffset, data.byteLength), count, esize);
    mode = 'TRIANGLES';
  } else if (a.componentType === 5126 && (r.kind === 'attr' && EXP_BITS[r.attr] || r.kind === 'anim_out')) {
    const bits = r.kind === 'anim_out' ? 14 : EXP_BITS[r.attr];
    const f = MeshoptEncoder.encodeFilterExp(data, count, stride, bits, 'SharedComponent');
    bytes = MeshoptEncoder.encodeVertexBuffer(f, count, stride); filter = 'EXPONENTIAL';
  } else {
    if (stride % 4) continue;
    bytes = MeshoptEncoder.encodeVertexBuffer(new Uint8Array(data.buffer, data.byteOffset, data.byteLength), count, stride);
  }
  encodedBytes.set(a.bufferView, { bytes, stride, count, mode, filter, origLen: count * stride, target: json.bufferViews[a.bufferView].target });
}

// ---------------------------------------------------------------- rebuild buffers
const pad4 = (n) => (n + 3) & ~3;
const chunks = []; let off = 0;
const place = (b) => { const o = off; chunks.push(Buffer.from(b)); off += b.length; const p = pad4(off) - off; if (p) { chunks.push(Buffer.alloc(p)); off += p; } return o; };
let fb = 0;
const views = json.bufferViews.map((v, i) => {
  const e = encodedBytes.get(i);
  if (!e) { const o = place(view(i)); return { ...v, buffer: 0, byteOffset: o, byteLength: v.byteLength }; }
  const o = place(e.bytes);
  const nv = { buffer: 1, byteOffset: fb, byteLength: e.origLen };
  fb += pad4(e.origLen);
  if (e.mode !== 'TRIANGLES') nv.byteStride = e.stride;
  if (e.target) nv.target = e.target;
  const ext = { buffer: 0, byteOffset: o, byteLength: e.bytes.length, byteStride: e.stride, count: e.count, mode: e.mode };
  if (e.filter) ext.filter = e.filter;
  nv.extensions = { EXT_meshopt_compression: ext };
  return nv;
});
json.bufferViews = views;
json.buffers = [{ byteLength: off }, { byteLength: fb, extensions: { EXT_meshopt_compression: { fallback: true } } }];
json.extensionsUsed = [...new Set([...(json.extensionsUsed || []), 'EXT_meshopt_compression'])].sort();
json.extensionsRequired = [...new Set([...(json.extensionsRequired || []), 'EXT_meshopt_compression'])];
const newBin = Buffer.concat(chunks);

let js = Buffer.from(JSON.stringify(json));
js = Buffer.concat([js, Buffer.alloc(pad4(js.length) - js.length, 0x20)]);
const nb = Buffer.concat([newBin, Buffer.alloc(pad4(newBin.length) - newBin.length)]);
const head = Buffer.alloc(12); head.writeUInt32LE(0x46546c67, 0); head.writeUInt32LE(2, 4); head.writeUInt32LE(12 + 8 + js.length + 8 + nb.length, 8);
const jh = Buffer.alloc(8); jh.writeUInt32LE(js.length, 0); jh.write('JSON', 4, 'latin1');
const bh = Buffer.alloc(8); bh.writeUInt32LE(nb.length, 0); bh.write('BIN\0', 4, 'latin1');
const result = Buffer.concat([head, jh, js, bh, nb]);
if (outArg === '-') fs.writeSync(1, result); else fs.writeFileSync(outArg, result);
