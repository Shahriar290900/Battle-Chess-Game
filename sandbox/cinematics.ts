// Cinematics sandbox: real three.js scene + placeholder GLBs + the real cinematics module driven through
// minimal sandbox implementations of BoardApi / CameraRig / PieceActor / FxApi.
import { gsap } from 'gsap';
import { ACESFilmicToneMapping, Clock, Color, DirectionalLight, HemisphereLight, PCFSoftShadowMap, WebGLRenderer } from 'three';
import type { CaptureMode, Faction, MoveResult, Role, SequenceContext, Settings, Side } from '../src/contracts';
import { DEFAULT_SETTINGS, EventBus, ROLE_SYMBOL } from '../src/contracts';
import { createAttract, createSequencePlayer } from '../src/cinematics';
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
const attract = createAttract({ board, camera, fx, registry, bus, settings, sequences: player });
const errors: string[] = [];
const eventLog: Array<{ name: string; t: number }> = [];
let frozen = false;
const freezers: Array<{ event: string; afterMs: number; fired: boolean; resolve: () => void }> = [];

for (const n of ['capture:begin', 'capture:impact', 'capture:shatter', 'capture:end', 'attack:whoosh', 'summon', 'spell', 'move:step', 'taunt', 'clash', 'weapon:drop', 'surrender', 'game:start', 'turn:start', 'game:over'] as const) {
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

async function runCapture(from: string, to: string, role: Role, side: Side, mode: CaptureMode) {
  settings.captureMode = mode;
  gsap.globalTimeline.resume(); frozen = false;
  const captured = board.actorAt(to)?.role ?? 'knight';
  const move: MoveResult = {
    from, to, san: 'x', side, role, captured, capturedSquare: to, flags: 'c', isCastle: false, isEnPassant: false,
    check: false, mate: false, stalemate: false, draw: false, fenAfter: '',
  };
  await player.capture(ctxFor(move));
}

async function playCapture(role: Role, faction: Faction, mode: CaptureMode = 'full') {
  const { from, to, side } = setupScene(role, faction);
  await runCapture(from, to, role, side, mode);
}

/** Full 32-piece board, then a capture in the middle of the crowd / on the back rank. */
const BACK: Role[] = ['rook', 'knight', 'bishop', 'queen', 'king', 'bishop', 'knight', 'rook'];
type Scenario = 'opening-w' | 'opening-b' | 'backrank-w' | 'backrank-b';
async function playScenario(name: Scenario, mode: CaptureMode = 'full') {
  board.clear();
  const rm = new Set<string>();
  const extra: Array<[Faction, Role, string]> = [];
  let from = ''; let to = ''; let role: Role = 'pawn'; let side: Side = 'w';
  if (name === 'opening-w') { rm.add('e2'); rm.add('d7'); extra.push(['emberhold', 'pawn', 'e4'], ['rime', 'pawn', 'd5']); from = 'e4'; to = 'd5'; }
  if (name === 'opening-b') { rm.add('e2'); rm.add('d7'); rm.add('g1'); extra.push(['emberhold', 'pawn', 'e4'], ['emberhold', 'knight', 'f3'], ['rime', 'pawn', 'd5']); from = 'd5'; to = 'e4'; side = 'b'; }
  if (name === 'backrank-w') { rm.add('d2'); rm.add('d7'); from = 'd1'; to = 'd8'; role = 'queen'; }
  if (name === 'backrank-b') { rm.add('d2'); rm.add('d7'); from = 'd8'; to = 'd1'; role = 'queen'; side = 'b'; }
  for (let f = 0; f < 8; f++) {
    for (const [rank, fac, r] of [['1', 'emberhold', BACK[f]], ['2', 'emberhold', 'pawn'], ['7', 'rime', 'pawn'], ['8', 'rime', BACK[f]]] as Array<[string, Faction, Role]>) {
      const sq = 'abcdefgh'[f] + rank;
      if (!rm.has(sq)) board.add(fac, r, sq);
    }
  }
  for (const [fac, r, sq] of extra) board.add(fac, r, sq);
  camera.toSeat(side, { instant: true });
  const attacker = board.actorAt(from)!;
  role = attacker.role;
  await runCapture(from, to, role, side, mode);
}

/** Check provoke: a checker of `role` threatens the enemy king. */
const CHECK_SQ: Record<Role, [string, string]> = {
  pawn: ['d7', 'e8'], rook: ['e4', 'e8'], knight: ['d6', 'e8'], bishop: ['h5', 'e8'], queen: ['e5', 'e8'], king: ['e7', 'e8'],
};
async function playCheck(role: Role, faction: Faction, mode: CaptureMode = 'full') {
  board.clear();
  const side: Side = faction === 'emberhold' ? 'w' : 'b';
  const mirror = (sq: string) => (side === 'w' ? sq : sq[0] + String(9 - Number(sq[1])));
  const [c, k] = CHECK_SQ[role].map(mirror);
  const other: Faction = faction === 'emberhold' ? 'rime' : 'emberhold';
  board.add(faction, role, c); board.add(other, 'king', k);
  for (const f of 'abcdefgh') for (const [r, fac] of [['2', 'emberhold'], ['7', 'rime']] as const) {
    const sq = f + r; if (sq !== c && sq !== k && !board.actorAt(sq)) board.add(fac, 'pawn', sq);
  }
  camera.toSeat(side, { instant: true });
  settings.captureMode = mode;
  gsap.globalTimeline.resume(); frozen = false;
  const move: MoveResult = { from: c, to: c, san: '+', side, role, flags: '', isCastle: false, isEnPassant: false, check: true, mate: false, stalemate: false, draw: false, fenAfter: '' };
  await player.check(ctxFor(move), k);
}

/** Checkmate of the Rime king on a full board. */
async function playMate() {
  board.clear();
  for (let f = 0; f < 8; f++) {
    for (const [rank, fac, r] of [['1', 'emberhold', BACK[f]], ['2', 'emberhold', 'pawn'], ['7', 'rime', 'pawn'], ['8', 'rime', BACK[f]]] as Array<[string, Faction, Role]>) board.add(fac, r, 'abcdefgh'[f] + rank);
  }
  camera.toSeat('w', { instant: true });
  settings.captureMode = 'full';
  gsap.globalTimeline.resume(); frozen = false;
  const move: MoveResult = { from: 'd1', to: 'd8', san: '#', side: 'w', role: 'queen', flags: '', isCastle: false, isEnPassant: false, check: true, mate: true, stalemate: false, draw: false, fenAfter: '' };
  await player.checkmate(ctxFor(move), 'e8');
}

function startAttract() { board.clear(); resetStart(); camera.toSeat('w', { instant: true }); gsap.globalTimeline.resume(); frozen = false; attract.start(); }
function resetStart() {
  for (let f = 0; f < 8; f++) {
    for (const [rank, fac, r] of [['1', 'emberhold', BACK[f]], ['2', 'emberhold', 'pawn'], ['7', 'rime', 'pawn'], ['8', 'rime', BACK[f]]] as Array<[string, Faction, Role]>) board.add(fac, r, 'abcdefgh'[f] + rank);
  }
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
  playScenario,
  playCheck,
  playMate,
  startAttract,
  stopAttract: () => attract.stop(),
  attract,
  /** Pause the GSAP world `ms` real ms from now; resolves when paused. */
  freezeAfter(ms: number) { return new Promise<void>((resolve) => setTimeout(() => { gsap.globalTimeline.pause(); frozen = true; resolve(); }, ms)); },
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
  const mk = (label: string, fn: () => void) => { const b = document.createElement('button'); b.textContent = label; b.onclick = fn; ui.append(b); };
  const checkRole = document.createElement('select');
  for (const r of ROLES) checkRole.add(new Option(`check by ${r}`, r));
  ui.append(checkRole);
  mk('Check provoke (Ember)', () => { void playCheck(checkRole.value as Role, 'emberhold', modeSel.value as CaptureMode); });
  mk('Check provoke (Rime)', () => { void playCheck(checkRole.value as Role, 'rime', modeSel.value as CaptureMode); });
  mk('Checkmate', () => { void playMate(); });
  mk('Attract start', () => { startAttract(); });
  mk('Attract stop', () => { void attract.stop(); });
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
