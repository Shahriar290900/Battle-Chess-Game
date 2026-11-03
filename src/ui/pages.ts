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

const GITHUB = CREDITS.github;

const link = (href: string, text: string, tip: string, external = true, cls = '') =>
  h('a', { href, text, class: cls, 'data-nav': '', 'data-tip': tip, ...(external ? { target: '_blank', rel: 'noopener noreferrer' } : {}) });

/** Credits: the game, the developer, GitHub and email only, plus one small "Licences" link. */
export function createCredits(_audio: AudioBus, exit: () => void, openLicences: () => void): Screen {
  const lic = h('button', { class: 'lic-link', type: 'button', 'data-nav': '', 'data-tip': 'Licences|Third-party licences: Stockfish (GPL), CC0 audio and the open fonts.', text: 'Licences' });
  lic.addEventListener('click', openLicences);
  const sheet = h('div', { class: 'sheet credits-sheet' },
    h('p', { class: 'cr-game', text: 'Battle Chess: Emberhold versus the Rime Host' }),
    h('div', { class: 'ornament' }),
    h('p', { class: 'cr-by', text: 'Developed by' }),
    h('p', { class: 'dev', text: CREDITS.developer }),
    h('div', { class: 'cr-links' },
      link(`https://${GITHUB}`, GITHUB, 'GitHub|Opens the developer\'s GitHub profile in your browser.'),
      link(`mailto:${CREDITS.email}`, CREDITS.email, 'Email|Write to the developer.', false)));
  const el = h('div', { class: 'scr page in', role: 'dialog', 'aria-label': 'Credits' },
    h('div', { class: 'hd' }, h('p', { class: 'kick', text: 'Made by' }), h('h2', { class: 'ttl', text: 'Credits' }), h('div', { class: 'rule' })),
    sheet, h('div', { class: 'lic-row' }, lic), backHint(exit));
  return { el, back() { exit(); return true; } };
}

/** Plain page listing the third-party licences the GPL and font licences require us to show. */
export function createLicences(exit: () => void): Screen {
  const a = (href: string, text: string) => link(href, text, `${text}|Opens the licence text.`, true, 'blk');
  return page('Licences', 'Third-party notices', () => [
    { head: 'Stockfish (computer opponent)', body: ['Stockfish 19, single-thread WebAssembly build, is free software under the GNU General Public License v3. Source code: stockfishchess.org.', a('/engine/Copying.txt', 'Read the licence (Copying.txt)')] },
    { head: 'Sound effects', body: ['Built from public-domain CC0 1.0 sound packs by Kenney, rubberduck, StarNinjas, themightyglider, artisticdude, qubodup, bart and others, then layered and processed. CC0 needs no attribution; the full list is in docs/audio/LICENSES.md in the source.'] },
    { head: 'Typefaces', body: ['IM Fell English (Igino Marini) and EB Garamond (Georg Duffner, Octavio Pardo) under the SIL Open Font License 1.1.', a('/fonts/OFL-IMFellEnglish.txt', 'IM Fell English licence'), a('/fonts/OFL-EBGaramond.txt', 'EB Garamond licence')] },
    { head: 'Libraries', body: ['three.js, chess.js and Rapier are used under their open-source licences; GSAP under its standard no-charge licence.'] },
  ], exit);
}

export function createHowTo(exit: () => void): Screen {
  return page('How to Play', 'The rules of the field', () => [
    { head: 'The field', body: ['Emberhold (White) moves first. Select a piece, then a lit tile, or drag it there.'] },
    { head: 'The pieces', body: ['Pawns step forward and strike diagonally. Rooks run straight, bishops slant, knights leap, the queen does both, the king takes one step.'] },
    { head: 'The goal', body: ['Trap the enemy king so it cannot escape: checkmate. A king with no safe move but no check is a stalemate, a draw.'] },
    { head: 'Special moves', body: ['Castling, en passant and promotion work as in standard chess. A pawn on the far rank asks what it becomes.'] },
    { head: 'Controls', body: ['Tap or press Space during an animation to skip it. U undoes, M shows the move list, F toggles the free camera, Esc pauses. See Settings, Controls for everything.'] },
  ], exit);
}
