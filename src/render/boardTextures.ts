// Procedural canvas textures for the board. Everything is generated in code: no image assets.
import { CanvasTexture, RepeatWrapping, SRGBColorSpace } from 'three';

export const FRAME_SIZE = 10.6; // outer edge of the frame, in squares

function canvas(size: number): [HTMLCanvasElement, CanvasRenderingContext2D] {
  const c = document.createElement('canvas');
  c.width = c.height = size;
  return [c, c.getContext('2d')!];
}

/** Deterministic PRNG so the board looks identical on every run. */
function rng(seed: number) {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function finish(c: HTMLCanvasElement, srgb = true): CanvasTexture {
  const t = new CanvasTexture(c);
  if (srgb) t.colorSpace = SRGBColorSpace;
  t.anisotropy = 8;
  t.needsUpdate = true;
  return t;
}

const mix = (a: number[], b: number[], t: number) => a.map((v, i) => Math.round(v + (b[i] - v) * t));
const rgb = (c: number[], a = 1) => `rgba(${c[0]},${c[1]},${c[2]},${a})`;

/**
 * One continuous 8x8-square slab of marble/basalt: smooth, low-contrast veins and fine grain, greyscale so the
 * board can tint it per square (bone marble / slate). Sampled by world position, so veins run across tile edges.
 * Canvas row 0 is the Rime side (-z).
 */
export function makeMarbleTexture(size = 2048): CanvasTexture {
  const [c, g] = canvas(size);
  const r = rng(11);
  g.fillStyle = '#c9c7c3';
  g.fillRect(0, 0, size, size);
  // soft cloudy variation
  for (let i = 0; i < 90; i++) {
    const x = r() * size, y = r() * size, rad = size * (0.04 + r() * 0.12);
    const rg = g.createRadialGradient(x, y, 0, x, y, rad);
    const v = r() < 0.5 ? 255 : 120;
    rg.addColorStop(0, `rgba(${v},${v},${v},${0.05 + r() * 0.05})`);
    rg.addColorStop(1, `rgba(${v},${v},${v},0)`);
    g.fillStyle = rg;
    g.fillRect(x - rad, y - rad, rad * 2, rad * 2);
  }
  // veins: long smooth curves, wide faint underlay + thin core (never coloured)
  g.lineCap = 'round';
  g.lineJoin = 'round';
  for (let i = 0; i < 26; i++) {
    let x = r() * size, y = r() * size;
    let ang = r() * Math.PI * 2;
    const pts: Array<[number, number]> = [[x, y]];
    for (let k = 0; k < 14; k++) {
      ang += (r() - 0.5) * 0.9;
      const step = size * (0.05 + r() * 0.05);
      x += Math.cos(ang) * step; y += Math.sin(ang) * step;
      pts.push([x, y]);
    }
    const trace = (w: number, a: number, shade: number) => {
      g.strokeStyle = `rgba(${shade},${shade},${shade},${a})`;
      g.lineWidth = w;
      g.beginPath();
      g.moveTo(pts[0][0], pts[0][1]);
      for (let k = 1; k < pts.length - 1; k++) {
        const mx = (pts[k][0] + pts[k + 1][0]) / 2, my = (pts[k][1] + pts[k + 1][1]) / 2;
        g.quadraticCurveTo(pts[k][0], pts[k][1], mx, my);
      }
      g.stroke();
    };
    trace(size * 0.012, 0.06, 70);
    trace(size * 0.005, 0.12, 80);
    trace(Math.max(1, size * 0.0016), 0.3, 90);
  }
  // fine grain
  for (let i = 0; i < size * size * 0.04; i++) {
    const v = r() < 0.5 ? 40 : 235;
    g.fillStyle = `rgba(${v},${v},${v},${0.03 + r() * 0.05})`;
    g.fillRect(r() * size, r() * size, 1, 1);
  }
  const t = finish(c);
  t.wrapS = t.wrapT = RepeatWrapping;
  return t;
}

/**
 * Whole-board overlay (transparent, row 0 = rank 8): thin bronze rules engraved inside the Emberhold-side squares
 * that fade out toward the middle, and soft rime frost creeping in from the Rime-side edges. No random colour.
 */
export function makeInlayTexture(size = 2048): CanvasTexture {
  const [c, g] = canvas(size);
  const r = rng(21);
  const s = size / 8;
  for (let row = 0; row < 8; row++) {
    const rankT = row / 7; // row 0 is rank 8 (canvas top) → 1 on rank 1 (row 7), 0 on rank 8
    const bronze = Math.max(0, (rankT - 0.5) / 0.5); // strong on ranks 1-2, gone by rank 4
    const frost = Math.max(0, (0.5 - rankT) / 0.5); // strong on ranks 7-8
    for (let f = 0; f < 8; f++) {
      const x = f * s, y = row * s;
      if (bronze > 0.02) {
        const inset = s * 0.07;
        g.strokeStyle = `rgba(205,150,80,${0.5 * bronze})`;
        g.lineWidth = Math.max(1.5, s * 0.012);
        g.strokeRect(x + inset, y + inset, s - inset * 2, s - inset * 2);
        g.fillStyle = `rgba(215,160,90,${0.6 * bronze})`;
        for (const [cx, cy] of [[x + inset, y + inset], [x + s - inset, y + inset], [x + inset, y + s - inset], [x + s - inset, y + s - inset]]) {
          const d = s * 0.018;
          g.beginPath(); g.moveTo(cx, cy - d); g.lineTo(cx + d, cy); g.lineTo(cx, cy + d); g.lineTo(cx - d, cy); g.closePath(); g.fill();
        }
      }
      if (frost > 0.02) {
        // soft rime along the square's edges and corners
        for (const [cx, cy] of [[x, y], [x + s, y], [x, y + s], [x + s, y + s]]) {
          const rad = s * (0.28 + r() * 0.2);
          const rg = g.createRadialGradient(cx, cy, 0, cx, cy, rad);
          rg.addColorStop(0, `rgba(225,242,252,${0.3 * frost})`);
          rg.addColorStop(1, 'rgba(225,242,252,0)');
          g.fillStyle = rg;
          g.fillRect(cx - rad, cy - rad, rad * 2, rad * 2);
        }
        // a few fine fern-like crystals growing in from the corners
        g.strokeStyle = `rgba(235,247,255,${0.32 * frost})`;
        g.lineWidth = Math.max(1, s * 0.006);
        for (const [cx, cy, dx, dy] of [[x, y, 1, 1], [x + s, y, -1, 1], [x, y + s, 1, -1], [x + s, y + s, -1, -1]] as const) {
          if (r() < 0.45) continue;
          const base = Math.atan2(dy, dx) + (r() - 0.5) * 0.4;
          const len = s * (0.16 + r() * 0.12);
          const branch = (px: number, py: number, a: number, l: number, depth: number) => {
            const ex = px + Math.cos(a) * l, ey = py + Math.sin(a) * l;
            g.beginPath(); g.moveTo(px, py); g.lineTo(ex, ey); g.stroke();
            if (depth > 0) { branch(ex, ey, a + 0.6, l * 0.55, depth - 1); branch(ex, ey, a - 0.6, l * 0.55, depth - 1); }
          };
          branch(cx, cy, base, len, 2);
        }
      }
    }
  }
  return finish(c);
}

/** Metal grid under the tiles: bronze on the Emberhold side to frosted silver on the Rime side (row 0 = far). */
export function makeSlabTexture(size = 256): CanvasTexture {
  const [c, g] = canvas(size);
  const lg = g.createLinearGradient(0, size, 0, 0);
  lg.addColorStop(0, '#a8763a');
  lg.addColorStop(0.45, '#8f7650');
  lg.addColorStop(0.6, '#8794a0');
  lg.addColorStop(1, '#aab9c4');
  g.fillStyle = lg;
  g.fillRect(0, 0, size, size);
  return finish(c);
}

/** Dark carved walnut-and-bronze frame top with file/rank labels readable from both seats. */
export function makeFrameTexture(size = 2048): CanvasTexture {
  const [c, g] = canvas(size);
  const r = rng(99);
  const S = size / FRAME_SIZE;
  const W = FRAME_SIZE;
  const border = (W - 8) / 2;
  g.fillStyle = '#4b3220';
  g.fillRect(0, 0, size, size);
  // wood grain follows each band: horizontal streaks on the top/bottom bands, vertical on the sides
  const streak = (x0: number, y0: number, x1: number, y1: number, horizontal: boolean) => {
    for (let i = 0; i < 700; i++) {
      const len = (60 + r() * 360) * (size / 2048);
      let x = x0 + r() * (x1 - x0), y = y0 + r() * (y1 - y0);
      const dark = r() < 0.55;
      g.strokeStyle = dark ? `rgba(24,12,5,${0.16 + r() * 0.22})` : `rgba(150,104,62,${0.12 + r() * 0.18})`;
      g.lineWidth = 0.6 + r() * 1.8;
      g.beginPath(); g.moveTo(x, y);
      const wob = (r() - 0.5) * 6;
      if (horizontal) g.bezierCurveTo(x + len * 0.3, y + wob, x + len * 0.7, y - wob, x + len, y + wob * 0.3);
      else g.bezierCurveTo(x + wob, y + len * 0.3, x - wob, y + len * 0.7, x + wob * 0.3, y + len);
      g.stroke();
    }
  };
  const bw = border * S;
  streak(0, 0, size, bw, true);
  streak(0, size - bw, size, size, true);
  streak(0, 0, bw, size, false);
  streak(size - bw, 0, size, size, false);
  // cold tint toward the Rime edge, warm toward Emberhold
  const tint = g.createLinearGradient(0, size, 0, 0);
  tint.addColorStop(0, 'rgba(140,80,30,0.10)');
  tint.addColorStop(0.5, 'rgba(0,0,0,0)');
  tint.addColorStop(1, 'rgba(100,150,190,0.12)');
  g.fillStyle = tint;
  g.fillRect(0, 0, size, size);
  // bronze inlay rules (outer, and hugging the tiles)
  const rule = (inset: number, width: number, a: number) => {
    const lg = g.createLinearGradient(0, size, 0, 0);
    lg.addColorStop(0, `rgba(196,138,70,${a})`);
    lg.addColorStop(0.5, `rgba(170,150,120,${a * 0.9})`);
    lg.addColorStop(1, `rgba(170,200,220,${a})`);
    g.strokeStyle = lg;
    g.lineWidth = width * S;
    const o = inset * S;
    g.strokeRect(o, o, size - o * 2, size - o * 2);
  };
  rule(0.16, 0.04, 0.9);
  rule(W / 2 - 4.1 - 0.02, 0.035, 0.95);
  rule(0.36, 0.012, 0.4);
  // corner studs
  for (const mx of [-1, 1]) for (const my of [-1, 1]) {
    const cx = size / 2 + mx * (W / 2 - border / 2) * S, cy = size / 2 + my * (W / 2 - border / 2) * S;
    const warm = my > 0;
    const rg = g.createRadialGradient(cx - 6, cy - 6, 2, cx, cy, border * 0.3 * S);
    rg.addColorStop(0, warm ? '#e0b070' : '#d6e6ee');
    rg.addColorStop(1, warm ? '#6e4a22' : '#5f7686');
    g.fillStyle = rg;
    g.beginPath(); g.arc(cx, cy, border * 0.3 * S, 0, Math.PI * 2); g.fill();
    g.strokeStyle = 'rgba(0,0,0,0.5)'; g.lineWidth = 2; g.stroke();
  }
  // labels
  const labelColor = (yUnit: number) => {
    const t = (yUnit + W / 2) / W; // 1 at the White edge, 0 at the Rime edge
    return rgb(mix([176, 208, 226], [214, 160, 92], t), 0.95);
  };
  g.textAlign = 'center';
  g.textBaseline = 'middle';
  g.font = `bold ${Math.round(0.46 * S)}px Georgia, "Times New Roman", serif`;
  const edge = 4 + border / 2 + 0.02;
  const px = (x: number) => (x + W / 2) * S;
  for (let i = 0; i < 8; i++) {
    const file = 'abcdefgh'[i];
    const rank = String(i + 1);
    const x = i - 3.5;
    const z = 3.5 - i;
    g.fillStyle = labelColor(edge);
    g.fillText(file, px(x), px(edge));
    g.save(); g.translate(px(x), px(-edge)); g.rotate(Math.PI); g.fillStyle = labelColor(-edge); g.fillText(file, 0, 0); g.restore();
    g.fillStyle = labelColor(z);
    g.fillText(rank, px(-edge), px(z));
    g.save(); g.translate(px(edge), px(z)); g.rotate(Math.PI); g.fillText(rank, 0, 0); g.restore();
  }
  return finish(c);
}

/** Flagstone hall floor (tiles on repeat): large slabs, dark mortar, mottled. */
export function makeFloorTexture(size = 1024): CanvasTexture {
  const [c, g] = canvas(size);
  const r = rng(5);
  g.fillStyle = '#4e4a46';
  g.fillRect(0, 0, size, size);
  const n = 6, cell = size / n;
  for (let y = 0; y < n; y++) for (let x = 0; x < n; x++) {
    const v = 58 + Math.floor(r() * 26);
    g.fillStyle = `rgb(${v + 4},${v + 2},${v})`;
    g.fillRect(x * cell + 3, y * cell + 3, cell - 6, cell - 6);
    for (let k = 0; k < 6; k++) {
      const cx = x * cell + r() * cell, cy = y * cell + r() * cell, rad = cell * (0.15 + r() * 0.3);
      const rg = g.createRadialGradient(cx, cy, 0, cx, cy, rad);
      const l = r() < 0.5 ? 255 : 0;
      rg.addColorStop(0, `rgba(${l},${l},${l},0.06)`);
      rg.addColorStop(1, `rgba(${l},${l},${l},0)`);
      g.fillStyle = rg; g.fillRect(cx - rad, cy - rad, rad * 2, rad * 2);
    }
  }
  g.strokeStyle = 'rgba(0,0,0,0.6)';
  g.lineWidth = 5;
  for (let i = 0; i <= n; i++) {
    g.beginPath(); g.moveTo(i * cell, 0); g.lineTo(i * cell, size); g.stroke();
    g.beginPath(); g.moveTo(0, i * cell); g.lineTo(size, i * cell); g.stroke();
  }
  for (let i = 0; i < size * size * 0.02; i++) {
    const l = r() < 0.5 ? 0 : 255;
    g.fillStyle = `rgba(${l},${l},${l},${0.02 + r() * 0.04})`;
    g.fillRect(r() * size, r() * size, 1, 1);
  }
  const t = finish(c);
  t.wrapS = t.wrapT = RepeatWrapping;
  return t;
}

/** Soft dark blob for the contact shadow under each piece. */
export function makeContactShadowTexture(size = 64): CanvasTexture {
  const [c, g] = canvas(size);
  const rg = g.createRadialGradient(size / 2, size / 2, 0, size / 2, size / 2, size / 2);
  rg.addColorStop(0, 'rgba(0,0,0,0.85)');
  rg.addColorStop(0.45, 'rgba(0,0,0,0.5)');
  rg.addColorStop(1, 'rgba(0,0,0,0)');
  g.fillStyle = rg;
  g.fillRect(0, 0, size, size);
  return finish(c, false);
}

/** Soft radial glow used by the tile tint overlay and legal-move discs. */
export function makeGlowTexture(size = 128): CanvasTexture {
  const [c, g] = canvas(size);
  const rg = g.createRadialGradient(size / 2, size / 2, 0, size / 2, size / 2, size / 2);
  rg.addColorStop(0, 'rgba(255,255,255,1)');
  rg.addColorStop(0.45, 'rgba(255,255,255,0.55)');
  rg.addColorStop(1, 'rgba(255,255,255,0)');
  g.fillStyle = rg;
  g.fillRect(0, 0, size, size);
  return finish(c);
}

/** Square tile glow: bright inner rectangle with a soft edge. */
export function makeTileGlowTexture(size = 128): CanvasTexture {
  const [c, g] = canvas(size);
  const rg = g.createRadialGradient(size / 2, size / 2, size * 0.05, size / 2, size / 2, size * 0.72);
  rg.addColorStop(0, 'rgba(255,255,255,0.85)');
  rg.addColorStop(0.7, 'rgba(255,255,255,0.6)');
  rg.addColorStop(1, 'rgba(255,255,255,0.25)');
  g.fillStyle = rg;
  g.fillRect(0, 0, size, size);
  return finish(c);
}
