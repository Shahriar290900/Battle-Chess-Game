// UI composition: screen stack (menu, pause, new-game flow, settings, pages), HUD, game over, promotion, input
// routing (Esc / Android back / shortcuts) and keyboard + gamepad navigation.
import type { AudioBus, EventBus, GameModeConfig, SettingsStore } from '../contracts';
import type { GameController } from '../core/game';
import { createCredits, createHowTo } from './pages';
import { createFlow } from './flow';
import { createGameOverPanel, type GameOverPanel, type PromotionPicker } from './endgame';
import { createHud, type Hud } from './hud';
import type { LoadingScreen } from './loading';
import { createMainMenu, createPause, type MenuHandlers } from './menu';
import { installNav, focusFirst } from './nav';
import type { Portraits } from './portraits';
import type { Screen } from './screen';
import { createSettings } from './settings';
import { installTooltips } from './tooltip';

export interface UiDeps {
  root: HTMLElement;
  controller: GameController;
  settings: SettingsStore;
  bus: EventBus;
  audio: AudioBus;
  loading: LoadingScreen;
  promotion: PromotionPicker;
  /** King portraits (filled in during loading; read lazily). */
  portraits(): Portraits;
  onStart(config: GameModeConfig): void;
  /** Learn area (src/learn), when present. May return a promise that settles when the lesson closes. */
  learn?: { open(kind: 'tutorial' | 'howto' | 'library'): void | Promise<unknown> };
}

export interface Ui {
  loading: LoadingScreen;
  hud: Hud;
  promotion: PromotionPicker;
  gameOver: GameOverPanel;
  showMenu(): void;
  openSettings(): void;
  /** Android back / Esc. Returns true if the UI consumed it. */
  handleBack(): boolean;
  /** True while a modal covers the board (board input should be ignored). */
  readonly modalOpen: boolean;
}

export function createUi(d: UiDeps): Ui {
  const { controller, settings, promotion, loading } = d;
  let overlayTimer = 0;
  const stack: Screen[] = [];
  const top = () => stack[stack.length - 1] ?? null;

  const reveal = (s: Screen) => {
    s.onShow?.();
    s.el.hidden = false;
    focusFirst(s.el);
    hud.setSuspended(true);
  };
  const push = (s: Screen) => { const t = top(); if (t) { t.el.hidden = true; t.onHide?.(); } stack.push(s); reveal(s); };
  const pop = () => {
    const s = stack.pop();
    if (s) { s.el.hidden = true; s.onHide?.(); }
    const t = top();
    if (t) reveal(t); else hud.setSuspended(false);
  };
  const clearAll = () => { while (stack.length) { const s = stack.pop()!; s.el.hidden = true; s.onHide?.(); } hud.setSuspended(false); };
  /** Replace the whole stack with one screen (menu <-> pause). */
  const only = (s: Screen) => { clearAll(); push(s); };

  const running = () => { const s = controller.snapshot(); return !!s.mode && s.state !== 'menu' && s.state !== 'boot' && s.state !== 'loading'; };

  const learnAvailable = () => !!d.learn;
  const openLearn = (k: 'tutorial' | 'howto' | 'library') => {
    clearAll();
    const r = d.learn?.open(k);
    if (r && typeof (r as Promise<unknown>).then === 'function') void (r as Promise<unknown>).then(() => { if (!top() && !running()) only(menu); }).catch(() => undefined);
  };

  const flow = createFlow({
    settings, portraits: d.portraits,
    start: (c) => { clearAll(); gameOver.close(); d.onStart(c); },
    exit: () => pop(),
  });
  const credits = createCredits(d.audio, () => pop());
  const howTo = createHowTo(() => pop());
  const settingsScreen = createSettings({
    settings, audio: d.audio, learnAvailable,
    replayLesson: () => { settings.set('tutorialSeen', true); openLearn('tutorial'); },
    exit: () => pop(),
  });

  const handlers: MenuHandlers = {
    resume: () => clearAll(),
    playAi: () => { flow.open('vs-ai'); push(flow); },
    twoPlayers: () => { flow.open('hotseat'); push(flow); },
    howTo: () => (learnAvailable() && !running() ? openLearn('howto') : push(howTo)),
    library: () => openLearn('library'),
    settings: () => push(settingsScreen),
    credits: () => push(credits),
    resign: () => { clearAll(); void controller.resign(); },
    mainMenu: () => only(menu),
    learnAvailable,
    beginLesson: () => openLearn('tutorial'),
  };
  const menu = createMainMenu(controller, settings, handlers);
  const pause = createPause(controller, handlers);

  const hud = createHud(controller, settings, {
    onMenu: () => { if (!top()) only(pause); },
    onSettings: () => { if (!top()) push(settingsScreen); },
    onUndo: () => { void controller.undo(); gameOver.close(); },
    onSkip: () => controller.skip(),
  });
  const gameOver = createGameOverPanel({
    onRematch: () => { const m = controller.gameMode; if (m) d.onStart({ ...m }); },
    onMenu: () => only(menu),
    onToggle: (o) => hud.setSuspended(o || stack.length > 0),
  });

  const screens = [menu, pause, flow, settingsScreen, credits, howTo];
  for (const s of screens) s.el.hidden = true;
  d.root.append(hud.el, ...screens.map((s) => s.el), promotion.el, gameOver.el);
  d.root.append(loading.el); // the loading screen stays on top
  installTooltips(d.root);

  // Game-over overlay appears shortly after the final sequence.
  d.bus.on('game:over', (end) => {
    clearTimeout(overlayTimer);
    overlayTimer = window.setTimeout(() => { if (controller.snapshot().result && !top()) gameOver.show(end, controller.gameMode); }, 250);
  });
  d.bus.on('game:start', () => { clearTimeout(overlayTimer); gameOver.close(); });

  const ui: Ui = {
    loading, hud, promotion, gameOver,
    showMenu: () => only(menu),
    openSettings: () => { if (!top()) push(settingsScreen); },
    get modalOpen() { return stack.length > 0 || promotion.isOpen || gameOver.isOpen; },
    handleBack() {
      if (!loading.el.hidden && !loading.el.classList.contains('fade-out')) return false;
      if (promotion.isOpen) { promotion.cancel(); return true; }
      const t = top();
      if (t) { if (t.back?.()) return true; pop(); return true; }
      if (gameOver.isOpen) { gameOver.close(); return true; }
      if (running()) { only(pause); return true; }
      return false;
    },
  };

  window.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') { if (ui.handleBack()) e.preventDefault(); return; }
    if (ui.modalOpen || e.ctrlKey || e.metaKey || e.altKey || !running()) return;
    const a = document.activeElement;
    if (a && a !== document.body && (a as HTMLElement).closest?.('input,select,textarea')) return;
    const k = e.key.toLowerCase();
    const s = controller.snapshot();
    if (k === 'u') { if (s.canUndo) { void controller.undo(); gameOver.close(); e.preventDefault(); } }
    else if (k === 'j') { hud.toggleJournal(); e.preventDefault(); }
    else if ((e.key === ' ' || e.key === 'Enter') && s.busy && (!a || a === document.body || a.tagName === 'CANVAS')) { controller.skip(); e.preventDefault(); }
  });
  installNav({
    active: () => (promotion.isOpen ? promotion.el : top()?.el ?? (gameOver.isOpen ? gameOver.el : null)),
    back: () => ui.handleBack(),
  });
  return ui;
}
