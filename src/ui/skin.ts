// Procedural material textures for the physical UI (wood, leather, brass, parchment, felt). Everything is drawn on
// small canvases at startup and exposed as CSS custom properties (data URLs): no image files, no fonts.
function rng(seed: number) {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function tile(size: number, draw: (g: CanvasRenderingContext2D, s: number) => void): string {
  const c = document.createElement('canvas');
  c.width = c.height = size;
  draw(c.getContext('2d')!, size);
  return `url(${c.toDataURL('image/png')})`;
}

/** Polished wood: base colour, long grain streaks, a few knots, faint polish sheen. Tiles seamlessly in x. */
function wood(base: [number, number, number], seed: number, size = 256): string {
  return tile(size, (g, s) => {
    const r = rng(seed);
    g.fillStyle = `rgb(${base})`;
    g.fillRect(0, 0, s, s);
    for (let i = 0; i < 260; i++) {
      const y = r() * s, len = s * (0.4 + r() * 0.9), x = r() * s;
      const d = r() < 0.6;
      g.strokeStyle = d ? `rgba(0,0,0,${0.05 + r() * 0.14})` : `rgba(255,220,170,${0.02 + r() * 0.06})`;
      g.lineWidth = 0.6 + r() * 1.6;
      g.beginPath(); g.moveTo(x, y);
      g.bezierCurveTo(x + len * 0.3, y + (r() - 0.5) * 5, x + len * 0.7, y + (r() - 0.5) * 5, x + len, y + (r() - 0.5) * 3);
      g.stroke();
      if (x + len > s) { g.beginPath(); g.moveTo(x - s, y); g.bezierCurveTo(x - s + len * 0.3, y + 1, x - s + len * 0.7, y - 1, x - s + len, y); g.stroke(); }
    }
    for (let k = 0; k < 2; k++) {
      const cx = r() * s, cy = r() * s;
      for (let ring = 1; ring < 6; ring++) {
        g.strokeStyle = `rgba(0,0,0,${0.08 - ring * 0.01})`;
        g.lineWidth = 1;
        g.beginPath(); g.ellipse(cx, cy, ring * 5, ring * 2, 0, 0, Math.PI * 2); g.stroke();
      }
    }
    const sheen = g.createLinearGradient(0, 0, 0, s);
    sheen.addColorStop(0, 'rgba(255,230,190,0.08)'); sheen.addColorStop(0.5, 'rgba(0,0,0,0)'); sheen.addColorStop(1, 'rgba(0,0,0,0.12)');
    g.fillStyle = sheen; g.fillRect(0, 0, s, s);
  });
}

function leather(base: [number, number, number], seed: number, size = 128): string {
  return tile(size, (g, s) => {
    const r = rng(seed);
    g.fillStyle = `rgb(${base})`;
    g.fillRect(0, 0, s, s);
    for (let i = 0; i < s * s * 0.5; i++) {
      const v = r() < 0.5 ? 0 : 255;
      g.fillStyle = `rgba(${v},${v},${v},${0.015 + r() * 0.035})`;
      g.fillRect(r() * s, r() * s, 1 + r() * 2, 1 + r() * 2);
    }
    for (let i = 0; i < 40; i++) { // cracked grain
      g.strokeStyle = `rgba(0,0,0,${0.08 + r() * 0.1})`;
      g.lineWidth = 0.7;
      let x = r() * s, y = r() * s;
      g.beginPath(); g.moveTo(x, y);
      for (let k = 0; k < 3; k++) { x += (r() - 0.5) * 14; y += (r() - 0.5) * 14; g.lineTo(x, y); }
      g.stroke();
    }
  });
}

/** Brushed brass: warm gradient plus fine horizontal brushing. */
function brass(size = 128): string {
  return tile(size, (g, s) => {
    const r = rng(77);
    const lg = g.createLinearGradient(0, 0, s, s);
    lg.addColorStop(0, '#8a6a30'); lg.addColorStop(0.35, '#d8b565'); lg.addColorStop(0.55, '#a98241'); lg.addColorStop(1, '#6e5122');
    g.fillStyle = lg; g.fillRect(0, 0, s, s);
    for (let i = 0; i < 400; i++) {
      const y = r() * s;
      g.strokeStyle = r() < 0.5 ? `rgba(255,240,190,${0.05 + r() * 0.08})` : `rgba(40,20,0,${0.05 + r() * 0.08})`;
      g.lineWidth = 0.6;
      g.beginPath(); g.moveTo(0, y); g.lineTo(s, y + (r() - 0.5) * 2); g.stroke();
    }
  });
}

function paper(size = 256): string {
  return tile(size, (g, s) => {
    const r = rng(33);
    g.fillStyle = '#d9c9a0'; g.fillRect(0, 0, s, s);
    for (let i = 0; i < 70; i++) {
      const x = r() * s, y = r() * s, rad = s * (0.05 + r() * 0.2);
      const rg = g.createRadialGradient(x, y, 0, x, y, rad);
      const dark = r() < 0.6;
      rg.addColorStop(0, dark ? `rgba(120,90,40,${0.04 + r() * 0.05})` : 'rgba(255,245,215,0.08)');
      rg.addColorStop(1, 'rgba(0,0,0,0)');
      g.fillStyle = rg; g.fillRect(x - rad, y - rad, rad * 2, rad * 2);
    }
    for (let i = 0; i < s * s * 0.15; i++) {
      g.fillStyle = `rgba(70,45,10,${0.02 + r() * 0.05})`;
      g.fillRect(r() * s, r() * s, 1, 1);
    }
  });
}

function felt(base: [number, number, number], size = 96): string {
  return tile(size, (g, s) => {
    const r = rng(5);
    g.fillStyle = `rgb(${base})`; g.fillRect(0, 0, s, s);
    for (let i = 0; i < s * s * 0.9; i++) {
      const v = r() < 0.5 ? 0 : 255;
      g.fillStyle = `rgba(${v},${v},${v},${0.03 + r() * 0.06})`;
      g.fillRect(r() * s, r() * s, 1, 1);
    }
  });
}

/** Leather cover colours for the spines on the bookshelf. */
export const BOOK_COLORS: Array<[number, number, number]> = [[96, 26, 28], [30, 62, 44], [28, 44, 78], [122, 82, 32], [52, 30, 24], [66, 38, 70]];

let installed = false;
export function installSkin(): void {
  if (installed) return;
  installed = true;
  const root = document.documentElement.style;
  root.setProperty('--tex-wood-dark', wood([44, 27, 16], 1));
  root.setProperty('--tex-wood-mid', wood([84, 52, 28], 2));
  root.setProperty('--tex-wood-light', wood([120, 78, 42], 3));
  root.setProperty('--tex-brass', brass());
  root.setProperty('--tex-paper', paper());
  root.setProperty('--tex-felt-green', felt([28, 70, 44]));
  root.setProperty('--tex-felt-red', felt([96, 28, 30]));
  BOOK_COLORS.forEach((c, i) => root.setProperty(`--tex-book-${i}`, leather(c, 100 + i)));
}
