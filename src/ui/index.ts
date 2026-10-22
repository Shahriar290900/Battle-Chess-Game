// UI composition: panel stack, back-button handling, HUD, menu, settings, promotion, game over.
import type { AudioBus, EventBus, GameModeConfig, SettingsStore } from '../contracts';
import type { GameController } from '../core/game';
import { createHud, type Hud } from './hud';
import { createMenu, type Menu } from './menu';
import { createGameOverPanel, createSettingsPanel, type GameOverPanel, type Panel, type PromotionPicker } from './panels';
import type { LoadingScreen } from './screens';

export interface UiDeps {
  root: HTMLElement;
  controller: GameController;
  settings: SettingsStore;
  bus: EventBus;
  audio: AudioBus;
  loading: LoadingScreen;
  promotion: PromotionPicker;
  onStart(config: GameModeConfig): void;
  /** Learn area (src/learn), when present. */
  learn?: { open(kind: 'tutorial' | 'howto' | 'library'): void };
}

export interface Ui {
  loading: LoadingScreen;
  hud: Hud;
  menu: Menu;
  settingsPanel: Panel;
  promotion: PromotionPicker;
  gameOver: GameOverPanel;
  showMenu(): void;
  openSettings(): void;
  /** Android back / Esc. Returns true if the UI consumed it. */
  handleBack(): boolean;
  /** True while a modal covers the board (input should be ignored). */
  readonly modalOpen: boolean;
}

export function createUi(d: UiDeps): Ui {
  const { controller, settings } = d;
  let overlayTimer = 0;

  const settingsPanel = createSettingsPanel(settings, d.audio);
  const { promotion, loading } = d;
  const menu = createMenu(controller, settings, {
    onStart: (c) => { gameOver.close(); d.onStart(c); },
    onResume: () => { /* the menu closes itself; the game kept running underneath */ },
    onSettings: () => settingsPanel.open(),
    onResign: () => { void controller.resign(); },
    onLearn: (k) => { menu.close(); d.learn?.open(k); },
    learnAvailable: () => !!d.learn,
  });
  const gameOver: GameOverPanel = createGameOverPanel({
    onRematch: () => { const m = controller.gameMode; if (m) d.onStart({ ...m }); },
    onMenu: () => menu.open(),
  });
  const hud = createHud(controller, settings, {
    onMenu: () => menu.open(),
    onSettings: () => settingsPanel.open(),
    onUndo: () => { void controller.undo(); gameOver.close(); },
    onSkip: () => controller.skip(),
  });
  d.root.append(hud.el, promotion.el, gameOver.el, menu.el, settingsPanel.el);
  d.root.append(loading.el); // keep the loading screen on top

  // Game-over overlay appears shortly after the final sequence.
  d.bus.on('game:over', (end) => {
    clearTimeout(overlayTimer);
    overlayTimer = window.setTimeout(() => {
      if (controller.snapshot().result) gameOver.show(end, controller.gameMode);
    }, 250);
  });
  d.bus.on('game:start', () => { clearTimeout(overlayTimer); gameOver.close(); });

  const ui: Ui = {
    loading, hud, menu, settingsPanel, promotion, gameOver,
    showMenu: () => menu.open(),
    openSettings: () => settingsPanel.open(),
    get modalOpen() { return menu.isOpen || settingsPanel.isOpen || promotion.isOpen || gameOver.isOpen; },
    handleBack() {
      if (promotion.isOpen) { promotion.cancel(); return true; }
      if (settingsPanel.isOpen) { settingsPanel.close(); return true; }
      if (gameOver.isOpen) { gameOver.close(); return true; }
      if (menu.isOpen) return menu.back();
      const s = controller.snapshot();
      if (s.mode && s.state !== 'menu') { menu.open(); return true; }
      return false;
    },
  };
  window.addEventListener('keydown', (e) => { if (e.key === 'Escape' && ui.handleBack()) e.preventDefault(); });
  return ui;
}
