// Retro LCD/VFD display: a tiny embedded 5x7 bitmap font drawn on a canvas, with unlit "ghost" pixels, a pixel grid
// and CSS scanlines. Amber phosphor for Emberhold, ice-blue for the Rime Host. No fonts, no images.
const GLYPHS: Record<string, number[]> = {
  A: [14, 17, 17, 31, 17, 17, 17], B: [30, 17, 17, 30, 17, 17, 30], C: [14, 17, 16, 16, 16, 17, 14], D: [30, 17, 17, 17, 17, 17, 30],
  E: [31, 16, 16, 30, 16, 16, 31], F: [31, 16, 16, 30, 16, 16, 16], G: [14, 17, 16, 23, 17, 17, 15], H: [17, 17, 17, 31, 17, 17, 17],
  I: [14, 4, 4, 4, 4, 4, 14], J: [7, 2, 2, 2, 2, 18, 12], K: [17, 18, 20, 24, 20, 18, 17], L: [16, 16, 16, 16, 16, 16, 31],
  M: [17, 27, 21, 21, 17, 17, 17], N: [17, 17, 25, 21, 19, 17, 17], O: [14, 17, 17, 17, 17, 17, 14], P: [30, 17, 17, 30, 16, 16, 16],
  Q: [14, 17, 17, 17, 21, 18, 13], R: [30, 17, 17, 30, 20, 18, 17], S: [15, 16, 16, 14, 1, 1, 30], T: [31, 4, 4, 4, 4, 4, 4],
  U: [17, 17, 17, 17, 17, 17, 14], V: [17, 17, 17, 17, 17, 10, 4], W: [17, 17, 17, 21, 21, 21, 10], X: [17, 17, 10, 4, 10, 17, 17],
  Y: [17, 17, 17, 10, 4, 4, 4], Z: [31, 1, 2, 4, 8, 16, 31],
  '0': [14, 17, 19, 21, 25, 17, 14], '1': [4, 12, 4, 4, 4, 4, 14], '2': [14, 17, 1, 2, 4, 8, 31], '3': [31, 2, 4, 2, 1, 17, 14],
  '4': [2, 6, 10, 18, 31, 2, 2], '5': [31, 16, 30, 1, 1, 17, 14], '6': [6, 8, 16, 30, 17, 17, 14], '7': [31, 1, 2, 4, 8, 8, 8],
  '8': [14, 17, 17, 14, 17, 17, 14], '9': [14, 17, 17, 15, 1, 2, 12],
  '.': [0, 0, 0, 0, 0, 12, 12], ':': [0, 12, 12, 0, 12, 12, 0], '-': [0, 0, 0, 31, 0, 0, 0], '+': [0, 4, 4, 31, 4, 4, 0],
  '#': [10, 10, 31, 10, 31, 10, 10], '=': [0, 0, 31, 0, 31, 0, 0], '/': [1, 1, 2, 4, 8, 16, 16], "'": [4, 4, 8, 0, 0, 0, 0],
  '!': [4, 4, 4, 4, 4, 0, 4], '?': [14, 17, 1, 2, 4, 0, 4], ',': [0, 0, 0, 0, 12, 4, 8], '*': [0, 4, 21, 14, 21, 4, 0],
  '%': [24, 25, 2, 4, 8, 19, 3], '_': [0, 0, 0, 0, 0, 0, 31], '>': [8, 4, 2, 1, 2, 4, 8], '<': [2, 4, 8, 16, 8, 4, 2],
  '(': [2, 4, 8, 8, 8, 4, 2], ')': [8, 4, 2, 2, 2, 4, 8], '[': [14, 8, 8, 8, 8, 8, 14], ']': [14, 2, 2, 2, 2, 2, 14],
  '█': [31, 31, 31, 31, 31, 31, 31], '░': [0, 0, 0, 0, 0, 0, 0], ' ': [0, 0, 0, 0, 0, 0, 0],
};

export type LcdTheme = 'amber' | 'ice';
const THEMES: Record<LcdTheme, { bg: string; on: string; ghost: string }> = {
  amber: { bg: '#150d03', on: '#ffb21a', ghost: 'rgba(255,178,26,0.07)' },
  ice: { bg: '#03101a', on: '#9fe4ff', ghost: 'rgba(159,228,255,0.07)' },
};

export interface Lcd {
  el: HTMLElement;
  setTheme(t: LcdTheme): void;
  /** Replace all rows (rows beyond `rows` are ignored, text is upper-cased and clipped to `cols`). */
  set(lines: string[]): void;
  /** A row-level meter: filled blocks 0..1 across the row width. */
  readonly cols: number;
}

export function createLcd(cols: number, rows: number, theme: LcdTheme = 'amber', cls = ''): Lcd {
  const CW = 6, CH = 8, SCALE = 2;
  const canvas = document.createElement('canvas');
  canvas.width = cols * CW * SCALE;
  canvas.height = rows * CH * SCALE;
  canvas.className = 'lcd-canvas';
  const g = canvas.getContext('2d')!;
  const el = document.createElement('div');
  el.className = `lcd ${cls}`.trim();
  el.setAttribute('role', 'img');
  el.append(canvas);
  let th = THEMES[theme];
  let lines: string[] = [];
  let last = '';

  function paint() {
    g.fillStyle = th.bg;
    g.fillRect(0, 0, canvas.width, canvas.height);
    for (let r = 0; r < rows; r++) {
      const text = (lines[r] ?? '').toUpperCase().slice(0, cols);
      for (let c = 0; c < cols; c++) {
        const glyph = GLYPHS[text[c] ?? ' '] ?? GLYPHS[' '];
        for (let y = 0; y < 7; y++) for (let x = 0; x < 5; x++) {
          const lit = (glyph[y] >> (4 - x)) & 1;
          g.fillStyle = lit ? th.on : th.ghost;
          g.fillRect((c * CW + x) * SCALE, (r * CH + y) * SCALE, SCALE - 0.4, SCALE - 0.4);
        }
      }
    }
  }
  paint();
  return {
    el, cols,
    setTheme(t) { th = THEMES[t]; el.dataset.theme = t; last = ''; paint(); },
    set(next) {
      const key = next.join('\n');
      if (key === last) return;
      last = key;
      lines = next;
      el.setAttribute('aria-label', next.filter(Boolean).join('. '));
      paint();
    },
  };
}

/** `[#####-----]`-style meter text of a given width. */
export function meterText(width: number, fraction: number): string {
  const n = Math.max(0, Math.min(width, Math.round(fraction * width)));
  return '█'.repeat(n) + '░'.repeat(width - n);
}
