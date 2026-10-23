// Main menu (over the live attract-mode board) and the in-game pause overlay.
import type { SettingsStore } from '../contracts';
import type { GameController } from '../core/game';
import { h, clear } from './dom';
import { button, setLabel } from './controls';
import type { Screen } from './screen';
import { isCoarse } from './screen';

export interface MenuHandlers {
  resume(): void;
  playAi(): void;
  twoPlayers(): void;
  howTo(): void;
  library(): void;
  settings(): void;
  credits(): void;
  resign(): void;
  mainMenu(): void;
  learnAvailable(): boolean;
  beginLesson(): void;
}

const gameRunning = (c: GameController) => { const s = c.snapshot(); return !!s.mode && s.state !== 'menu' && s.state !== 'boot' && s.state !== 'loading'; };

/** A two-step destructive button: first click arms it, a second click within 3 s confirms. No dialogs. */
function confirmButton(label: string, confirmLabel: string, run: () => void, tip: string): HTMLButtonElement {
  let timer = 0;
  const b = button(label, () => {
    if (b.classList.contains('armed')) { clearTimeout(timer); b.classList.remove('armed'); setLabel(b, label); run(); return; }
    b.classList.add('armed'); setLabel(b, confirmLabel);
    timer = window.setTimeout(() => { b.classList.remove('armed'); setLabel(b, label); }, 3000);
  }, { cls: 'danger', tip });
  b.addEventListener('blur', () => { clearTimeout(timer); b.classList.remove('armed'); setLabel(b, label); });
  return b;
}

export function createMainMenu(controller: GameController, settings: SettingsStore, hd: MenuHandlers): Screen {
  const list = h('div', { class: 'menu-list', role: 'menu' });
  const note = h('div', { class: 'note fr', hidden: true });
  const foot = h('div', { class: 'menu-foot' },
    h('span', {}, h('i', { class: 'kbd', text: 'Up' }), h('i', { class: 'kbd', text: 'Down' }), 'Navigate'),
    h('span', {}, h('i', { class: 'kbd', text: 'Enter' }), 'Select'), h('span', {}, h('i', { class: 'kbd', text: 'Esc' }), 'Back'));
  if (isCoarse()) foot.hidden = true;
  const el = h('div', { class: 'scr menu in', role: 'dialog', 'aria-label': 'Main menu' },
    h('div', { class: 'col' },
      h('div', { class: 'logo-block' }, h('h1', { class: 'ttl' }, 'Battle', h('br'), 'Chess'), h('p', { class: 'kick', text: 'Emberhold versus the Rime Host' }), h('div', { class: 'rule' })),
      list, note), foot);

  function build() {
    clear(list);
    const s = controller.snapshot();
    const running = gameRunning(controller);
    if (running) list.append(button(s.result ? 'View Board' : 'Continue', hd.resume, { tip: 'Continue|Return to the game in progress.', tipKey: 'Esc' }));
    list.append(
      button('Play vs Computer', hd.playAi, { tip: 'Play vs Computer|Face the Stockfish opponent. Choose your host and its strength.' }),
      button('Two Players', hd.twoPlayers, { tip: 'Two Players|Pass-and-play on one device. The board can turn to face each player.' }),
      button('How to Play', hd.howTo, { tip: 'How to Play|Short guided lessons on the real board.' }));
    if (hd.learnAvailable()) list.append(button('Piece Library', hd.library, { tip: 'Piece Library|Turn each piece in 3D and watch how it moves and fights.' }));
    list.append(
      button('Settings', hd.settings, { tip: 'Settings|Graphics, audio, gameplay and controls.' }),
      button('Credits', hd.credits, { tip: 'Credits|Who made this and what it is built with.' }));
    if (running && !s.result) list.append(confirmButton('Resign', 'Confirm resign', hd.resign, 'Resign|Concede the game. Tap twice to confirm.'));
    list.firstElementChild?.setAttribute('data-autofocus', '');
    const showNote = !settings.get().tutorialSeen && hd.learnAvailable() && !running;
    note.hidden = !showNote;
    clear(note);
    if (showNote) {
      note.append(h('p', { text: 'New to the field? A short lesson teaches you the pieces.' }),
        h('div', { class: 'acts' },
          button('Start', () => { settings.set('tutorialSeen', true); hd.beginLesson(); }, { cls: 'small' }),
          button('Later', () => { settings.set('tutorialSeen', true); }, { cls: 'small' })));
    }
  }
  settings.subscribe((_, k) => { if (k === 'tutorialSeen' && !el.hidden) build(); });
  return {
    el,
    onShow: build,
    back() { if (gameRunning(controller)) { hd.resume(); return true; } return false; },
  };
}

export function createPause(controller: GameController, hd: MenuHandlers): Screen {
  const list = h('div', { class: 'menu-list', role: 'menu' });
  const el = h('div', { class: 'scr pause in', role: 'dialog', 'aria-label': 'Paused' },
    h('div', { class: 'col fr' },
      h('div', { class: 'logo-block' }, h('h1', { class: 'ttl', text: 'Paused' }), h('div', { class: 'rule' })), list));
  function build() {
    clear(list);
    const s = controller.snapshot();
    list.append(
      button('Resume', hd.resume, { cls: 'sel', tip: 'Resume|Back to the board.', tipKey: 'Esc' }),
      button('Settings', hd.settings, { tip: 'Settings|Graphics, audio and gameplay options.' }),
      button('How to Play', hd.howTo, { tip: 'How to Play|A quick refresher on the rules and controls.' }));
    if (!s.result) list.append(confirmButton('Resign', 'Confirm resign', hd.resign, 'Resign|Concede the game. Press twice to confirm.'));
    list.append(button('Main Menu', hd.mainMenu, { tip: 'Main Menu|Leave to the title screen. Your game stays available under Continue.' }));
    list.firstElementChild?.setAttribute('data-autofocus', '');
  }
  return { el, onShow: build, back() { hd.resume(); return true; } };
}
