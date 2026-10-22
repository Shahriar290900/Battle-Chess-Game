// FX sandbox: board + placeholder pieces + a button per effect. Served by `npx vite` at /sandbox/fx.html.
import { gsap } from 'gsap';
import {
  ACESFilmicToneMapping, AmbientLight, CanvasTexture, Color, DirectionalLight, Group, HemisphereLight, Mesh, MeshStandardMaterial,
  Object3D, PerspectiveCamera, PlaneGeometry, Scene, SRGBColorSpace, Vector3, WebGLRenderer,
} from 'three';
import { clone as skClone } from 'three/examples/jsm/utils/SkeletonUtils.js';
import { MeshoptDecoder } from 'three/examples/jsm/libs/meshopt_decoder.module.js';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';
import { createFx, emitFaction } from '../src/fx';
import { createPost } from '../src/render/post';
import { GRAPHICS_PRESETS, type Faction, type GraphicsSettings, type ParticlePreset, type PieceActor, type QualityTier, type Role } from '../src/contracts';

const renderer = new WebGLRenderer({ antialias: false, powerPreference: 'high-performance' });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.toneMapping = ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.0;
renderer.shadowMap.enabled = true;
document.body.prepend(renderer.domElement);

const scene = new Scene();
scene.background = new Color(0x07090c);
const camera = new PerspectiveCamera(42, 1, 0.1, 100);
camera.position.set(0, 3.4, 6.2);
camera.lookAt(0, 0.6, 0);

// lights: warm key from the Emberhold side (+z... board has Emberhold at -x here), cold rim
scene.add(new HemisphereLight(0x8899cc, 0x2a221a, 1.1));
scene.add(new AmbientLight(0x404858, 0.8));
const key = new DirectionalLight(0xffb070, 4.5); key.position.set(-4, 6, 3); key.castShadow = true; key.shadow.mapSize.set(1024, 1024);
Object.assign(key.shadow.camera, { left: -6, right: 6, top: 6, bottom: -6 });
scene.add(key);
const rim = new DirectionalLight(0x7fb8ff, 3.2); rim.position.set(5, 3, -4); scene.add(rim);

// board
const cv = document.createElement('canvas'); cv.width = cv.height = 512;
const cx = cv.getContext('2d')!;
for (let r = 0; r < 8; r++) for (let c = 0; c < 8; c++) { cx.fillStyle = (r + c) % 2 ? '#1a1d22' : '#2b2a29'; cx.fillRect(c * 64, r * 64, 64, 64); }
const tex = new CanvasTexture(cv); tex.colorSpace = SRGBColorSpace;
const board = new Mesh(new PlaneGeometry(8, 8).rotateX(-Math.PI / 2), new MeshStandardMaterial({ map: tex, roughness: 0.55, metalness: 0.2 }));
board.receiveShadow = true; scene.add(board);

const loader = new GLTFLoader();
loader.setMeshoptDecoder(MeshoptDecoder);
const cache = new Map<string, Promise<Object3D>>();
const load = (name: string) => {
  if (!cache.has(name)) cache.set(name, loader.loadAsync(`/models/${name}.glb`).then((g) => g.scene));
  return cache.get(name)!;
};

function makeActor(faction: Faction, role: Role, model: Object3D, x: number): PieceActor {
  const root = new Group(); root.position.set(x, 0, 0);
  root.rotation.y = faction === 'emberhold' ? Math.PI : 0;
  const m = skClone(model); root.add(m);
  const meshes: Mesh[] = [];
  m.traverse((c) => { const me = c as Mesh; if (me.isMesh) { meshes.push(me); me.castShadow = true; me.material = (me.material as any).clone(); } });
  const impact = new Object3D(); impact.position.set(0, 0.7, 0); root.add(impact);
  scene.add(root);
  return { id: `${faction}_${role}`, faction, role, side: faction === 'emberhold' ? 'w' : 'b', root, model: m, meshes,
    sockets: { socket_impact: impact }, square: 'e4' } as unknown as PieceActor;
}

const fx = createFx();
let post = createPost(renderer, scene, camera, 'high');
let actors: Record<string, PieceActor> = {};

async function spawn() {
  for (const a of Object.values(actors)) { scene.remove(a.root); }
  const [pawn, queen] = await Promise.all([load('emberhold_pawn'), load('rime_queen')]);
  actors = { pawn: makeActor('emberhold', 'pawn', pawn, -1.6), queen: makeActor('rime', 'queen', queen, 1.6) };
}

async function shatter(which: 'pawn' | 'queen', cut = false) {
  const a = actors[which];
  const fr = skClone(await load(`${a.id}_fragments`));
  fr.position.copy(a.root.position); fr.quaternion.copy(a.root.quaternion);
  scene.add(fr);
  fr.traverse((c: any) => { if (c.isMesh) c.castShadow = true; });
  const dir = new Vector3(which === 'pawn' ? 1 : -1, 0.15, 0.3).normalize();
  await fx.shatter({ actor: a, fragments: fr, impulseDir: dir, magnitude: which === 'queen' ? 1.4 : 0.8,
    cutNormal: cut ? new Vector3(0.3, 0.8, 0.5).normalize() : undefined, onDone: () => scene.remove(fr) });
}

const P = (x: number, y = 0, z = 0) => new Vector3(x, y, z);
const effects: Record<string, () => unknown> = {
  'embers': () => fx.emit('embers', P(-1.6, 0.4), { count: 40 }),
  'sparks': () => fx.emit('sparks', P(-1.6, 0.8), { count: 50 }),
  'smoke': () => fx.emit('smoke', P(-1.6, 0.4), { count: 16 }),
  'frostMist': () => fx.emit('frostMist', P(1.6, 0.4), { count: 24 }),
  'iceGlitter': () => fx.emit('iceGlitter', P(1.6, 0.8), { count: 60 }),
  'summonSpiral E': () => emitFaction(fx, 'summonSpiral', P(-1.6, 0.05), 'emberhold'),
  'summonSpiral R': () => emitFaction(fx, 'summonSpiral', P(1.6, 0.05), 'rime'),
  'dustPuff': () => fx.emit('dustPuff', P(0, 0.05)),
  'fireWave': () => fx.emit('fireWave', P(-3, 0.05), { direction: P(1), duration: 0.9, scale: 1.2 }),
  'frostBeam': () => fx.emit('frostBeam', P(3, 0.9), { direction: P(-1), duration: 0.7, scale: 1.3 }),
  'shockwave E': () => fx.shockwave(P(-1.6), 'emberhold', 2.6),
  'shockwave R': () => fx.shockwave(P(1.6), 'rime', 2.6),
  'iceSpikes': () => fx.iceSpikes(P(1.6), 8),
  'trail E': () => { const o = new Object3D(); scene.add(o); const t = fx.trail(o, 'emberhold'); const s = { a: 0 };
    gsap.to(s, { a: 1, duration: 0.8, ease: 'power2.inOut', onUpdate: () => o.position.set(-2.5 + s.a * 2.5, 0.9 + Math.sin(s.a * 3.14) * 0.6, 0.5 - s.a), onComplete: () => { t.stop(); scene.remove(o); } }); },
  'trail R': () => { const o = new Object3D(); scene.add(o); const t = fx.trail(o, 'rime'); const s = { a: 0 };
    gsap.to(s, { a: 1, duration: 0.8, ease: 'power2.inOut', onUpdate: () => o.position.set(2.5 - s.a * 2.5, 0.9 + Math.sin(s.a * 3.14) * 0.6, 0.5 - s.a), onComplete: () => { t.stop(); scene.remove(o); } }); },
  'decal crack': () => fx.decal(P(-0.6, 0, 1.2), 'crack'),
  'decal scorch': () => fx.decal(P(0.6, 0, 1.2), 'scorch'),
  'decal frost': () => fx.decal(P(1.8, 0, 1.2), 'frost'),
  'column E': () => fx.column(P(-1.6), 'emberhold', 2.0),
  'column R': () => fx.column(P(1.6), 'rime', 2.0),
  'aura E': () => fx.aura(P(-1.6), 'emberhold'),
  'aura R': () => fx.aura(P(1.6), 'rime'),
  'flash pawn': () => fx.flash(actors.pawn),
  'flash queen': () => fx.flash(actors.queen),
  'mist': () => fx.mist(),
  'sweep ember (pawn)': () => fx.sweep(actors.pawn, 'ember', 1.0),
  'sweep frost (queen)': () => fx.sweep(actors.queen, 'frost', 0.8),
  'dissolve pawn': () => fx.dissolve(actors.pawn.root, 'emberhold', 1.0),
  'dissolve queen': () => fx.dissolve(actors.queen.root, 'rime', 1.0),
  'shatter pawn': () => shatter('pawn'),
  'shatter queen (cut)': () => shatter('queen', true),
  'respawn': () => spawn(),
};

const ui = document.getElementById('ui')!;
const sel = document.createElement('select');
for (const t of ['high', 'medium', 'low']) sel.add(new Option('tier: ' + t, t));
sel.onchange = () => setTier(sel.value as QualityTier);
ui.append(sel);
const slow = document.createElement('button'); slow.textContent = 'slow-mo 0.3';
slow.onclick = () => { const g = gsap.globalTimeline; g.timeScale(g.timeScale() === 1 ? 0.3 : 1); };
ui.append(slow);


let gfx: GraphicsSettings = { ...GRAPHICS_PRESETS.high };
function applyGfx() { fx.setGraphics(gfx); post.setGraphics(gfx); }
function setTier(t: QualityTier) { gfx = { ...GRAPHICS_PRESETS[t] }; fx.setQuality(t); post.setQuality(t); applyGfx(); sel.value = t; syncUi(); }
function setGfx(p: Partial<GraphicsSettings>) { gfx = { ...gfx, ...p, preset: 'custom' }; applyGfx(); }

// graphics toggles
const gui: Record<string, HTMLSelectElement> = {};
function addSel(label: string, key: keyof GraphicsSettings, opts: (string | number | boolean)[]) {
  const s = document.createElement('select'); s.title = label;
  for (const o of opts) s.add(new Option(`${label}: ${o}`, String(o)));
  s.onchange = () => { const raw = s.value; const v = raw === 'true' ? true : raw === 'false' ? false : isNaN(Number(raw)) ? raw : Number(raw); setGfx({ [key]: v } as any); };
  ui.append(s); gui[key] = s;
}
function syncUi() { for (const [k, s] of Object.entries(gui)) s.value = String((gfx as any)[k]); }
addSel('particles', 'particles', ['low', 'medium', 'high']);
addSel('physics', 'physics', ['simple', 'full']);
addSel('bloom', 'bloom', [true, false]);
addSel('smaa', 'antialias', [true, false]);
addSel('ambient', 'ambient', [false, true]);
addSel('res', 'resolutionScale', [1, 0.75, 0.5]);

// crowded board + physics stress test
let crowd: PieceActor[] = [];
async function makeCrowd() {
  for (const a of crowd) scene.remove(a.root);
  const pawn = await load('emberhold_pawn'), rpawn = await load('rime_pawn');
  crowd = [];
  const spots: [number, number][] = [[-0.6, 1.2], [0.2, 1.4], [1.0, -1.2], [-1.2, -1.0], [0, -1.6], [2.6, 1.0], [-2.6, 1.2], [0.4, 0.5]];
  spots.forEach(([x, z], i) => { const f: Faction = i % 2 ? 'rime' : 'emberhold'; const a = makeActor(f, 'pawn', i % 2 ? rpawn : pawn, x); a.root.position.z = z; crowd.push(a); });
  fx.setStaticActors([...Object.values(actors), ...crowd]);
}
async function stress() {
  await makeCrowd();
  const q = await load('rime_queen'), frag = await load('rime_queen_fragments');
  const spots: [number, number][] = [[-1.2, 0.0], [0.8, 0.6], [1.8, -0.6]];
  await Promise.all(spots.map(async ([x, z]) => {
    const a = makeActor('rime', 'queen', q, x); a.root.position.z = z;
    const fr = skClone(frag); fr.position.copy(a.root.position); fr.quaternion.copy(a.root.quaternion); scene.add(fr);
    await fx.shatter({ actor: a, fragments: fr, impulseDir: new Vector3(0.6, 0.15, 0.4).normalize(), magnitude: 1.4, onDone: () => { scene.remove(fr); scene.remove(a.root); } });
  }));
}
effects['crowd'] = () => makeCrowd();
effects['stress x3 queens'] = () => stress();


for (const [name, fn] of Object.entries(effects)) {
  const b = document.createElement('button'); b.textContent = name; b.dataset.fx = name;
  b.onclick = () => { void fn(); };
  ui.append(b);
}
function resize() {
  const w = window.innerWidth, h = window.innerHeight;
  camera.aspect = w / h; camera.updateProjectionMatrix();
  post.setSize(w, h);
}
window.addEventListener('resize', resize);

let last = performance.now(), frames = 0, acc = 0;
const fpsEl = document.getElementById('fps')!;
const stats = { frames: 0, time: 0 };
let paused = false;
function loop(now: number) {
  const dt = Math.min(0.1, (now - last) / 1000); last = now;
  if (!paused) fx.update(dt * gsap.globalTimeline.timeScale());
  post.render(dt);
  frames++; acc += dt; stats.frames++; stats.time += dt;
  if (acc >= 0.5) { fpsEl.textContent = `${Math.round(frames / acc)} fps`; frames = 0; acc = 0; }
  requestAnimationFrame(loop);
}

(async () => {
  await fx.init(scene, renderer, camera);
  fx.setQuality('high');
  await spawn();
  resize();
  requestAnimationFrame(loop);
  (window as any).__fx = {
    names: Object.keys(effects), camera, scene, setGfx, probe: () => {
      // render one frame and read back a pixel grid: returns mean luminance (0 = black frame) and GL error
      post.render(0);
      const gl = renderer.getContext() as WebGL2RenderingContext;
      const w = gl.drawingBufferWidth, h = gl.drawingBufferHeight, px = new Uint8Array(4);
      let sum = 0, n = 0, lit = 0;
      for (let i = 1; i < 8; i++) for (let j = 1; j < 8; j++) { gl.readPixels((w * i) / 8 | 0, (h * j) / 8 | 0, 1, 1, gl.RGBA, gl.UNSIGNED_BYTE, px); const l = px[0] + px[1] + px[2]; sum += l; n++; if (j <= 3 && l > 12) lit++; }
      // lit: lower-half grid cells (the board) that are not black; expect most of the 21
      return { lum: sum / n / 3, lit, err: gl.getError(), w, h, pr: renderer.getPixelRatio() };
    }, slow: (k: number) => gsap.globalTimeline.timeScale(k),
    // Deterministic stepping for screenshots: pause real time, then advance sim by t seconds in 1/60 steps.
    pause: (on: boolean) => { paused = on; if (on) gsap.globalTimeline.pause(); else gsap.globalTimeline.resume(); },
    advance: (t: number) => { const g = gsap.globalTimeline; for (let i = 0; i < Math.round(t * 60); i++) { g.time(g.time() + 1 / 60, false); fx.update(1 / 60); } }, run: (n: string) => effects[n](), setTier, stats, actors: () => actors,
    reset: () => { stats.frames = 0; stats.time = 0; }, ready: true,
  };
})().catch((e) => { console.error('sandbox init failed', e); });

void (null as unknown as ParticlePreset);
