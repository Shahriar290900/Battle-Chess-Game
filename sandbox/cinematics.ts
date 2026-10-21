// Cinematics sandbox: real three.js scene + placeholder GLBs + the real cinematics module driven through
// minimal sandbox implementations of BoardApi / CameraRig / PieceActor / FxApi.
import { gsap } from 'gsap';
import { ACESFilmicToneMapping, Clock, Color, DirectionalLight, HemisphereLight, PCFSoftShadowMap, WebGLRenderer } from 'three';
import type { CaptureMode, Faction, MoveResult, Role, SequenceContext, Settings, Side } from '../src/contracts';
import { DEFAULT_SETTINGS, EventBus, ROLE_SYMBOL } from '../src/contracts';
import { createSequencePlayer } from '../src/cinematics';
import { SandboxRegistry } from './cinematics/actor';
import { SandboxBoard } from './cinematics/board';
import { SandboxCamera } from './cinematics/camera';
import { SandboxFx } from './cinematics/fx';

const ROLES: Role[] = ['pawn', 'rook', 'knight', 'bishop', 'queen', 'king'];
const SQUARES: Record<Role, Record<Side, [string, string]>> = {
  pawn: { w: ['e4', 'd5'], b: ['d5', 'e4'] }, rook: { w: ['a1', 'a5'], b: ['h8', 'h4'] },
  knight: { w: ['e4', 'f6'], b: ['e5', 'd3'] }, bishop: { w: ['c1', 'g5'], b: ['f8', 'b4'] },
  queen: { w: ['d1', 'h5'], b: ['d8', 'h4'] }, king: { w: ['e1', 'e2'], b: ['e8', 'e7'] },
};

const canvas = document.getElementById('c') as HTMLCanvasElement;
const status = document.getElementById('status')!;
const renderer = new WebGLRenderer({ canvas, antialias: true });
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
renderer.shadowMap.enabled = true; renderer.shadowMap.type = PCFSoftShadowMap;
renderer.toneMapping = ACESFilmicToneMapping;

const registry = new SandboxRegistry();
const board = new SandboxBoard(registry);
const camera = new SandboxCamera();
const fx = new SandboxFx();
const bus = new EventBus();
const player = createSequencePlayer();
const settings: Settings = { ...DEFAULT_SETTINGS };
const errors: string[] = [];
const eventLog: Array<{ name: string; t: number }> = [];
let frozen = false;
const freezers: Array<{ event: string; afterMs: number; fired: boolean; resolve: () => void }> = [];

for (const n of ['capture:begin', 'capture:impact', 'capture:shatter', 'capture:end', 'attack:whoosh', 'summon', 'spell', 'move:step'] as const) {
  bus.on(n, () => {
    eventLog.push({ name: n, t: performance.now() });
    for (const f of freezers) if (!f.fired && f.event === n) {
      f.fired = true;
      setTimeout(() => { gsap.globalTimeline.pause(); frozen = true; f.resolve(); }, f.afterMs);
    }
  });
}
window.addEventListener('error', (e) => errors.push(String(e.message)));
window.addEventListener('unhandledrejection', (e) => errors.push('unhandled: ' + String(e.reason)));

function lights() {
  const s = board.scene;
  s.background = new Color(0x15110f);
  s.add(new HemisphereLight(0xcfd8ff, 0x3a2a20, 1.2));
  const key = new DirectionalLight(0xffe2b8, 2.6);
  key.position.set(5, 10, 6); key.castShadow = true; key.shadow.mapSize.set(2048, 2048);
  Object.assign(key.shadow.camera, { left: -6, right: 6, top: 6, bottom: -6, near: 1, far: 30 });
  s.add(key);
  const rim = new DirectionalLight(0x8fd8ff, 1.4); rim.position.set(-6, 5, -7); s.add(rim);
}

function setupScene(role: Role, faction: Faction) {
  board.clear();
  const side: Side = faction === 'emberhold' ? 'w' : 'b';
  const [from, to] = SQUARES[role][side];
  const other: Faction = faction === 'emberhold' ? 'rime' : 'emberhold';
  board.add(faction, role, from);
  board.add(other, 'knight', to);
  for (const f of 'abcdefgh') for (const [r, fac] of [['2', 'emberhold'], ['7', 'rime']] as const) {
    const sq = f + r;
    if (sq !== from && sq !== to) board.add(fac, 'pawn', sq);
  }
  if (!board.actorAt('e1')) board.add('emberhold', 'king', 'e1');
  if (!board.actorAt('e8')) board.add('rime', 'king', 'e8');
  camera.toSeat(side, { instant: true });
  return { from, to, side };
}

function ctxFor(move: MoveResult): SequenceContext {
  return { move, board, camera, fx, registry, bus, settings };
}

async function playCapture(role: Role, faction: Faction, mode: CaptureMode = 'full') {
  const { from, to, side } = setupScene(role, faction);
  settings.captureMode = mode;
  gsap.globalTimeline.resume(); frozen = false;
  const move: MoveResult = {
    from, to, san: 'x', side, role, captured: 'knight', capturedSquare: to, flags: 'c', isCastle: false, isEnPassant: false,
    check: false, mate: false, stalemate: false, draw: false, fenAfter: '', 
  };
  await player.capture(ctxFor(move));
}

function resize() {
  const w = innerWidth, h = innerHeight;
  renderer.setSize(w, h, false); camera.resize(w, h);
}
addEventListener('resize', resize);

const sandbox = {
  ready: false,
  errors,
  eventLog,
  get frozen() { return frozen; },
  playCapture,
  skip: () => player.skip(),
  settings,
  camera,
  fx,
  board,
  /** Pause the whole GSAP world `afterMs` real ms after the next `event`; resolves when paused. */
  armFreeze(event: string, afterMs = 0) { return new Promise<void>((resolve) => { freezers.push({ event, afterMs, fired: false, resolve }); }); },
  clearFreezers() { freezers.length = 0; },
  resume() { frozen = false; gsap.globalTimeline.resume(); },
  hideUi(v = true) { document.getElementById('ui')!.classList.toggle('hidden', v); },
};
(window as unknown as { __sandbox: typeof sandbox }).__sandbox = sandbox;

async function main() {
  lights();
  await registry.preload((l, t) => { status.textContent = `loading ${l}/${t}`; });
  await fx.init(board.scene, renderer, camera.camera);
  setupScene('pawn', 'emberhold');
  resize();
  const ui = document.getElementById('ui')!;
  const modeSel = document.createElement('select');
  for (const m of ['full', 'quick', 'off']) modeSel.add(new Option(`mode: ${m}`, m));
  ui.append(modeSel);
  const speed = document.createElement('select');
  for (const s of [0.5, 1, 2]) speed.add(new Option(`speed ${s}x`, String(s), false, s === 1));
  speed.onchange = () => { settings.animSpeed = Number(speed.value); };
  ui.append(speed);
  const skip = document.createElement('button'); skip.textContent = 'skip'; skip.onclick = () => player.skip(); ui.append(skip);
  for (const faction of ['emberhold', 'rime'] as Faction[]) for (const role of ROLES) {
    const b = document.createElement('button');
    b.textContent = `${faction === 'emberhold' ? 'Ember' : 'Rime'} ${role} (${ROLE_SYMBOL[role]})`;
    if (faction === 'rime') b.className = 'rime';
    b.onclick = () => { void playCapture(role, faction, modeSel.value as CaptureMode); };
    ui.append(b);
  }
  const clock = new Clock();
  renderer.setAnimationLoop(() => {
    const dt = Math.min(0.1, clock.getDelta());
    const scaled = dt * gsap.globalTimeline.timeScale() * (frozen ? 0 : 1);
    board.update(scaled);
    fx.update(scaled);
    camera.update(dt);
    renderer.render(board.scene, camera.camera);
  });
  sandbox.ready = true;
  status.textContent = 'ready';
}
main().catch((e) => { errors.push(String(e)); status.textContent = 'error: ' + e; });
