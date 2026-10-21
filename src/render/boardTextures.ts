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

/** Greyscale carved stone, tinted per instance by the board. */
export function makeStoneTexture(size = 256): CanvasTexture {
  const [c, g] = canvas(size);
  const r = rng(7);
  g.fillStyle = '#b9b6b2';
  g.fillRect(0, 0, size, size);
  // grain
  for (let i = 0; i < size * size * 0.35; i++) {
    const v = 150 + r() * 80;
    g.fillStyle = `rgba(${v},${v},${v},${0.10 + r() * 0.12})`;
    g.fillRect(r() * size, r() * size, 1 + r() * 2, 1 + r() * 2);
  }
  // veins
  g.lineWidth = 1;
  for (let i = 0; i < 6; i++) {
    g.strokeStyle = `rgba(40,40,40,${0.06 + r() * 0.1})`;
    g.beginPath();
    let x = r() * size, y = r() * size;
    g.moveTo(x, y);
    for (let k = 0; k < 7; k++) { x += (r() - 0.5) * size * 0.3; y += (r() - 0.5) * size * 0.3; g.lineTo(x, y); }
    g.stroke();
  }
  // carved bevel: lighter top-left, darker bottom-right
  const e = size * 0.05;
  g.lineWidth = e;
  g.strokeStyle = 'rgba(255,255,255,0.22)';
  g.beginPath(); g.moveTo(e / 2, size - e / 2); g.lineTo(e / 2, e / 2); g.lineTo(size - e / 2, e / 2); g.stroke();
  g.strokeStyle = 'rgba(0,0,0,0.32)';
  g.beginPath(); g.moveTo(size - e / 2, e / 2); g.lineTo(size - e / 2, size - e / 2); g.lineTo(e / 2, size - e / 2); g.stroke();
  const t = finish(c);
  t.wrapS = t.wrapT = RepeatWrapping;
  return t;
}

/**
 * Whole-board overlay (transparent): per-square inlay borders that run from forge bronze on the
 * Emberhold side to frost-silver on the Rime side, ember veins on one half, frost crystals on the other.
 * Row 0 of the canvas is rank 8 (Rime side).
 */
export function makeInlayTexture(size = 2048): CanvasTexture {
  const [c, g] = canvas(size);
  const r = rng(21);
  const s = size / 8;
  const bronze = [196, 135, 66], silver = [168, 214, 236];
  for (let row = 0; row < 8; row++) {
    const t = 1 - row / 7; // 1 on rank 1 (Emberhold) … 0 on rank 8 (Rime)
    const col = mix(silver, bronze, t);
    for (let f = 0; f < 8; f++) {
      const x = f * s, y = row * s, inset = s * 0.055;
      g.strokeStyle = rgb(col, 0.78);
      g.lineWidth = Math.max(2, s * 0.018);
      g.strokeRect(x + inset, y + inset, s - inset * 2, s - inset * 2);
      g.strokeStyle = rgb(col, 0.32);
      g.lineWidth = Math.max(1, s * 0.008);
      const in2 = inset * 2.1;
      g.strokeRect(x + in2, y + in2, s - in2 * 2, s - in2 * 2);
      // corner diamonds
      g.fillStyle = rgb(col, 0.85);
      for (const [cx, cy] of [[x + inset, y + inset], [x + s - inset, y + inset], [x + inset, y + s - inset], [x + s - inset, y + s - inset]]) {
        const d = s * 0.028;
        g.beginPath(); g.moveTo(cx, cy - d); g.lineTo(cx + d, cy); g.lineTo(cx, cy + d); g.lineTo(cx - d, cy); g.closePath(); g.fill();
      }
      if (t > 0.45) {
        // ember veins
        g.strokeStyle = `rgba(255,${110 + r() * 50},30,${0.12 + r() * 0.2 * t})`;
        g.lineWidth = Math.max(1, s * 0.01);
        for (let k = 0; k < 3; k++) {
          let px = x + r() * s, py = y + r() * s;
          g.beginPath(); g.moveTo(px, py);
          for (let m = 0; m < 4; m++) { px += (r() - 0.5) * s * 0.4; py += (r() - 0.5) * s * 0.4; g.lineTo(px, py); }
          g.stroke();
        }
      }
      if (t < 0.55) {
        // frost crystals creeping in from the square edges
        g.strokeStyle = `rgba(230,246,255,${0.2 + r() * 0.25 * (1 - t)})`;
        g.lineWidth = Math.max(1, s * 0.008);
        for (let k = 0; k < 4; k++) {
          const edge = Math.floor(r() * 4);
          let px = edge < 2 ? x + r() * s : edge === 2 ? x : x + s;
          let py = edge < 2 ? (edge === 0 ? y : y + s) : y + r() * s;
          const ang = Math.atan2(y + s / 2 - py, x + s / 2 - px) + (r() - 0.5);
          g.beginPath(); g.moveTo(px, py);
          for (let m = 0; m < 3; m++) {
            const len = s * (0.06 + r() * 0.08);
            px += Math.cos(ang + (r() - 0.5) * 0.9) * len; py += Math.sin(ang + (r() - 0.5) * 0.9) * len;
            g.lineTo(px, py);
          }
          g.stroke();
        }
      }
    }
  }
  return finish(c);
}

/** Frame top: carved dark stone, bronze inlay → frosted obsidian, with file/rank labels for both players. */
export function makeFrameTexture(size = 2048): CanvasTexture {
  const [c, g] = canvas(size);
  const r = rng(99);
  const S = size / FRAME_SIZE; // px per square unit
  const W = FRAME_SIZE;
  // base gradient: Emberhold (bottom, near White) → Rime (top)
  const grad = g.createLinearGradient(0, size, 0, 0);
  grad.addColorStop(0, '#2b2018');
  grad.addColorStop(0.45, '#221d1c');
  grad.addColorStop(0.55, '#1a2028');
  grad.addColorStop(1, '#101822');
  g.fillStyle = grad;
  g.fillRect(0, 0, size, size);
  for (let i = 0; i < size * size * 0.12; i++) {
    const v = 70 + r() * 120;
    g.fillStyle = `rgba(${v},${v},${v},${0.04 + r() * 0.07})`;
    g.fillRect(r() * size, r() * size, 1 + r() * 2, 1 + r() * 2);
  }
  const hole = 4.1, border = (W - 8) / 2;
  const frame = (inset: number, width: number, a: number) => {
    // line of constant colour per edge, bronze → silver by vertical position
    const lg = g.createLinearGradient(0, size, 0, 0);
    lg.addColorStop(0, `rgba(205,140,70,${a})`);
    lg.addColorStop(0.5, `rgba(190,170,150,${a * 0.8})`);
    lg.addColorStop(1, `rgba(170,215,240,${a})`);
    g.strokeStyle = lg;
    g.lineWidth = width * S;
    const o = inset * S;
    g.strokeRect(o, o, size - o * 2, size - o * 2);
  };
  frame(0.14, 0.05, 0.9);                    // outer inlay
  frame(W / 2 - hole - 0.1, 0.045, 0.95);    // inner inlay hugging the tiles
  frame(0.34, 0.015, 0.45);
  // corner medallions
  for (const [mx, my, warm] of [[-1, 1, 1], [1, 1, 1], [-1, -1, 0], [1, -1, 0]] as const) {
    const cx = size / 2 + mx * (W / 2 - border / 2) * S, cy = size / 2 + my * (W / 2 - border / 2) * S;
    const rg = g.createRadialGradient(cx, cy, 0, cx, cy, border * 0.42 * S);
    rg.addColorStop(0, warm ? 'rgba(255,170,70,0.95)' : 'rgba(190,240,255,0.95)');
    rg.addColorStop(0.55, warm ? 'rgba(160,100,45,0.9)' : 'rgba(120,170,200,0.9)');
    rg.addColorStop(1, 'rgba(0,0,0,0)');
    g.fillStyle = rg;
    g.beginPath(); g.arc(cx, cy, border * 0.42 * S, 0, Math.PI * 2); g.fill();
  }
  // labels
  const labelColor = (yUnit: number) => {
    const t = (yUnit + W / 2) / W; // 1 at the White edge … 0 at the Rime edge
    const col = mix([176, 218, 240], [226, 162, 84], t);
    return rgb(col, 0.96);
  };
  g.textAlign = 'center';
  g.textBaseline = 'middle';
  g.font = `bold ${Math.round(0.5 * S)}px Georgia, "Times New Roman", serif`;
  const edge = 8 / 2 + border / 2 + 0.02; // label centre line
  const px = (x: number) => (x + W / 2) * S;
  for (let i = 0; i < 8; i++) {
    const file = 'abcdefgh'[i];
    const rank = String(i + 1);
    const x = i - 3.5;
    const z = 3.5 - i; // rank i+1 sits at z
    // files: upright along the White edge, upside-down along the Rime edge (readable for Black)
    g.fillStyle = labelColor(edge);
    g.fillText(file, px(x), px(edge));
    g.save(); g.translate(px(x), px(-edge)); g.rotate(Math.PI); g.fillStyle = labelColor(-edge); g.fillText(file, 0, 0); g.restore();
    // ranks: upright on the a-file side, upside-down on the h-file side
    g.fillStyle = labelColor(z);
    g.fillText(rank, px(-edge), px(z));
    g.save(); g.translate(px(edge), px(z)); g.rotate(Math.PI); g.fillText(rank, 0, 0); g.restore();
  }
  return finish(c);
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
