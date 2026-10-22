// Main menu: a carved wooden bookshelf. Each option is a leather-bound book with a gilt spine title; books lean on
// hover and slide out when chosen. "Play vs Computer" opens a second shelf (side + difficulty books, wax-seal Begin).
import type { AiLevel, GameModeConfig, SettingsStore, Side } from '../contracts';
import type { GameController } from '../core/game';
import { clear, h } from './dom';
import { createToggle, plaque } from './controls';
import { LEVEL_LABEL } from './glyphs';

export interface MenuHandlers {
  onStart(config: GameModeConfig): void;
  onResume(): void;
  onSettings(): void;
  onResign(): void;
  /** Open a Learn area screen (src/learn). Only called when `learnAvailable()`. */
  onLearn(kind: 'tutorial' | 'howto' | 'library'): void;
  learnAvailable(): boolean;
}

export interface Menu {
  el: HTMLElement;
  readonly isOpen: boolean;
  open(): void;
  close(): void;
  /** Android back / Esc: returns true if it consumed the event. */
  back(): boolean;
}

const CREDITS = [
  ['Battle Chess', 'Emberhold versus the Rime Host. An original game: no franchise names, crests or sculpts.'],
  ['Engine', 'Rules by chess.js. The computer opponent is Stockfish (single-thread WebAssembly) in a worker.'],
  ['Craft', 'three.js and GSAP for the stage and its animation. Every texture, model, sound and this very bookshelf is made in code.'],
  ['Music', 'Bring your own tape: load a track in Settings. Sound effects are synthesised.'],
];
const HOWTO = [
  ['The field', 'Emberhold (White) moves first. Click a piece, then a glowing square, or drag it there.'],
  ['The pieces', 'Pawns step forward and strike diagonally. Rooks run straight, bishops slant, knights leap, the queen does both, the king takes one step.'],
  ['The goal', 'Trap the enemy king so it cannot escape (checkmate). A king with no safe move but no check is a stalemate: a draw.'],
  ['Special moves', 'Castling, en passant and promotion all work as in standard chess; a pawn reaching the far rank asks what it becomes.'],
  ['Controls', 'Tap during an animation to skip it. Undo, the move list and Settings are the keys on the chronicle box.'],
];

function book(label: string, idx: number, onClick: () => void, o: { cls?: string; tall?: number; sub?: string } = {}): HTMLButtonElement {
  const b = h('button', { class: `book c${idx % 6} ${o.cls ?? ''}`.trim(), type: 'button', style: { '--bi': String(idx % 6), '--bh': `${o.tall ?? 100}%` } },
    h('span', { class: 'book-band' }), h('span', { class: 'book-title', text: label }), o.sub ? h('span', { class: 'book-sub', text: o.sub }) : null, h('span', { class: 'book-band low' }));
  b.addEventListener('click', () => {
    b.classList.add('pulling');
    window.setTimeout(() => { b.classList.remove('pulling'); onClick(); }, 180);
  });
  return b;
}

export function createMenu(controller: GameController, settings: SettingsStore, hd: MenuHandlers): Menu {
  const shelfMain = h('div', { class: 'shelf shelf-main', role: 'menu' });
  const shelfSub = h('div', { class: 'shelf shelf-sub', hidden: true });
  const note = h('div', { class: 'note', hidden: true });
  const reader = h('div', { class: 'reader', hidden: true });
  const cabinet = h('div', { class: 'cabinet', role: 'dialog', 'aria-modal': 'true', 'aria-label': 'Main menu' },
    h('div', { class: 'cabinet-head' }, h('h1', { class: 'cabinet-title', text: 'Battle Chess' }), h('p', { class: 'cabinet-sub', text: 'Emberhold versus the Rime Host' })),
    note, shelfMain, shelfSub, reader,
    h('div', { class: 'cabinet-foot' }, createToggle({ label: 'Music', value: settings.get().musicEnabled, onChange: (v) => settings.set('musicEnabled', v) }).el));
  const el = h('div', { class: 'overlay menu-overlay', hidden: true }, cabinet);
  let open = false;
  let view: 'root' | 'ai' | 'reader' = 'root';

  function renderMain() {
    clear(shelfMain);
    const s = controller.snapshot();
    const running = !!s.mode && s.state !== 'menu' && s.state !== 'boot' && s.state !== 'loading';
    let i = 0;
    if (running) shelfMain.append(book(s.result ? 'View Board' : 'Continue', i++, () => { api.close(); hd.onResume(); }, { tall: 100 }));
    shelfMain.append(
      book('Play vs Computer', i++, () => show('ai'), { tall: 96 }),
      book('Two Players', i++, () => { api.close(); hd.onStart({ kind: 'hotseat', playerSide: 'w', aiLevel: settings.get().aiLevel }); }, { tall: 90 }),
      book('Settings', i++, () => hd.onSettings(), { tall: 84 }),
      book('How to Play', i++, () => (hd.learnAvailable() ? hd.onLearn('howto') : read('How to Play', HOWTO)), { tall: 92 }),
    );
    if (hd.learnAvailable()) shelfMain.append(book('Piece Library', i++, () => hd.onLearn('library'), { tall: 88 }));
    shelfMain.append(book('Credits', i++, () => read('Credits', CREDITS), { tall: 80 }));
    if (running && !s.result) shelfMain.append(book('Resign', 4, () => { api.close(); hd.onResign(); }, { cls: 'resign', tall: 76 }));
    // first-launch prompt
    const showNote = !settings.get().tutorialSeen && hd.learnAvailable();
    note.hidden = !showNote;
    clear(note);
    if (showNote) {
      note.append(h('p', { class: 'note-text', text: 'New to the field? A short lesson will teach you the pieces.' }),
        h('div', { class: 'note-actions' },
          plaque('Begin lesson', () => { settings.set('tutorialSeen', true); hd.onLearn('tutorial'); }),
          plaque('Not now', () => { settings.set('tutorialSeen', true); note.hidden = true; }, 'quiet')));
    }
  }

  function renderSub() {
    clear(shelfSub);
    const st = settings.get();
    let side: Side = st.playerSide;
    let level: AiLevel = st.aiLevel;
    const sideBooks: HTMLElement[] = [];
    const levelBooks: HTMLElement[] = [];
    const mark = (list: HTMLElement[], on: HTMLElement) => list.forEach((b) => b.classList.toggle('selected', b === on));
    const mkSide = (v: Side, label: string, sub: string, idx: number) => {
      const b = book(label, idx, () => { side = v; mark(sideBooks, b); }, { cls: 'side', tall: 100, sub });
      b.classList.toggle('selected', v === side);
      sideBooks.push(b);
      return b;
    };
    shelfSub.append(
      h('div', { class: 'shelf-label', text: 'Your host' }),
      h('div', { class: 'row-books' }, mkSide('w', 'Emberhold', 'White', 0), mkSide('b', 'Rime Host', 'Black', 2)),
      h('div', { class: 'shelf-label', text: 'Difficulty' }),
      h('div', { class: 'row-books small' }, ...(Object.keys(LEVEL_LABEL) as AiLevel[]).map((l, k) => {
        const b = book(LEVEL_LABEL[l], k + 1, () => { level = l; mark(levelBooks, b); }, { cls: 'level', tall: 80 + k * 6 });
        b.classList.toggle('selected', l === level);
        levelBooks.push(b);
        return b;
      })),
      h('div', { class: 'shelf-actions' },
        plaque('Back', () => show('root'), 'quiet'),
        plaque('Begin', () => { settings.set('playerSide', side); settings.set('aiLevel', level); api.close(); hd.onStart({ kind: 'vs-ai', playerSide: side, aiLevel: level }); }, 'seal')),
    );
  }

  function read(title: string, pages: string[][]) {
    clear(reader);
    reader.append(
      h('h2', { class: 'reader-title', text: title }),
      h('div', { class: 'reader-pages' }, ...pages.map(([t, body]) => h('section', { class: 'reader-sec' }, h('h3', { text: t }), h('p', { text: body })))),
      h('div', { class: 'shelf-actions' }, plaque('Close book', () => show('root'))));
    show('reader');
  }

  function show(v: 'root' | 'ai' | 'reader') {
    view = v;
    shelfMain.hidden = v !== 'root';
    shelfSub.hidden = v !== 'ai';
    reader.hidden = v !== 'reader';
    cabinet.dataset.view = v;
    if (v === 'root') renderMain(); else if (v === 'ai') renderSub();
  }

  const api: Menu = {
    el,
    get isOpen() { return open; },
    open() { open = true; el.hidden = false; show('root'); (cabinet.querySelector('.book') as HTMLElement | null)?.focus({ preventScroll: true }); },
    close() { open = false; el.hidden = true; },
    back() {
      if (!open) return false;
      if (view !== 'root') { show('root'); return true; }
      const s = controller.snapshot();
      if (s.mode && s.state !== 'menu') { api.close(); hd.onResume(); return true; }
      return false;
    },
  };
  settings.subscribe((_, k) => { if (open && view === 'root' && (k === 'tutorialSeen')) renderMain(); });
  return api;
}
