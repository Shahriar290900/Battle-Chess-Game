// Kinematics sandbox: real GLB actors (registry + mixer), walk/stop/hop/impulse/look-at buttons and a frame-time readout.
// Served by `npx vite` at /sandbox/kinematics.html. Automation hook: window.__sandbox.
import { gsap } from 'gsap';
import {
  ACESFilmicToneMapping, AmbientLight, Color, DirectionalLight, HemisphereLight, Mesh, MeshStandardMaterial,
  PerspectiveCamera, PlaneGeometry, Scene, Vector3, WebGLRenderer,
} from 'three';
import { createAssetRegistry } from '../src/assets/registry';
import type { PieceActor, Role } from '../src/contracts';
import { squareToWorld } from '../src/contracts';
import { createKinematics } from '../src/kinematics';

const renderer = new WebGLRenderer({ antialias: false, powerPreference: 'high-performance' });
renderer.setPixelRatio(1);
renderer.toneMapping = ACESFilmicToneMapping;
renderer.shadowMap.enabled = true;
document.body.prepend(renderer.domElement);
const scene = new Scene();
scene.background = new Color(0x07090c);
const camera = new PerspectiveCamera(40, 1, 0.1, 100);
camera.position.set(0, 2.6, 7.6);
camera.lookAt(0, 0.7, 0);
scene.add(new HemisphereLight(0x8899cc, 0x2a221a, 1.1), new AmbientLight(0x404858, 0.8));
const key = new DirectionalLight(0xffb070, 4.5); key.position.set(-4, 6, 4); key.castShadow = true; key.shadow.mapSize.set(1024, 1024);
Object.assign(key.shadow.camera, { left: -6, right: 6, top: 6, bottom: -6 });
scene.add(key);
const rim = new DirectionalLight(0x7fb8ff, 3); rim.position.set(5, 3, -4); scene.add(rim);
const floor = new Mesh(new PlaneGeometry(14, 6).rotateX(-Math.PI / 2), new MeshStandardMaterial({ color: 0x23262b, roughness: 0.6 }));
floor.receiveShadow = true; scene.add(floor);

const kin = createKinematics();
kin.setCamera(camera);
const registry = createAssetRegistry();
const actors: PieceActor[] = [];
const ROLES: Role[] = ['pawn', 'rook', 'knight', 'bishop', 'queen', 'king'];
const home = new Map<PieceActor, Vector3>();
const target = new Vector3(0, 1.1, 3);
const hud = document.getElementById('hud')!;
let enabled = true;
let msAvg = 0, msMax = 0;
const cutoff: number[] = [];

function layout(i: number): Vector3 { return new Vector3(-3.1 + i * 1.24, 0, -0.6); }

async function init() {
  await registry.preload();
  ROLES.forEach((role, i) => {
    const a = registry.createActor(i % 2 ? 'rime' : 'emberhold', role, 'e4');
    a.root.position.copy(layout(i));
    a.root.rotation.y = 0.0; // all face +Z (towards camera)
    scene.add(a.root);
    kin.attach(a);
    actors.push(a);
    home.set(a, a.root.position.clone());
  });
  // a crowd for the perf readout: 26 extra attached actors (shared templates), parked far back
  for (let i = 0; i < 26; i++) {
    const a = registry.createActor(i % 2 ? 'rime' : 'emberhold', ROLES[i % 6], 'a1');
    a.root.position.set(-6.2 + (i % 13) * 1.0, 0, -2.2 - Math.floor(i / 13) * 1.1);
    scene.add(a.root); kin.attach(a); crowd.push(a);
  }
}
const crowd: PieceActor[] = [];
void squareToWorld;

// ---- scripted motions (root is tweened by gsap exactly like the cinematics do)
const walk = (a: PieceActor, dz = 1.8, dur = 1.1) => {
  gsap.killTweensOf(a.root.position);
  a.play('Move', { fade: 0.15 });
  return gsap.to(a.root.position, { z: home.get(a)!.z + dz, duration: dur, ease: 'power2.inOut', onComplete: () => a.play('Idle', { fade: 0.2 }) });
};
const stopAbrupt = (a: PieceActor) => {
  gsap.killTweensOf(a.root.position);
  a.play('Move', { fade: 0.1 });
  const z0 = a.root.position.z;
  return gsap.to(a.root.position, { z: z0 + 1.2, duration: 0.4, ease: 'none', onComplete: () => a.play('Idle', { fade: 0.2 }) });
};
const hop = (a: PieceActor) => {
  gsap.killTweensOf(a.root.position);
  const p = a.root.position, z0 = p.z;
  const tl = gsap.timeline();
  tl.to(p, { y: 0.9, z: z0 + 0.8, duration: 0.28, ease: 'power2.out' }).to(p, { y: 0, z: z0 + 1.6, duration: 0.26, ease: 'power2.in' });
  return tl;
};
const reset = () => { for (const a of actors) { gsap.killTweensOf(a.root.position); a.root.position.copy(home.get(a)!); a.play('Idle', { fade: 0.1 }); kin.lookAt(a, null); } };
const impulse = (strength = 2.2) => kin.impulse(new Vector3(0, 0.2, -0.6), strength, 4);
const look = (on: boolean) => { for (const a of actors) kin.lookAt(a, on ? target : null, 1); };
const setEnabled = (on: boolean) => { enabled = on; kin.setEnabled(on); };
const attackScrub = (a: PieceActor) => { const tl = a.attackTimeline(); tl.eventCallback('onComplete', () => a.play('Idle', { fade: 0.2 })); return tl; };

/** Offline micro-benchmark of kin.update over the attached actors (no rendering in between), with the actors drifting. */
function bench(n = 600): number {
  const all = [...actors, ...crowd];
  const saved = all.map((a) => a.root.position.x);
  for (let i = 0; i < 120; i++) kin.update(1 / 60); // warm
  const t0 = performance.now();
  for (let i = 0; i < n; i++) { all[i % all.length].root.position.x += Math.sin(i * 0.1) * 0.02; kin.update(1 / 60); }
  const ms = (performance.now() - t0) / n;
  all.forEach((a, i) => { a.root.position.x = saved[i]; });
  return ms;
}

const sandbox = {
  bench,
  ready: false, actors, kin, walk, stopAbrupt, hop, reset, impulse, look, setEnabled, attackScrub, target,
  hideUi: (h: boolean) => { document.getElementById('ui')!.style.display = h ? 'none' : ''; },
  stats: () => ({ msAvg, msMax, ...kin.stats(), enabled }),
  errors: [] as string[],
};
(window as unknown as { __sandbox: typeof sandbox }).__sandbox = sandbox;

const ui = document.getElementById('ui')!;
const btn = (label: string, fn: () => void) => { const b = document.createElement('button'); b.textContent = label; b.onclick = fn; ui.appendChild(b); };
btn('Walk all', () => actors.forEach((a) => walk(a)));
btn('Stop abruptly', () => actors.forEach((a) => stopAbrupt(a)));
btn('Hop all', () => actors.forEach((a) => hop(a)));
btn('Impulse', () => impulse());
btn('Big impulse', () => impulse(4));
btn('Look at marker', () => look(true));
btn('Release look', () => look(false));
btn('Attack (scrub gate)', () => actors.forEach((a) => attackScrub(a)));
btn('Toggle kinematics', () => { setEnabled(!enabled); });
btn('Reset', reset);
document.addEventListener('pointermove', (e) => {
  target.set((e.clientX / innerWidth - 0.5) * 8, 0.6 + (1 - e.clientY / innerHeight) * 2.2, 3);
});

function resize() { renderer.setSize(innerWidth, innerHeight); camera.aspect = innerWidth / innerHeight; camera.updateProjectionMatrix(); }
addEventListener('resize', resize); resize();

let last = performance.now();
function frame(now: number) {
  const dt = Math.min((now - last) / 1000, 0.1); last = now;
  for (const a of actors) a.update(dt);
  for (const a of crowd) a.update(dt);
  const t0 = performance.now();
  kin.update(dt);
  const ms = performance.now() - t0;
  cutoff.push(ms); if (cutoff.length > 120) cutoff.shift();
  msAvg = cutoff.reduce((s, v) => s + v, 0) / cutoff.length; msMax = Math.max(...cutoff);
  hud.textContent = `kinematics ${enabled ? 'ON ' : 'OFF'}  ${msAvg.toFixed(3)} ms avg  ${msMax.toFixed(3)} max\n${actors.length + crowd.length} actors attached`;
  renderer.render(scene, camera);
  requestAnimationFrame(frame);
}
init().then(() => { sandbox.ready = true; requestAnimationFrame(frame); }, (e) => { sandbox.errors.push(String(e)); hud.textContent = 'init failed: ' + e; });
