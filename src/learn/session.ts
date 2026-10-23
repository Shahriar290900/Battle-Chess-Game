// A Learn session owns everything a mode borrows from the game: the board, the camera, the attract flyover, the
// HUD space and the key handling. close() always puts it all back (board FEN, camera seat, LOD, reserve, attract).
import type { CameraRigImpl } from '../camera/cameraRig';
import type { BoardImpl } from '../render/board';
import type { Side } from '../contracts';
import { START_FEN } from '../core/rules';
import type { AppServices } from '../main';
import { h, sleep } from './dom';
import { LearnStage } from './stage';
import { createPaneManager, type PaneManager } from './panes';

export interface CloseOptions {
  /** Reopen the main menu afterwards (default true). */
  toMenu?: boolean;
  /** Do not touch the board / camera: a new game is about to replace them. */
  keepBoard?: boolean;
}

export interface Session {
  readonly root: HTMLElement;
  readonly services: AppServices;
  readonly kind: string;
  /** Run when the session ends (reverse order). */
  addCleanup(fn: () => void | Promise<void>): void;
  stage(): LearnStage;
  panes(): PaneManager;
  /** Bottom space (px) the camera leaves free for the caption card. */
  setReserve(px: number): void;
  /** Escape / Android back: return true when consumed. */
  onBack: (() => boolean) | null;
  close(opts?: CloseOptions): Promise<void>;
  readonly closed: boolean;
}

const EMPTY_FEN = '8/8/8/8/8/8/8/8 w - - 0 1';
export { EMPTY_FEN };

export async function beginSession(s: AppServices, kind: string, exit: (o: CloseOptions) => void, opts: { lod1?: boolean } = {}): Promise<Session> {
  const uiRoot = (document.getElementById('ui-root') ?? document.body) as HTMLElement;
  const board = s.board as BoardImpl;
  const rig = s.camera as CameraRigImpl;
  const wasAttract = !!s.attract?.running;

  await s.attract?.stop();
  // an AI move or sequence may still be in flight: let it land before taking the board
  const snap0 = s.controller.snapshot();
  if (snap0.busy || snap0.thinking) await Promise.race([s.controller.settled(), sleep(3000)]);
  s.sequences.skip();

  const snap = s.controller.snapshot();
  const inGame = !!snap.mode && snap.state !== 'menu' && snap.state !== 'boot' && snap.state !== 'loading';
  const savedSeat: Side = rig.seat;
  const savedLod = s.registry.lod;
  if (snap.check) board.tintSquare(snap.check, null);
  if (opts.lod1) s.registry.lod = 1;

  const root = h('div', { class: `learn-root learn-${kind}`, role: 'dialog', 'aria-label': kind });
  uiRoot.append(root);
  uiRoot.classList.add('learn-on');

  const cleanups: Array<() => void | Promise<void>> = [];
  let stage: LearnStage | null = null;
  let panes: PaneManager | null = null;
  let closed = false;
  let closing: Promise<void> | null = null;

  const onKey = (e: KeyboardEvent) => {
    if (e.key !== 'Escape') return;
    if (session.onBack?.()) { e.preventDefault(); e.stopImmediatePropagation(); }
    else { e.preventDefault(); e.stopImmediatePropagation(); void session.close(); }
  };
  window.addEventListener('keydown', onKey, true);

  const session: Session = {
    root, services: s, kind,
    get closed() { return closed; },
    onBack: null,
    addCleanup(fn) { cleanups.push(fn); },
    stage() { return (stage ??= new LearnStage(s, root)); },
    panes() { return (panes ??= createPaneManager(s.renderer)); },
    setReserve(px) { rig.setReserve(px); },
    close(o = {}) {
      closing ??= (async () => {
        closed = true;
        window.removeEventListener('keydown', onKey, true);
        for (const fn of cleanups.reverse()) { try { await fn(); } catch (e) { console.warn('[learn] cleanup failed', e); } }
        stage?.dispose(); stage = null;
        panes?.dispose(); panes = null;
        s.sequences.skip();
        s.registry.lod = savedLod;
        root.remove();
        uiRoot.classList.remove('learn-on');
        if (!o.keepBoard) {
          await rig.restore(0);
          const cur = s.controller.snapshot();
          const live = !!cur.mode && cur.state !== 'menu' && cur.state !== 'boot' && cur.state !== 'loading';
          board.root.visible = true;
          board.syncToFen(live ? cur.fen : START_FEN);
          s.fx.setStaticActors?.(board.allActors());
          if (live && cur.check) board.tintSquare(cur.check, 0xff3a2a);
          void rig.toSeat(live ? savedSeat : 'w', { instant: true });
          const hud = uiRoot.querySelector('.hud') as HTMLElement | null;
          rig.setReserve(hud && !hud.hidden ? Math.round(window.innerHeight - hud.getBoundingClientRect().top + 6) : 0);
          if (!inGame && !live && wasAttract) s.attract?.start();
        } else {
          board.root.visible = true;
          rig.setReserve(0);
        }
        if (o.toMenu !== false) exit(o);
      })();
      return closing;
    },
  };
  return session;
}
