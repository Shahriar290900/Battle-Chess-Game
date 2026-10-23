// Tiny DOM helpers + inline SVG icons (no image files: the APK must work offline; fonts are bundled in public/fonts).
import type { Faction, Role } from '../contracts';

type Child = Node | string | number | null | undefined | false;
type Props = Record<string, unknown> | null | undefined;

export function h<K extends keyof HTMLElementTagNameMap>(tag: K, props?: Props, ...children: Child[]): HTMLElementTagNameMap[K] {
  const el = document.createElement(tag);
  if (props) {
    for (const [k, v] of Object.entries(props)) {
      if (v === undefined || v === null || v === false) continue;
      if (k === 'class') el.className = String(v);
      else if (k === 'text') el.textContent = String(v);
      else if (k === 'style' && typeof v === 'object') Object.assign(el.style, v);
      else if (k.startsWith('on') && typeof v === 'function') el.addEventListener(k.slice(2).toLowerCase(), v as EventListener);
      else if (v === true) el.setAttribute(k, '');
      else el.setAttribute(k, String(v));
    }
  }
  append(el, children);
  return el;
}

export function append(el: Element, children: Child[]): void {
  for (const c of children) {
    if (c === null || c === undefined || c === false) continue;
    el.append(typeof c === 'object' ? c : document.createTextNode(String(c)));
  }
}

export function clear(el: Element): void { while (el.firstChild) el.removeChild(el.firstChild); }

const NS = 'http://www.w3.org/2000/svg';
export function svg(path: string, cls = 'ic', viewBox = '0 0 24 24'): SVGSVGElement {
  const s = document.createElementNS(NS, 'svg');
  s.setAttribute('viewBox', viewBox);
  s.setAttribute('class', cls);
  s.setAttribute('aria-hidden', 'true');
  const p = document.createElementNS(NS, 'path');
  p.setAttribute('d', path);
  s.appendChild(p);
  return s;
}

/** UI glyph paths (24x24, stroked line icons; see .ic in theme.css). */
export const ICON = {
  menu: 'M4 7h16M4 12h16M4 17h16',
  undo: 'M9 14L4 9l5-5M4 9h9a6 6 0 0 1 0 12h-3',
  gear: 'M12 8.5a3.5 3.5 0 1 0 0 7 3.5 3.5 0 0 0 0-7zM12 3v2.5M12 18.5V21M3 12h2.5M18.5 12H21M5.6 5.6l1.8 1.8M16.6 16.6l1.8 1.8M5.6 18.4l1.8-1.8M16.6 7.4l1.8-1.8',
  skip: 'M5 5l8 7-8 7zM17 5v14',
  list: 'M5 4h14v16H5zM8 9h8M8 13h8M8 17h5',
  flag: 'M6 21V4M6 5h11l-2 4 2 4H6',
  close: 'M6 6l12 12M18 6L6 18',
  note: 'M9 18V5l10-2v13M9 18a3 3 0 1 1-3-3 3 3 0 0 1 3 3zM19 16a3 3 0 1 1-3-3 3 3 0 0 1 3 3z',
  chevL: 'M15 5l-7 7 7 7',
  chevR: 'M9 5l7 7-7 7',
  chev2L: 'M12 5l-7 7 7 7M19 5l-7 7 7 7',
  chev2R: 'M12 5l7 7-7 7M5 5l7 7-7 7',
  rotate: 'M20 12a8 8 0 1 1-2.6-5.9M20 4v5h-5',
  board: 'M4 4h16v16H4zM4 9.3h16M4 14.7h16M9.3 4v16M14.7 4v16',
  back: 'M10 6l-6 6 6 6M4 12h16',
} as const;

const CREST_SHIELD = 'M12 2.5l8 2.6v6.4c0 4.700-3.300 8-8 10-4.700-2-8-5.300-8-10V5.100z';
const CREST_MARK = {
  emberhold: 'M12 6.500c.9 2.400 3.400 3.800 3.400 6.600a3.400 3.400 0 0 1-6.800 0c0-1.500.7-2.300 1.400-3 .2 1 .8 1.400 1.300 1.500-.3-2 .1-3.800.7-5.100z',
  rime: 'M12 6.500v11M7.300 9.200l9.400 5.600M16.700 9.200l-9.400 5.600',
} as const;

/** Heraldic crest: a shield with the faction's mark (flame / ice crystal). */
export function crest(faction: Faction, cls = ''): SVGSVGElement {
  const s = document.createElementNS(NS, 'svg');
  s.setAttribute('viewBox', '0 0 24 24');
  s.setAttribute('class', `ic crest ${faction} ${cls}`.trim());
  s.setAttribute('aria-hidden', 'true');
  for (const d of [CREST_SHIELD, CREST_MARK[faction]]) {
    const p = document.createElementNS(NS, 'path');
    p.setAttribute('d', d);
    s.appendChild(p);
  }
  return s;
}

/** Chess silhouettes (24x24). Styled by faction in CSS. */
const PIECE_PATH: Record<Role, string> = {
  pawn: 'M12 3.5a3.2 3.2 0 1 1 0 6.4 3.2 3.2 0 0 1 0-6.4zM9.6 10.8h4.8l1.7 5.4H7.9zM6.5 17.2h11v2.3h-11z',
  rook: 'M6 3.5h2.6v2h2.1v-2h2.6v2h2.1v-2H18v5.2l-2.1 1.8v4.2l2.1 1.6v2H6v-2l2.1-1.6v-4.2L6 8.7z',
  knight: 'M7.5 20v-2.4c0-2.7 1.2-4.5 3.2-6.2L8.4 9.6 10.2 5l2-1.5 1.2 1.3 2.6-.5 1.7 4.2c.5 3.7-.6 6.1-1.8 9.5v2z',
  bishop: 'M12 2.8l1.2 1.5-1.2 1.6-1.2-1.6zM12 7c3.1 1.5 4.6 3.9 4.6 6.4 0 1.5-1 2.6-2.1 3.1v1.3h2.3V20H7.2v-2.2h2.3v-1.3C8.4 16 7.4 14.900 7.400 13.400 7.400 10.900 8.900 8.500 12 7z',
  queen: 'M3.5 8.2l3.6 4.1.9-6.5 4 5.6 4-5.6.9 6.5 3.6-4.1L19.200 19H4.800zM5.500 20h13v1.700h-13z',
  king: 'M11 2h2v2.100h2.100v2H13v2.200h-2V6.100H8.900v-2H11zM7.200 10h9.600l1.600 8.400H5.600zM5.500 19.400h13V21h-13z',
};

export function pieceIcon(role: Role, faction: Faction, cls = ''): SVGSVGElement {
  return svg(PIECE_PATH[role], `piece-ic ${faction} ${cls}`.trim());
}
