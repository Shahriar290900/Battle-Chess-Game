// Tiny DOM helpers + inline SVG icons (no web fonts, no image files: the APK must work offline).
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

/** UI glyph paths (24x24, filled). */
export const ICON = {
  menu: 'M4 6.5h16v2H4zm0 4.5h16v2H4zm0 4.5h16v2H4z',
  undo: 'M12.5 8c-2.65 0-5.05 1-6.9 2.6L2 7v9h9l-3.62-3.62A7.96 7.96 0 0 1 12.5 10c3.54 0 6.55 2.31 7.6 5.5l2.37-.78A10.5 10.5 0 0 0 12.5 8z',
  gear: 'M19.4 13a7.6 7.6 0 0 0 0-2l2.1-1.6-2-3.5-2.5 1a7.4 7.4 0 0 0-1.7-1L15 3h-4l-.4 2.9a7.4 7.4 0 0 0-1.7 1l-2.5-1-2 3.5L6.6 11a7.6 7.6 0 0 0 0 2l-2.1 1.6 2 3.5 2.5-1a7.4 7.4 0 0 0 1.7 1L11 21h4l.4-2.9a7.4 7.4 0 0 0 1.7-1l2.5 1 2-3.5zM13 15.5a3.5 3.5 0 1 1 0-7 3.5 3.5 0 0 1 0 7z',
  skip: 'M5 5l9 7-9 7zm10 0h3v14h-3z',
  list: 'M4 5h2v2H4zm4 0h12v2H8zM4 11h2v2H4zm4 0h12v2H8zM4 17h2v2H4zm4 0h12v2H8z',
  flag: 'M6 3h2v18H6zm3 1h10l-2.5 4L19 12H9z',
  close: 'M6.4 5l5.6 5.6L17.6 5 19 6.4 13.4 12l5.6 5.6-1.4 1.4-5.6-5.6L6.4 19 5 17.6 10.6 12 5 6.4z',
  note: 'M9 3v10.6A3.5 3.5 0 1 0 11 17V8h6V3z',
  noteOff: 'M9 3v10.6A3.5 3.5 0 1 0 11 17V8h6V3zM3 4l1.4-1.4L21 19.2 19.6 20.6z',
  chevron: 'M8 5l8 7-8 7z',
  swords: 'M4 4l6 1 8 8-1.5 1.5-1.5-1.5L13 16l2 2-1.5 1.5L10 16l-3.5 3.5L5 18l3.5-3.5L5 11zM20 4l-1 6-3 3-1.5-1.5L17 8z',
} as const;

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
