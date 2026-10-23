// Tiny DOM helpers for the Learn area (kept local: Learn must not depend on the themed src/ui modules).
type Child = Node | string | number | null | undefined | false;
type Props = Record<string, unknown> | null | undefined;

export function h<K extends keyof HTMLElementTagNameMap>(tag: K, props?: Props, ...children: Child[]): HTMLElementTagNameMap[K] {
  const el = document.createElement(tag);
  if (props) {
    for (const [k, v] of Object.entries(props)) {
      if (v === undefined || v === null || v === false) continue;
      if (k === 'class') el.className = String(v);
      else if (k === 'text') el.textContent = String(v);
      else if (k.startsWith('on') && typeof v === 'function') el.addEventListener(k.slice(2).toLowerCase(), v as EventListener);
      else if (v === true) el.setAttribute(k, '');
      else el.setAttribute(k, String(v));
    }
  }
  for (const c of children) {
    if (c === null || c === undefined || c === false) continue;
    el.append(typeof c === 'object' ? c : document.createTextNode(String(c)));
  }
  return el;
}

export function clear(el: Element): void { while (el.firstChild) el.removeChild(el.firstChild); }

/** Every interactive Learn control carries `data-tip="Title|One-line description"` for the shared tooltip system. */
export const tip = (title: string, description: string): string => `${title}|${description}`;

/** A text button with the Learn button classes and a tooltip. */
export function btn(label: string, tipText: string, onClick: () => void, cls = ''): HTMLButtonElement {
  return h('button', { class: `learn-btn ${cls}`.trim(), type: 'button', 'data-tip': tipText, onClick }, label);
}

export const sleep = (ms: number) => new Promise<void>((r) => setTimeout(r, ms));

export function isTouch(): boolean {
  try { return window.matchMedia('(pointer: coarse)').matches; } catch { return false; }
}
