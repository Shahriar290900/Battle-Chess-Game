// Theme runtime: draws the few procedural textures once (rough-edged frame images for CSS border-image, a painted
// grain tile) and hands them to CSS as custom properties; tracks the visual viewport; tags the page with input modality.
// Everything is cheap, static and generated at startup, so there are no image files and no per-frame cost.
function rng(seed: number) {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function canvas(w: number, h: number): [HTMLCanvasElement, CanvasRenderingContext2D] {
  const c = document.createElement('canvas');
  c.width = w; c.height = h;
  return [c, c.getContext('2d')!];
}

/** A thin, hand-scratched rectangle outline used as a 9-slice border image (slice 32 of 96, drawn at 8 px). */
function frameImage(rgb: string, alpha: number, seed: number): string {
  const S = 96, M = 14, T = 5.5;
  const [c, g] = canvas(S, S);
  const r = rng(seed);
  g.fillStyle = `rgba(${rgb},1)`;
  const line = (horizontal: boolean, pos: number) => {
    let wob = 0;
    for (let i = 0; i < S; i += 2) {
      wob = Math.max(-1.4, Math.min(1.4, wob + (r() - 0.5) * 0.9));
      const a = alpha * (0.72 + r() * 0.28);
      g.globalAlpha = a;
      const thick = T * (0.82 + r() * 0.3);
      if (horizontal) g.fillRect(i, pos + wob - thick / 2, 2.4, thick);
      else g.fillRect(pos + wob - thick / 2, i, thick, 2.4);
    }
  };
  line(true, M); line(true, S - M); line(false, M); line(false, S - M);
  // worn corners: knock out a few chips and add a few specks
  g.globalCompositeOperation = 'destination-out';
  for (const [cx, cy] of [[M, M], [S - M, M], [M, S - M], [S - M, S - M]]) {
    for (let i = 0; i < 3; i++) {
      g.globalAlpha = 0.5 + r() * 0.5;
      g.fillRect(cx + (r() - 0.5) * 12, cy + (r() - 0.5) * 12, 1.5 + r() * 3, 1.5 + r() * 3);
    }
  }
  g.globalCompositeOperation = 'source-over';
  g.fillStyle = `rgba(${rgb},1)`;
  for (let i = 0; i < 26; i++) {
    g.globalAlpha = alpha * 0.55 * r();
    const edge = Math.floor(r() * 4), p = 4 + r() * (S - 8), o = M + (r() - 0.5) * 11;
    if (edge === 0) g.fillRect(p, o, 1.6, 1.6); else if (edge === 1) g.fillRect(p, S - o, 1.6, 1.6);
    else if (edge === 2) g.fillRect(o, p, 1.6, 1.6); else g.fillRect(S - o, p, 1.6, 1.6);
  }
  return `url(${c.toDataURL('image/png')})`;
}

/** Painted-wall grain: soft mottled blobs plus fine speckle in one 256 px tile (wraps at the edges). */
function grainTile(): string {
  const S = 256;
  const [c, g] = canvas(S, S);
  const r = rng(77);
  for (let i = 0; i < 34; i++) {
    const x = r() * S, y = r() * S, rad = 40 + r() * 90, dark = r() < 0.6;
    for (const ox of [-S, 0, S]) for (const oy of [-S, 0, S]) {
      const gr = g.createRadialGradient(x + ox, y + oy, 0, x + ox, y + oy, rad);
      gr.addColorStop(0, dark ? 'rgba(0,0,0,0.20)' : 'rgba(190,170,140,0.05)');
      gr.addColorStop(1, 'rgba(0,0,0,0)');
      g.fillStyle = gr;
      g.fillRect(x + ox - rad, y + oy - rad, rad * 2, rad * 2);
    }
  }
  const img = g.getImageData(0, 0, S, S);
  const d = img.data;
  for (let i = 0; i < d.length; i += 4) {
    const n = r();
    if (n < 0.06) { const dark = n < 0.045; d[i] = d[i + 1] = d[i + 2] = dark ? 0 : 190; d[i + 3] = dark ? Math.max(d[i + 3], Math.floor(18 + r() * 30)) : Math.floor(5 + r() * 9); }
  }
  g.putImageData(img, 0, 0);
  return `url(${c.toDataURL('image/png')})`;
}

let installed = false;

/** Call once, before the first screen is shown. */
export function installTheme(): void {
  if (installed) return;
  installed = true;
  const root = document.documentElement;
  const set = (k: string, v: string) => root.style.setProperty(k, v);
  try {
    set('--fr-dim', frameImage('214,203,180', 0.5, 11));
    set('--fr-hot', frameImage('240,231,208', 0.95, 12));
    set('--fr-red', frameImage('201,40,48', 1, 13));
    set('--grain', grainTile());
  } catch (e) {
    console.warn('[ui] procedural theme textures failed; using plain borders', e);
  }
  // Pointer modality: the focus ring and the keyboard hints only appear after keyboard/gamepad use.
  const mode = (m: 'kbd' | 'ptr') => { if (root.dataset.input !== m) root.dataset.input = m; };
  root.dataset.input = 'ptr';
  window.addEventListener('keydown', (e) => { if (e.key.startsWith('Arrow') || e.key === 'Tab' || e.key === 'Enter') mode('kbd'); }, true);
  window.addEventListener('pointerdown', () => mode('ptr'), true);

  // Visual viewport: --vw/--vh follow the visible area (mobile URL bars, rotation) so fixed layouts never hide behind chrome.
  let raf = 0;
  const apply = () => {
    raf = 0;
    const vv = window.visualViewport;
    const w = Math.round(vv?.width ?? window.innerWidth), h = Math.round(vv?.height ?? window.innerHeight);
    set('--vw', `${w}px`); set('--vh', `${h}px`);
    root.dataset.orient = h >= w ? 'portrait' : 'landscape';
  };
  const queue = () => { if (!raf) raf = requestAnimationFrame(apply); };
  apply();
  window.addEventListener('resize', queue);
  window.addEventListener('orientationchange', () => setTimeout(queue, 120));
  window.visualViewport?.addEventListener('resize', queue);
}
