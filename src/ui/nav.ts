// Keyboard and gamepad navigation: arrow keys / d-pad move focus spatially between `[data-nav]` elements inside the
// topmost open screen; Enter/Space (A) activate through the native button click; Esc (B) goes back. Gamepad polling
// only runs while a pad is connected AND a screen is open, so it costs nothing otherwise.
export interface NavDeps {
  /** The element of the topmost open screen, or null when the board has the focus. */
  active(): HTMLElement | null;
  back(): boolean;
}

type Dir = 'up' | 'down' | 'left' | 'right';

const visible = (el: HTMLElement) => !el.hidden && !(el as HTMLButtonElement).disabled && el.getClientRects().length > 0 && !el.closest('[hidden]');

export function focusFirst(root: HTMLElement): void {
  const pref = root.querySelector<HTMLElement>('[data-autofocus]');
  const first = pref && visible(pref) ? pref : [...root.querySelectorAll<HTMLElement>('[data-nav]')].find(visible);
  first?.focus({ preventScroll: true });
}

function move(root: HTMLElement, dir: Dir): boolean {
  const items = [...root.querySelectorAll<HTMLElement>('[data-nav]')].filter(visible);
  if (!items.length) return false;
  const cur = document.activeElement as HTMLElement | null;
  const from = cur && root.contains(cur) && items.includes(cur) ? cur : items.find((i) => i.contains(cur)) ?? null;
  if (!from) { items[0].focus({ preventScroll: true }); return true; }
  const a = from.getBoundingClientRect();
  const ax = a.left + a.width / 2, ay = a.top + a.height / 2;
  let best: HTMLElement | null = null, bestScore = Infinity;
  for (const it of items) {
    if (it === from) continue;
    const r = it.getBoundingClientRect();
    const dx = r.left + r.width / 2 - ax, dy = r.top + r.height / 2 - ay;
    const main = dir === 'left' ? -dx : dir === 'right' ? dx : dir === 'up' ? -dy : dy;
    if (main <= 2) continue;
    const cross = dir === 'left' || dir === 'right' ? Math.abs(dy) : Math.abs(dx);
    const score = main + cross * 2.2;
    if (score < bestScore) { bestScore = score; best = it; }
  }
  if (!best) return false;
  best.focus({ preventScroll: true });
  best.scrollIntoView({ block: 'nearest', inline: 'nearest' });
  return true;
}

export function installNav(d: NavDeps): void {
  const KEYS: Record<string, Dir> = { ArrowUp: 'up', ArrowDown: 'down', ArrowLeft: 'left', ArrowRight: 'right' };
  window.addEventListener('keydown', (e) => {
    const root = d.active();
    if (!root || e.defaultPrevented || e.altKey || e.ctrlKey || e.metaKey) return;
    const dir = KEYS[e.key];
    if (dir) { if (move(root, dir)) e.preventDefault(); return; }
    if (e.key === 'Tab') {
      // keep Tab inside the open screen
      const items = [...root.querySelectorAll<HTMLElement>('[data-nav]')].filter(visible);
      if (!items.length) return;
      const i = items.indexOf(document.activeElement as HTMLElement);
      const n = items[(i + (e.shiftKey ? -1 : 1) + items.length) % items.length];
      n.focus({ preventScroll: true });
      e.preventDefault();
    }
  });

  // ---- gamepad (standard mapping): d-pad / left stick, A = activate, B = back
  let raf = 0;
  let held = '';
  let nextAt = 0;
  const poll = () => {
    raf = 0;
    const root = d.active();
    const pad = [...(navigator.getGamepads?.() ?? [])].find((p) => p && p.connected);
    if (!pad) return;
    if (root) {
      const b = pad.buttons;
      const ax = pad.axes[0] ?? 0, ay = pad.axes[1] ?? 0;
      let dir: Dir | '' = b[12]?.pressed || ay < -0.6 ? 'up' : b[13]?.pressed || ay > 0.6 ? 'down' : b[14]?.pressed || ax < -0.6 ? 'left' : b[15]?.pressed || ax > 0.6 ? 'right' : '';
      const act = b[0]?.pressed ? 'a' : b[1]?.pressed ? 'b' : '';
      const now = performance.now();
      const key = dir || act;
      if (key && (key !== held || now >= nextAt)) {
        nextAt = now + (key === held ? 140 : 380);
        held = key;
        document.documentElement.dataset.input = 'kbd';
        if (dir) {
          const cur = document.activeElement as HTMLElement | null;
          // on a stepper row left/right changes the value, like the keyboard
          if ((dir === 'left' || dir === 'right') && cur?.classList.contains('row')) cur.dispatchEvent(new KeyboardEvent('keydown', { key: dir === 'left' ? 'ArrowLeft' : 'ArrowRight', bubbles: true, cancelable: true }));
          else move(root, dir);
        } else if (act === 'a') (document.activeElement as HTMLElement | null)?.click?.();
        else if (act === 'b') d.back();
      } else if (!key) held = '';
      dir = '';
    }
    raf = requestAnimationFrame(poll);
  };
  const start = () => { if (!raf) raf = requestAnimationFrame(poll); };
  window.addEventListener('gamepadconnected', start);
  window.addEventListener('gamepaddisconnected', () => { cancelAnimationFrame(raf); raf = 0; });
  if ((navigator.getGamepads?.() ?? []).some(Boolean)) start();
}
