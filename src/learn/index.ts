// Learn area entry. main.ts calls createLearn(services) once and wires open(kind) to the menu.
//   kind 'tutorial' : first-launch guided tour on the real board
//   kind 'howto'    : "How to Play" interactive lessons
//   kind 'library'  : Piece Library (codex with 3D inspector and live duel)
// Exiting any mode restores the board / camera / settings; the menu is reopened through `onExit` (set by main).
import './learn.css';
import type { AppServices } from '../main';
import { startCoach, type Coach } from './coach';
import { runHowTo } from './howto';
import { runLibrary } from './library';
import { createProgressStore, type ProgressStore } from './progress';
import { beginSession, type CloseOptions, type Session } from './session';
import { runTutorial } from './tutorial';

export type LearnKind = 'tutorial' | 'howto' | 'library';

export interface LearnApi {
  /** Resolves when the mode has closed and control is back with the menu / game (main re-shows the menu then). */
  open(kind: LearnKind): Promise<void>;
  start(kind: LearnKind): Promise<void>;
  close(): Promise<void>;
  /** Escape / Android back: true if Learn consumed it. */
  handleBack(): boolean;
  readonly isOpen: boolean;
  readonly progress: ProgressStore;
  /** Set by main: called after a mode closes and the menu should return. */
  onExit?: () => void;
}

export function createLearn(s: AppServices): LearnApi {
  const progress = createProgressStore();
  let session: Session | null = null;
  let coach: Coach | null = null;
  let opening = false;
  const uiRoot = () => (document.getElementById('ui-root') ?? document.body) as HTMLElement;

  const waiters: Array<() => void> = [];
  const resolveAll = () => { for (const w of waiters.splice(0)) w(); };

  const exit = (_o: CloseOptions) => {
    session = null;
    resolveAll();
    if (api.onExit) { api.onExit(); return; }
    // fallback when main did not set onExit: ask the debug UI hook (if any) and announce on window
    try { (window as unknown as { __bc?: { ui?: { showMenu?: () => void } } }).__bc?.ui?.showMenu?.(); } catch { /* ignore */ }
    window.dispatchEvent(new CustomEvent('learn:exit'));
  };

  async function startBeginnerGame(): Promise<void> {
    coach?.stop();
    coach = startCoach(s, uiRoot());
    progress.addBeginnerGame();
    s.settings.set('tutorialSeen', true);
    try { await s.controller.newGame({ kind: 'vs-ai', playerSide: 'w', aiLevel: 'easy' }); } finally { resolveAll(); }
  }

  async function open(kind: LearnKind): Promise<void> {
    if (opening) return;
    opening = true;
    try {
      if (session && !session.closed) await session.close({ toMenu: false });
      coach?.stop(); coach = null;
      const sess = await beginSession(s, kind, exit, { lod1: kind === 'library' });
      session = sess;
      const deps = {
        progress,
        startBeginnerGame: () => { void startBeginnerGame(); },
        openTutorial: () => { void sess.close({ toMenu: false }).then(() => open('tutorial')); },
      };
      if (kind === 'tutorial') runTutorial(sess, deps);
      else if (kind === 'howto') runHowTo(sess, deps);
      else runLibrary(sess);
    } catch (e) {
      console.error('[learn] failed to open', kind, e);
      if (session && !session.closed) await session.close();
      resolveAll();
    } finally {
      opening = false;
    }
  }

  const api: LearnApi = {
    open: (k) => { const p = new Promise<void>((r) => { waiters.push(r); }); void open(k); return p; },
    start: (k) => api.open(k),
    close: async () => { if (session && !session.closed) await session.close(); },
    handleBack() {
      if (!session || session.closed) return false;
      if (session.onBack) return session.onBack();
      void session.close();
      return true;
    },
    get isOpen() { return !!session && !session.closed; },
    progress,
  };
  try {
    if (import.meta.env.DEV || new URLSearchParams(location.search).has('debug')) (window as unknown as Record<string, unknown>).__learn = api;
  } catch { /* ignore */ }
  return api;
}
