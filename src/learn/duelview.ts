// Live mini-duel: the selected piece fights each enemy role in turn using the REAL capture / check / checkmate
// sequences on the real board (squares chosen by duel.ts). A private camera frames it and the view is drawn through
// a pane (small, 30 fps, paused when hidden). The main camera is parked on the same pose so billboard fx line up,
// and the board is hidden for the main full-screen render (only shown while the pane draws) to keep the GPU cheap.
import { gsap } from 'gsap';
import { PerspectiveCamera, Vector3 } from 'three';
import type { CameraMode, CameraRig, CinematicCameraHandle, Faction, Role } from '../contracts';
import type { BoardImpl } from '../render/board';
import type { AppServices } from '../main';
import { DUEL_ENEMIES, duelScenario, type DuelScenario } from './duel';
import type { Pane, PaneManager } from './panes';
import { sleep } from './dom';

class DuelCamera implements CameraRig {
  readonly camera = new PerspectiveCamera(36, 1, 0.1, 80);
  mode: CameraMode = 'fixed';
  readonly look = new Vector3(0, 0.6, 0);
  private readonly home = { pos: new Vector3(4, 2.6, 4), look: new Vector3(0, 0.6, 0), fov: 36 };
  private tween: gsap.core.Tween | null = null;
  private readonly handle: CinematicCameraHandle = {
    camera: this.camera,
    set: (p, l, fov) => {
      this.tween?.kill(); this.tween = null;
      this.camera.position.copy(p); this.camera.lookAt(l); this.look.copy(l);
      if (fov !== undefined && Math.abs(fov - this.camera.fov) > 1e-4) { this.camera.fov = fov; this.camera.updateProjectionMatrix(); }
    },
  };
  setMode(): void { /* fixed */ }
  async toSeat(): Promise<void> { /* no seats */ }
  borrow(): CinematicCameraHandle { return this.handle; }
  restore(duration = 0.8): Promise<void> {
    this.tween?.kill();
    const p0 = this.camera.position.clone(), l0 = this.look.clone(), f0 = this.camera.fov;
    const s = { t: 0 };
    return new Promise<void>((resolve) => {
      this.tween = gsap.to(s, {
        t: 1, duration: Math.max(0.05, duration), ease: 'power2.inOut',
        onUpdate: () => {
          this.camera.position.lerpVectors(p0, this.home.pos, s.t);
          this.look.lerpVectors(l0, this.home.look, s.t);
          this.camera.lookAt(this.look);
          this.camera.fov = f0 + (this.home.fov - f0) * s.t; this.camera.updateProjectionMatrix();
        },
        onComplete: () => { this.tween = null; resolve(); },
        onInterrupt: () => resolve(),
      });
    });
  }
  shake(): void { /* no shake in the small view */ }
  resize(): void { /* aspect is set by the pane */ }
  update(): void { /* driven by sequences */ }
  frame(sc: DuelScenario, board: BoardImpl): void {
    this.tween?.kill(); this.tween = null;
    const a = board.squareCenter(sc.attackerSq, new Vector3()), d = board.squareCenter(sc.defenderSq, new Vector3());
    const mid = a.clone().lerp(d, 0.5);
    this.home.look.set(mid.x, 0.55, mid.z);
    this.home.pos.set(mid.x + 4.4, 2.5, mid.z + (sc.attackerSide === 'w' ? 3.4 : -3.4));
    this.home.fov = 36;
    this.camera.position.copy(this.home.pos); this.camera.fov = 36; this.camera.updateProjectionMatrix();
    this.camera.lookAt(this.home.look); this.look.copy(this.home.look);
  }
  stop(): void { this.tween?.kill(); this.tween = null; }
}

export interface DuelView {
  readonly pane: Pane;
  readonly el: HTMLCanvasElement;
  setAttacker(faction: Faction, role: Role): void;
  /** One enemy role, or 'all' to cycle through every role. */
  setEnemy(enemy: Role | 'all'): void;
  status: (text: string, enemy: Role) => void;
  dispose(): Promise<void>;
}

export function createDuelView(s: AppServices, panes: PaneManager, rigHandle: CinematicCameraHandle): DuelView {
  const board = s.board as BoardImpl;
  const cam = new DuelCamera();
  const pane = panes.create({ scene: s.scene, camera: cam.camera, maxSide: 480, fps: 30 });
  pane.el.classList.add('learn-duel-canvas');
  pane.el.setAttribute('role', 'img');
  pane.el.setAttribute('aria-label', 'Live duel: the selected piece fights an enemy piece.');
  let attacker: { faction: Faction; role: Role } | null = null;
  let enemy: Role | 'all' = 'all';
  let token = 0;
  let loop: Promise<void> | null = null;
  let disposed = false;
  const view: DuelView = {
    pane, el: pane.el, status: () => {},
    setAttacker(faction, role) { attacker = { faction, role }; restart(); },
    setEnemy(e) { enemy = e; restart(); },
    async dispose() {
      if (disposed) return;
      disposed = true; token++;
      offs.forEach((f) => f());
      s.sequences.skip();
      cam.stop();
      await Promise.race([loop ?? Promise.resolve(), sleep(2500)]);
      s.sequences.skip();
      pane.dispose();
      board.root.visible = true;
    },
  };
  pane.before = () => {
    board.root.visible = true;
    rigHandle.set(cam.camera.position, cam.look, cam.camera.fov);
  };
  pane.after = () => { board.root.visible = false; };
  pane.needsRender = () => true;
  board.root.visible = false;

  const offs = [
    s.bus.on('capture:begin', () => view.status('Closing in…', lastEnemy)),
    s.bus.on('capture:impact', () => view.status('Impact!', lastEnemy)),
    s.bus.on('capture:shatter', () => view.status('The defender shatters.', lastEnemy)),
    s.bus.on('check', () => view.status('Check!', lastEnemy)),
    s.bus.on('taunt', () => view.status('Provoking the king…', lastEnemy)),
    s.bus.on('surrender', () => view.status('Checkmate: the host surrenders.', lastEnemy)),
  ];
  let lastEnemy: Role = 'pawn';

  const waitVisible = async (tok: number) => { while (tok === token && (!pane.visible || document.hidden)) await sleep(250); };

  async function playOne(sc: DuelScenario, tok: number): Promise<void> {
    board.syncToFen(sc.fenBefore);
    s.fx.setStaticActors?.(board.allActors());
    cam.frame(sc, board);
    lastEnemy = sc.defenderRole;
    view.status('Face to face', sc.defenderRole);
    await sleep(1100);
    if (tok !== token) return;
    const ctx = {
      move: sc.move, board, camera: cam, fx: s.fx, registry: s.registry, bus: s.bus, kinematics: s.kinematics,
      settings: { ...s.settings.get(), captureMode: 'full' as const, animSpeed: 1 },
    };
    try {
      if (sc.kind === 'capture') await s.sequences.capture(ctx);
      else {
        await s.sequences.check(ctx, sc.defenderSq);
        if (tok !== token) return;
        await s.sequences.checkmate(ctx, sc.defenderSq);
      }
    } catch (e) { console.warn('[learn] duel sequence failed', e); }
    if (tok !== token) return;
    view.status(sc.kind === 'capture' ? 'Victory.' : 'The king kneels.', sc.defenderRole);
    await sleep(1400);
  }

  async function run(tok: number): Promise<void> {
    while (tok === token && attacker) {
      const list = enemy === 'all' ? DUEL_ENEMIES : [enemy];
      for (const e of list) {
        if (tok !== token || !attacker) return;
        await waitVisible(tok);
        if (tok !== token) return;
        await playOne(duelScenario(attacker.faction, attacker.role, e), tok);
      }
      if (enemy !== 'all') await sleep(300);
    }
  }

  function restart() {
    if (disposed) return;
    token++;
    const tok = token;
    s.sequences.skip();
    const prev = loop;
    loop = (async () => {
      await Promise.race([prev ?? Promise.resolve(), sleep(1500)]); // let the old loop unwind
      if (tok !== token || disposed) return;
      await run(tok);
    })().catch((e) => console.warn('[learn] duel loop failed', e));
  }
  return view;
}
