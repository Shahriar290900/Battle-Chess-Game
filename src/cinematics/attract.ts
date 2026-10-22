// Attract mode / launch cinematic: a camera flyover of both armies (low dolly along the Emberhold line, crane over
// the board, low dolly along the Rime line, then a slow orbit) with staged background duels played through the
// real capture sequences on a private chess.js game. Emits only sequence events (capture:*, taunt, ...), never
// game:* / turn:*. stop() aborts at any point and leaves the board at the start position and the camera at the seat.
import { Chess } from 'chess.js';
import type { Move } from 'chess.js';
import { gsap } from 'gsap';
import { Vector3 } from 'three';
import type { PerspectiveCamera } from 'three';
import type {
  AttractContext, AttractMode, CameraMode, CameraRig, CinematicCameraHandle, MoveResult, SequenceContext, Settings, Side, Square,
} from '../contracts';
import { SYMBOL_ROLE } from '../contracts';
import { lerp, smoothstep, withTimeout } from './common';
import { newPose, type ShotPose } from './shots';

export const START_FEN = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1';
/** Short scripted opening (played with real move sequences during the flyover). */
export const ATTRACT_SCRIPT = ['e4', 'd5', 'Nf3', 'Bg4', 'Nc3', 'Nf6'] as const;
const RESET_EVERY = 3;

// flyover timing (seconds)
const T_EMBER = 5; const T_CRANE = 4.5; const T_RIME = 5; const T_SETTLE = 2.5;
export const FLY_SECONDS = T_EMBER + T_CRANE + T_RIME + T_SETTLE;

/** Camera rig seen by the sequences: shots are widened and fed into the attract camera; restore() returns to the orbit. */
class AttractCamera implements CameraRig {
  mode: CameraMode = 'follow';
  private handle: CinematicCameraHandle | null = null;
  private clock = 0;
  private phase: 'fly' | 'orbit' | 'duel' = 'fly';
  private duel = newPose(); private hasDuel = false;
  private from = newPose(); private bt = 1; private bd = 0.8;
  private out = newPose(); private base = newPose(); private tmpA = newPose(); private tmpB = newPose();
  private restoreTimer: ReturnType<typeof setTimeout> | null = null;
  private readonly tick = (_t: number, dtMs: number) => this.update(Math.min(0.1, dtMs / 1000));
  glint: ((t: number, look: Vector3) => void) | null = null;
  private lastGlint = 0;

  constructor(private readonly real: CameraRig, private readonly onTime: (t: number) => void) {}
  get camera(): PerspectiveCamera { return this.real.camera; }

  begin(): void {
    this.handle = this.real.borrow();
    this.clock = 0; this.phase = 'fly'; this.bt = 1;
    gsap.ticker.add(this.tick);
  }

  async end(): Promise<void> {
    gsap.ticker.remove(this.tick);
    if (this.restoreTimer) { clearTimeout(this.restoreTimer); this.restoreTimer = null; }
    if (this.handle) { this.handle = null; await withTimeout(this.real.restore(0.5), 1500); }
  }

  // ---- CameraRig for the sequences
  setMode(m: CameraMode): void { this.mode = m; }
  async toSeat(): Promise<void> {}
  borrow(): CinematicCameraHandle {
    this.switchTo('duel', 0.7); this.hasDuel = false;
    return {
      camera: this.real.camera,
      set: (p, l, fov) => {
        // "background" framing: pull back and up so the menu stays readable
        this.duel.lookAt.copy(l);
        this.duel.position.copy(l).addScaledVector(this.tmpA.position.copy(p).sub(l), 1.35);
        this.duel.position.y = Math.min(8, this.duel.position.y + 0.9);
        this.duel.fov = (fov ?? 40) + 3;
        this.hasDuel = true;
      },
    };
  }
  restore(duration = 1): Promise<void> {
    this.switchTo('orbit', Math.max(0.3, duration));
    return new Promise((r) => { this.restoreTimer = setTimeout(r, Math.max(0, duration) * 1000); });
  }
  shake(t: number): void { this.real.shake(t * 0.5); }
  resize(w: number, h: number): void { this.real.resize(w, h); }

  private switchTo(p: 'orbit' | 'duel', dur: number): void {
    if (this.phase === p) return;
    this.from.position.copy(this.out.position); this.from.lookAt.copy(this.out.lookAt); this.from.fov = this.out.fov;
    this.phase = p; this.bt = 0; this.bd = dur;
  }

  /** Advance the camera clock (real seconds) and push the pose. */
  update(dt: number): void {
    if (!this.handle) return;
    this.clock += dt; this.bt += dt;
    this.onTime(this.clock);
    const b = this.base;
    if (this.phase === 'duel' && this.hasDuel) { b.position.copy(this.duel.position); b.lookAt.copy(this.duel.lookAt); b.fov = this.duel.fov; }
    else if (this.phase === 'duel') { b.position.copy(this.out.position); b.lookAt.copy(this.out.lookAt); b.fov = this.out.fov; }
    else if (this.clock < FLY_SECONDS && this.phase === 'fly') this.flyPose(this.clock, b);
    else { this.phase = this.phase === 'fly' ? 'orbit' : this.phase; this.orbitPose(this.clock, b); }
    const u = smoothstep(this.bt / this.bd);
    const o = this.out;
    if (u < 1) { o.position.copy(this.from.position).lerp(b.position, u); o.lookAt.copy(this.from.lookAt).lerp(b.lookAt, u); o.fov = lerp(this.from.fov, b.fov, u); }
    else { o.position.copy(b.position); o.lookAt.copy(b.lookAt); o.fov = b.fov; }
    this.handle.set(o.position, o.lookAt, o.fov);
    if (this.glint && this.phase === 'fly' && this.clock - this.lastGlint > 0.4) { this.lastGlint = this.clock; this.glint(this.clock, o.lookAt); }
  }

  private orbitPose(t: number, out: ShotPose): void {
    const a = 0.3 + (t - FLY_SECONDS + T_SETTLE) * 0.05;
    out.position.set(Math.sin(a) * 11.5, 8.2, Math.cos(a) * 11.5);
    out.lookAt.set(0, 0.2, 0); out.fov = 38;
  }

  /** Low dolly along the Emberhold line, crane over the board, low dolly along the Rime line, settle into the orbit. */
  private flyPose(t: number, out: ShotPose): void {
    const t1 = T_EMBER; const t2 = t1 + T_CRANE; const t3 = t2 + T_RIME;
    const dollyA = (p: number, o: ShotPose) => { // Emberhold line: camera between the armies facing the +z ranks
      const x = lerp(-5.8, 5.8, smoothstep(p));
      o.position.set(x, 0.95, 0.9); o.lookAt.set(x + 1.2, 0.8, 3.0); o.fov = 52;
    };
    const dollyB = (p: number, o: ShotPose) => { // Rime line, travelling the other way
      const x = lerp(5.8, -5.8, smoothstep(p));
      o.position.set(x, 0.95, -0.9); o.lookAt.set(x - 1.2, 0.8, -3.0); o.fov = 52;
    };
    const high = this.tmpB; high.position.set(0, 10.5, 9.5); high.lookAt.set(0, 0, 0); high.fov = 42;
    if (t < t1) { dollyA(t / t1, out); return; }
    if (t < t2) { // crane up
      const e = smoothstep((t - t1) / T_CRANE);
      dollyA(1, this.tmpA);
      out.position.copy(this.tmpA.position).lerp(high.position, e); out.position.y += Math.sin(e * Math.PI) * 1.5;
      out.lookAt.copy(this.tmpA.lookAt).lerp(high.lookAt, e); out.fov = lerp(this.tmpA.fov, high.fov, e);
      return;
    }
    if (t < t3) { // descend onto the Rime line, then dolly
      const p = (t - t2) / T_RIME; const e = smoothstep(Math.min(1, p / 0.3));
      dollyB(p, this.tmpA);
      out.position.copy(high.position).lerp(this.tmpA.position, e); out.lookAt.copy(high.lookAt).lerp(this.tmpA.lookAt, e); out.fov = lerp(high.fov, this.tmpA.fov, e);
      return;
    }
    // settle into the orbit
    const e = smoothstep((t - t3) / T_SETTLE);
    dollyB(1, this.tmpA); this.orbitPose(FLY_SECONDS, high);
    out.position.copy(this.tmpA.position).lerp(high.position, e); out.lookAt.copy(this.tmpA.lookAt).lerp(high.lookAt, e); out.fov = lerp(this.tmpA.fov, high.fov, e);
  }
}

function moveResult(m: Move, game: Chess): MoveResult {
  const role = SYMBOL_ROLE[m.piece];
  const castle = m.flags.includes('k') || m.flags.includes('q');
  const rank = m.from[1];
  return {
    from: m.from, to: m.to, san: m.san, side: m.color as Side, role,
    captured: m.captured ? SYMBOL_ROLE[m.captured] : undefined,
    capturedSquare: m.captured ? (m.flags.includes('e') ? m.to[0] + m.from[1] : m.to) : undefined,
    flags: m.flags, isCastle: castle,
    rookFrom: castle ? (m.flags.includes('k') ? 'h' + rank : 'a' + rank) : undefined,
    rookTo: castle ? (m.flags.includes('k') ? 'f' + rank : 'd' + rank) : undefined,
    isEnPassant: m.flags.includes('e'), promotion: undefined,
    check: m.san.endsWith('+'), mate: m.san.endsWith('#'), stalemate: false, draw: false,
    fenAfter: game.fen(),
  };
}

function kingSquare(game: Chess, side: Side): Square {
  for (const row of game.board()) for (const p of row) if (p && p.type === 'k' && p.color === side) return p.square;
  return 'e1';
}

export function createAttract(base: AttractContext): AttractMode {
  const { board, fx, sequences } = base;
  let running = false;
  let token = 0;
  let loop: Promise<void> | null = null;
  let wake: (() => void) | null = null;
  let cam: AttractCamera | null = null;

  const openGame = () => { const g = new Chess(); for (const san of ATTRACT_SCRIPT) g.move(san); return g; };
  const OPEN_FEN = openGame().fen();

  const sleep = (ms: number) => new Promise<void>((res) => {
    const id = setTimeout(() => { wake = null; res(); }, ms);
    wake = () => { clearTimeout(id); wake = null; res(); };
  });
  const alive = (tok: number) => running && tok === token;
  const rand = (a: number, b: number) => a + Math.random() * (b - a);

  const settingsNow = (): Readonly<Settings> => {
    const s = base.settings;
    const low = s.graphics?.preset === 'low' || s.quality === 'low';
    return { ...s, captureMode: low ? 'quick' : 'full', animSpeed: 0.85 };
  };
  const ctxFor = (move: MoveResult): SequenceContext => ({
    move, board, camera: cam!, fx, registry: base.registry, bus: base.bus, settings: settingsNow(), kinematics: base.kinematics,
  });

  async function play(m: Move, game: Chess, tok: number): Promise<void> {
    const mr = moveResult(m, game);
    const ctx = ctxFor(mr);
    if (mr.isCastle) await sequences.castle(ctx);
    else if (mr.captured) await sequences.capture(ctx);
    else await sequences.move(ctx);
    if (alive(tok) && mr.check && !mr.mate) await sequences.check(ctx, kingSquare(game, game.turn()));
  }

  function pick(game: Chess): Move | null {
    const moves = game.moves({ verbose: true }).filter((m) => !m.promotion && !m.san.includes('#'));
    const caps = moves.filter((m) => m.captured);
    const pool = caps.length ? caps : moves;
    return pool.length ? pool[Math.floor(Math.random() * pool.length)] : null;
  }

  async function run(tok: number): Promise<void> {
    const game = new Chess();
    // the scripted opening is played with real move sequences while the camera flies over the armies
    const script = (async () => {
      await sleep(2500);
      for (const san of ATTRACT_SCRIPT) {
        if (!alive(tok)) return;
        const m = game.moves({ verbose: true }).find((x) => x.san === san);
        if (!m) return;
        game.move(m);
        await play(m, new Chess(m.after), tok);
        await sleep(500);
      }
    })();
    await Promise.all([script, sleep(FLY_SECONDS * 1000)]);
    let duels = 0;
    while (alive(tok)) {
      await sleep(rand(2200, 4200));
      if (!alive(tok)) break;
      const m = game.isGameOver() ? null : pick(game);
      if (!m) { board.syncToFen(OPEN_FEN); game.load(OPEN_FEN); continue; }
      game.move(m);
      try { await play(m, game, tok); } catch (e) { console.warn('[attract] sequence failed', e); board.syncToFen(game.fen()); }
      if (!alive(tok)) break;
      duels++;
      if (duels % RESET_EVERY === 0 || game.isGameOver()) {
        await sleep(1500);
        if (!alive(tok)) break;
        board.syncToFen(OPEN_FEN); game.load(OPEN_FEN); // keep the board populated
      }
    }
  }

  return {
    get running() { return running; },

    start() {
      if (running) return;
      running = true;
      const tok = ++token;
      cam = new AttractCamera(base.camera, () => {});
      cam.begin();
      const low = base.settings.graphics?.preset === 'low' || base.settings.quality === 'low';
      cam.glint = (_t, look) => {
        // pieces glint as the dolly passes
        const near = board.allActors().filter((a) => Math.abs(a.root.position.x - look.x) < 2.5 && Math.abs(a.root.position.z - look.z) < 1.8);
        const a = near[Math.floor(Math.random() * near.length)];
        if (a) fx.emit('sparks', new Vector3(a.root.position.x, 0.9 + Math.random() * 0.5, a.root.position.z), { count: low ? 2 : 4, scale: 0.4, speed: 0.5 });
      };
      loop = run(tok).catch((e) => console.warn('[attract] loop failed', e));
    },

    async stop() {
      if (!running && !loop) return;
      running = false; token++;
      wake?.();
      sequences.skip();
      await withTimeout(loop ?? Promise.resolve(), 3000);
      sequences.skip();
      loop = null;
      try { board.syncToFen(START_FEN); } catch (e) { console.warn('[attract] syncToFen failed', e); }
      await cam?.end();
      cam = null;
      gsap.globalTimeline.timeScale(1);
    },
  };
}
