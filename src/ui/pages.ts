// Text pages in the same style: Credits and the How to Play fallback.
import { CREDITS } from '../contracts';
import type { AudioBus } from '../contracts';
import { clear, h } from './dom';
import { backHint } from './controls';
import type { Screen } from './screen';

interface Section { head: string; body: Array<Node | string> }

function page(label: string, kickText: string, build: () => Section[], exit: () => void): Screen {
  const sheet = h('div', { class: 'sheet scroll-y' });
  const el = h('div', { class: 'scr page in', role: 'dialog', 'aria-label': label },
    h('div', { class: 'hd' }, h('p', { class: 'kick', text: kickText }), h('h2', { class: 'ttl', text: label }), h('div', { class: 'rule' })),
    sheet, backHint(exit));
  return {
    el,
    onShow() {
      clear(sheet);
      for (const s of build()) sheet.append(h('section', {}, h('h3', { text: s.head }), h('p', {}, ...s.body)));
      sheet.scrollTop = 0;
    },
    back() { exit(); return true; },
  };
}

export function createCredits(audio: AudioBus, exit: () => void): Screen {
  return page('Credits', 'Made by', () => [
    { head: 'Developed by', body: [h('span', { class: 'dev', text: CREDITS.developer }), h('br'), h('a', { href: `mailto:${CREDITS.email}`, text: CREDITS.email })] },
    { head: 'Craft', body: ['An original game: Emberhold versus the Rime Host. Every model, texture and sound effect is made in code.'] },
    { head: 'Technology', body: ['three.js (stage), GSAP (animation), Rapier (physics), chess.js (rules), Stockfish 19 (computer opponent, GPL, single-thread WebAssembly).'] },
    { head: 'Music', body: [audio.hasMusic() ? 'Original music theme © its respective owner.' : 'Generated score.'] },
    { head: 'Typefaces', body: ['IM Fell English and EB Garamond, under the SIL Open Font License.'] },
  ], exit);
}

export function createHowTo(exit: () => void): Screen {
  return page('How to Play', 'The rules of the field', () => [
    { head: 'The field', body: ['Emberhold (White) moves first. Select a piece, then a lit tile, or drag it there.'] },
    { head: 'The pieces', body: ['Pawns step forward and strike diagonally. Rooks run straight, bishops slant, knights leap, the queen does both, the king takes one step.'] },
    { head: 'The goal', body: ['Trap the enemy king so it cannot escape: checkmate. A king with no safe move but no check is a stalemate, a draw.'] },
    { head: 'Special moves', body: ['Castling, en passant and promotion work as in standard chess. A pawn on the far rank asks what it becomes.'] },
    { head: 'Controls', body: ['Tap or press Space during an animation to skip it. U undoes, J shows the move list, Esc pauses.'] },
  ], exit);
}
