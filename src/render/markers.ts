// Board hints with four switchable styles (Settings.highlightStyle), all driven by one tiny instanced-overlay system:
//   glow     refined glow disc on legal squares, disc + ring on captures, soft frame on the selection
//   brackets thin gothic corner brackets (crimson for captures)
//   tint     the whole tile subtly tinted (captures are hatched, so they never rely on hue alone)
//   runes    an animated faction glyph etched into the legal squares (ember sigil / frost snowflake)
// Five InstancedMesh layers (moves, captures, selected, last move, tints) each with ONE ShaderMaterial for the active style; pulses and
// shimmer run in the shader, so there is no per-frame CPU work or allocation. The colour-blind option swaps the palette to blue/orange
// and keeps the shapes distinct (diamond vs crossed ring, hatched capture tiles).
import {
  CanvasTexture, Color, DoubleSide, Group, InstancedBufferAttribute, InstancedMesh, Matrix4, NormalBlending, AdditiveBlending, PlaneGeometry,
  ShaderMaterial, SRGBColorSpace, Texture, type Blending, type Scene,
} from 'three';
import type { Faction, HighlightStyle, SettingsStore, Square } from '../contracts';
import { squareToWorld } from '../contracts';

export interface HintTarget { square: Square; capture: boolean }

export interface Markers {
  show(targets: HintTarget[]): void;
  clear(): void;
  setSelected(sq: Square | null): void;
  /** Pointer-over / drop-target highlight (a thin bright frame). `snap` = the square a drag would drop on. null clears. */
  setHover(sq: Square | null, snap?: boolean): void;
  setLastMove(from: Square | null, to?: Square | null): void;
  setColorBlind(on: boolean): void;
  /** Persistent coloured tile (check, lessons). `color === null` removes it. */
  setTint(sq: Square, color: number | null): void;
  setStyle(style: HighlightStyle): void;
  /** 0.2-1 */
  setIntensity(v: number): void;
  /** Faction whose glyph the 'runes' style etches (follows the selected piece when `getFaction` is provided). */
  setFaction(f: Faction): void;
  update(time: number): void;
  dispose(): void;
}

export interface MarkerOptions {
  settings?: SettingsStore;
  /** Faction of the piece standing on a square (for the rune glyph). */
  getFaction?: (sq: Square) => Faction | undefined;
}

// ------------------------------------------------------------------------------------------------ textures
function tex(draw: (g: CanvasRenderingContext2D, s: number) => void, size = 128): CanvasTexture {
  const c = document.createElement('canvas');
  c.width = c.height = size;
  const g = c.getContext('2d')!;
  g.lineCap = 'round'; g.lineJoin = 'round';
  draw(g, size);
  const t = new CanvasTexture(c);
  t.colorSpace = SRGBColorSpace;
  t.anisotropy = 4;
  return t;
}
const W = 'rgba(255,255,255,';

function bracketPath(g: CanvasRenderingContext2D, s: number, inset: number, arm: number) {
  const a = s * inset, b = s - a, l = s * arm;
  for (const [cx, cy, dx, dy] of [[a, a, 1, 1], [b, a, -1, 1], [a, b, 1, -1], [b, b, -1, -1]] as const) {
    g.moveTo(cx + dx * l, cy); g.lineTo(cx, cy); g.lineTo(cx, cy + dy * l);
  }
}

function makeTextures() {
  const disc = tex((g, s) => {
    const r = g.createRadialGradient(s / 2, s / 2, 0, s / 2, s / 2, s / 2);
    r.addColorStop(0, W + '1)'); r.addColorStop(0.28, W + '0.92)'); r.addColorStop(0.5, W + '0.4)'); r.addColorStop(1, W + '0)');
    g.fillStyle = r; g.fillRect(0, 0, s, s);
  });
  const captureGlow = tex((g, s) => {
    const r = g.createRadialGradient(s / 2, s / 2, s * 0.1, s / 2, s / 2, s / 2);
    r.addColorStop(0, W + '0.55)'); r.addColorStop(0.55, W + '0.2)'); r.addColorStop(1, W + '0)');
    g.fillStyle = r; g.fillRect(0, 0, s, s);
    g.strokeStyle = W + '1)'; g.lineWidth = s * 0.055;
    g.beginPath(); g.arc(s / 2, s / 2, s * 0.37, 0, Math.PI * 2); g.stroke();
    g.strokeStyle = W + '0.45)'; g.lineWidth = s * 0.13;
    g.beginPath(); g.arc(s / 2, s / 2, s * 0.37, 0, Math.PI * 2); g.stroke();
  });
  const diamond = tex((g, s) => {
    g.fillStyle = W + '0.95)';
    g.beginPath(); g.moveTo(s / 2, s * 0.2); g.lineTo(s * 0.8, s / 2); g.lineTo(s / 2, s * 0.8); g.lineTo(s * 0.2, s / 2); g.closePath(); g.fill();
    g.strokeStyle = W + '0.4)'; g.lineWidth = s * 0.05; g.stroke();
  });
  const crossRing = tex((g, s) => {
    g.strokeStyle = W + '1)'; g.lineWidth = s * 0.08;
    g.beginPath(); g.arc(s / 2, s / 2, s * 0.37, 0, Math.PI * 2); g.stroke();
    g.lineWidth = s * 0.075;
    g.beginPath(); g.moveTo(s * 0.34, s * 0.34); g.lineTo(s * 0.66, s * 0.66); g.moveTo(s * 0.66, s * 0.34); g.lineTo(s * 0.34, s * 0.66); g.stroke();
  });
  const frame = tex((g, s) => {
    g.strokeStyle = W + '1)'; g.lineWidth = s * 0.06;
    g.strokeRect(s * 0.07, s * 0.07, s * 0.86, s * 0.86);
    g.strokeStyle = W + '0.35)'; g.lineWidth = s * 0.14;
    g.strokeRect(s * 0.04, s * 0.04, s * 0.92, s * 0.92);
  });
  const soft = tex((g, s) => {
    const r = g.createRadialGradient(s / 2, s / 2, s * 0.1, s / 2, s / 2, s * 0.72);
    r.addColorStop(0, W + '0.7)'); r.addColorStop(0.75, W + '0.5)'); r.addColorStop(1, W + '0.2)');
    g.fillStyle = r; g.fillRect(s * 0.03, s * 0.03, s * 0.94, s * 0.94);
  });
  // brackets: thin L corners with a barb and a small diamond at each corner
  const brackets = tex((g, s) => {
    g.strokeStyle = W + '1)'; g.lineWidth = s * 0.035;
    g.beginPath(); bracketPath(g, s, 0.07, 0.24); g.stroke();
    g.lineWidth = s * 0.018; g.strokeStyle = W + '0.8)';
    g.beginPath(); bracketPath(g, s, 0.12, 0.13); g.stroke();
    g.fillStyle = W + '1)';
    for (const [cx, cy] of [[0.07, 0.07], [0.93, 0.07], [0.07, 0.93], [0.93, 0.93]]) {
      const d = s * 0.028; g.beginPath(); g.moveTo(cx * s, cy * s - d); g.lineTo(cx * s + d, cy * s); g.lineTo(cx * s, cy * s + d); g.lineTo(cx * s - d, cy * s); g.closePath(); g.fill();
    }
  }, 256);
  const bracketsCapture = tex((g, s) => {
    g.strokeStyle = W + '1)'; g.lineWidth = s * 0.05;
    g.beginPath(); bracketPath(g, s, 0.05, 0.3); g.stroke();
    g.lineWidth = s * 0.02;
    g.beginPath(); bracketPath(g, s, 0.11, 0.17); g.stroke();
    // small cross at the centre: captures read by shape as well as hue
    g.lineWidth = s * 0.035;
    g.beginPath(); g.moveTo(s * 0.42, s * 0.42); g.lineTo(s * 0.58, s * 0.58); g.moveTo(s * 0.58, s * 0.42); g.lineTo(s * 0.42, s * 0.58); g.stroke();
  }, 256);
  // tint squares
  const tint = tex((g, s) => {
    g.fillStyle = W + '1)'; g.fillRect(s * 0.035, s * 0.035, s * 0.93, s * 0.93);
    g.strokeStyle = W + '1)'; g.lineWidth = s * 0.02; g.strokeRect(s * 0.035, s * 0.035, s * 0.93, s * 0.93);
  });
  const tintHatch = tex((g, s) => {
    g.fillStyle = W + '0.55)'; g.fillRect(s * 0.035, s * 0.035, s * 0.93, s * 0.93);
    g.save(); g.beginPath(); g.rect(s * 0.035, s * 0.035, s * 0.93, s * 0.93); g.clip();
    g.strokeStyle = W + '1)'; g.lineWidth = s * 0.05;
    for (let i = -s; i < s * 2; i += s * 0.16) { g.beginPath(); g.moveTo(i, s); g.lineTo(i + s, 0); g.stroke(); }
    g.restore();
    g.strokeStyle = W + '1)'; g.lineWidth = s * 0.03; g.strokeRect(s * 0.035, s * 0.035, s * 0.93, s * 0.93);
  });
  // runes
  const runeEmber = tex((g, s) => {
    const c = s / 2;
    g.strokeStyle = W + '0.9)'; g.lineWidth = s * 0.022;
    g.beginPath(); g.arc(c, c, s * 0.4, 0, Math.PI * 2); g.stroke();
    g.lineWidth = s * 0.012; g.beginPath(); g.arc(c, c, s * 0.34, 0, Math.PI * 2); g.stroke();
    for (let i = 0; i < 8; i++) { const a = (i / 8) * Math.PI * 2; g.lineWidth = s * 0.02; g.beginPath(); g.moveTo(c + Math.cos(a) * s * 0.4, c + Math.sin(a) * s * 0.4); g.lineTo(c + Math.cos(a) * s * 0.455, c + Math.sin(a) * s * 0.455); g.stroke(); }
    // flame sigil: two licks with a core
    g.fillStyle = W + '1)';
    g.beginPath();
    g.moveTo(c, s * 0.2);
    g.bezierCurveTo(c + s * 0.17, s * 0.38, c + s * 0.2, s * 0.52, c + s * 0.11, s * 0.65);
    g.bezierCurveTo(c + s * 0.07, s * 0.7, c - s * 0.07, s * 0.7, c - s * 0.11, s * 0.65);
    g.bezierCurveTo(c - s * 0.2, s * 0.5, c - s * 0.1, s * 0.38, c, s * 0.2);
    g.closePath(); g.fill();
    g.globalCompositeOperation = 'destination-out';
    g.beginPath(); g.moveTo(c, s * 0.42); g.bezierCurveTo(c + s * 0.07, s * 0.52, c + s * 0.06, s * 0.6, c, s * 0.63); g.bezierCurveTo(c - s * 0.06, s * 0.6, c - s * 0.07, s * 0.52, c, s * 0.42); g.fill();
    g.globalCompositeOperation = 'source-over';
  }, 256);
  const runeFrost = tex((g, s) => {
    const c = s / 2;
    g.strokeStyle = W + '0.9)'; g.lineWidth = s * 0.018;
    g.beginPath();
    for (let i = 0; i <= 6; i++) { const a = (i / 6) * Math.PI * 2 + Math.PI / 6; const x = c + Math.cos(a) * s * 0.41, y = c + Math.sin(a) * s * 0.41; if (i) g.lineTo(x, y); else g.moveTo(x, y); }
    g.stroke();
    g.lineWidth = s * 0.03;
    for (let i = 0; i < 6; i++) {
      const a = (i / 6) * Math.PI * 2;
      const ex = c + Math.cos(a) * s * 0.34, ey = c + Math.sin(a) * s * 0.34;
      g.beginPath(); g.moveTo(c, c); g.lineTo(ex, ey); g.stroke();
      for (const k of [0.55, 0.8]) {
        const bx = c + Math.cos(a) * s * 0.34 * k, by = c + Math.sin(a) * s * 0.34 * k, bl = s * 0.09 * (1.2 - k * 0.5);
        for (const side of [-1, 1]) { g.beginPath(); g.moveTo(bx, by); g.lineTo(bx + Math.cos(a + side * 0.9) * bl, by + Math.sin(a + side * 0.9) * bl); g.stroke(); }
      }
    }
    g.fillStyle = W + '1)'; g.beginPath(); g.arc(c, c, s * 0.03, 0, Math.PI * 2); g.fill();
  }, 256);
  const runeCapture = (rune: CanvasTexture) => tex((g, s) => {
    g.strokeStyle = W + '1)'; g.lineWidth = s * 0.05;
    g.beginPath(); g.arc(s / 2, s / 2, s * 0.46, 0, Math.PI * 2); g.stroke();
    g.lineWidth = s * 0.02; g.beginPath(); g.arc(s / 2, s / 2, s * 0.4, 0, Math.PI * 2); g.stroke();
    g.globalAlpha = 0.95;
    g.drawImage(rune.image as CanvasImageSource, s * 0.15, s * 0.15, s * 0.7, s * 0.7);
  }, 256);
  return {
    disc, captureGlow, diamond, crossRing, frame, soft, brackets, bracketsCapture, tint, tintHatch, runeEmber, runeFrost,
    runeEmberCap: runeCapture(runeEmber), runeFrostCap: runeCapture(runeFrost),
  };
}

// ------------------------------------------------------------------------------------------------ materials
interface MatSpec { map: Texture; blending: Blending; opacity: number; pulse: number; speed: number; shimmer?: number; boost?: number }

function overlayMaterial(spec: MatSpec): ShaderMaterial {
  return new ShaderMaterial({
    uniforms: {
      uMap: { value: spec.map }, uTime: { value: 0 }, uOpacity: { value: spec.opacity }, uBase: { value: spec.opacity },
      uPulse: { value: spec.pulse }, uSpeed: { value: spec.speed }, uShimmer: { value: spec.shimmer ?? 0 }, uBoost: { value: spec.boost ?? 1 },
    },
    vertexShader: /* glsl */ `
      attribute float aPhase;
      varying vec2 vUv; varying vec3 vCol; varying float vPhase;
      void main() {
        vUv = uv; vCol = instanceColor; vPhase = aPhase;
        gl_Position = projectionMatrix * modelViewMatrix * instanceMatrix * vec4(position, 1.0);
      }`,
    fragmentShader: /* glsl */ `
      uniform sampler2D uMap; uniform float uTime, uOpacity, uPulse, uSpeed, uShimmer, uBoost;
      varying vec2 vUv; varying vec3 vCol; varying float vPhase;
      void main() {
        vec4 t = texture2D(uMap, vUv);
        float p = 1.0 + uPulse * sin(uTime * uSpeed + vPhase);
        float sh = 1.0 + uShimmer * (sin(uTime * 3.1 + vPhase + dot(vUv, vec2(9.0, 6.0))) * 0.5 - 0.15);
        gl_FragColor = vec4(vCol * uBoost * p, t.a * uOpacity * sh);
        #include <tonemapping_fragment>
        #include <colorspace_fragment>
      }`,
    transparent: true, depthWrite: false, blending: spec.blending, side: DoubleSide,
    polygonOffset: true, polygonOffsetFactor: -2, polygonOffsetUnits: -2,
  });
}

type Kind = 'moves' | 'captures' | 'selected' | 'last' | 'tints' | 'hover';
const KINDS: Kind[] = ['moves', 'captures', 'selected', 'last', 'tints', 'hover'];
const CAP: Record<Kind, number> = { moves: 40, captures: 24, selected: 1, last: 2, tints: 10, hover: 1 };
const Y: Record<Kind, number> = { moves: 0.013, captures: 0.013, selected: 0.012, last: 0.01, tints: 0.011, hover: 0.014 };
const ORDER: Record<Kind, number> = { moves: 5, captures: 5, selected: 4, last: 2, tints: 3, hover: 6 };

interface Layer { mesh: InstancedMesh; phase: InstancedBufferAttribute; n: number }

export function createMarkers(scene: Scene, opts: MarkerOptions = {}): Markers {
  const t = makeTextures();
  const group = new Group();
  group.name = 'markers';
  scene.add(group);
  const geo = new PlaneGeometry(1, 1).rotateX(-Math.PI / 2);

  const spec = (style: HighlightStyle, kind: Kind, blind: boolean, faction: Faction): MatSpec => {
    if (kind === 'hover') return { map: t.frame, blending: AdditiveBlending, opacity: 0.8, pulse: 0.08, speed: 5, boost: 1.1 };
    switch (style) {
      case 'glow':
        if (kind === 'moves') return { map: blind ? t.diamond : t.disc, blending: AdditiveBlending, opacity: 0.95, pulse: 0.12, speed: 3, boost: 1.5 };
        if (kind === 'captures') return { map: blind ? t.crossRing : t.captureGlow, blending: AdditiveBlending, opacity: 1, pulse: 0.15, speed: 3.4, boost: 1.6 };
        if (kind === 'selected') return { map: t.frame, blending: AdditiveBlending, opacity: 0.95, pulse: 0.25, speed: 4, boost: 1.6 };
        if (kind === 'last') return { map: t.soft, blending: AdditiveBlending, opacity: 0.4, pulse: 0, speed: 1, boost: 1 };
        return { map: t.soft, blending: AdditiveBlending, opacity: 0.85, pulse: 0.3, speed: 4.5, boost: 1.5 };
      case 'brackets':
        if (kind === 'moves') return { map: t.brackets, blending: AdditiveBlending, opacity: 1, pulse: 0.1, speed: 3, boost: 1.4 };
        if (kind === 'captures') return { map: t.bracketsCapture, blending: AdditiveBlending, opacity: 1, pulse: 0.16, speed: 4, boost: 1.5 };
        if (kind === 'selected') return { map: t.brackets, blending: AdditiveBlending, opacity: 1, pulse: 0.2, speed: 4, boost: 1.9 };
        if (kind === 'last') return { map: t.brackets, blending: AdditiveBlending, opacity: 0.55, pulse: 0, speed: 1, boost: 1 };
        return { map: t.bracketsCapture, blending: AdditiveBlending, opacity: 1, pulse: 0.3, speed: 4.5, boost: 1.6 };
      case 'tint':
        if (kind === 'moves') return { map: t.tint, blending: NormalBlending, opacity: 0.34, pulse: 0.08, speed: 3, boost: 1 };
        if (kind === 'captures') return { map: t.tintHatch, blending: NormalBlending, opacity: 0.5, pulse: 0.1, speed: 3.4, boost: 1 };
        if (kind === 'selected') return { map: t.tint, blending: NormalBlending, opacity: 0.55, pulse: 0.15, speed: 4, boost: 1 };
        if (kind === 'last') return { map: t.tint, blending: NormalBlending, opacity: 0.22, pulse: 0, speed: 1, boost: 1 };
        return { map: t.tint, blending: NormalBlending, opacity: 0.6, pulse: 0.2, speed: 4.5, boost: 1 };
      case 'runes': {
        const ember = faction === 'emberhold';
        if (kind === 'moves') return { map: blind ? t.diamond : ember ? t.runeEmber : t.runeFrost, blending: AdditiveBlending, opacity: 0.95, pulse: 0.18, speed: 2.4, shimmer: 0.5, boost: 1.6 };
        if (kind === 'captures') return { map: blind ? t.crossRing : ember ? t.runeEmberCap : t.runeFrostCap, blending: AdditiveBlending, opacity: 1, pulse: 0.2, speed: 3.2, shimmer: 0.4, boost: 1.7 };
        if (kind === 'selected') return { map: t.frame, blending: AdditiveBlending, opacity: 0.9, pulse: 0.25, speed: 4, boost: 1.5 };
        if (kind === 'last') return { map: ember ? t.runeEmber : t.runeFrost, blending: AdditiveBlending, opacity: 0.4, pulse: 0, speed: 1, boost: 1 };
        return { map: t.bracketsCapture, blending: AdditiveBlending, opacity: 1, pulse: 0.3, speed: 4.5, boost: 1.6 };
      }
    }
  };

  let style: HighlightStyle = opts.settings?.get().highlightStyle ?? 'glow';
  let intensity = opts.settings?.get().highlightIntensity ?? 0.8;
  let blind = !!opts.settings?.get().colorBlind;
  let faction: Faction = 'emberhold';

  const layers = {} as Record<Kind, Layer>;
  for (const k of KINDS) {
    const mesh = new InstancedMesh(geo, undefined as never, CAP[k]);
    mesh.count = 0;
    mesh.frustumCulled = false;
    mesh.renderOrder = ORDER[k];
    mesh.raycast = () => undefined;
    mesh.instanceColor = new InstancedBufferAttribute(new Float32Array(CAP[k] * 3), 3);
    const phase = new InstancedBufferAttribute(new Float32Array(CAP[k]), 1);
    mesh.geometry = geo.clone(); // per-layer geometry so the instanced phase attribute stays separate
    mesh.geometry.setAttribute('aPhase', phase);
    group.add(mesh);
    layers[k] = { mesh, phase, n: 0 };
  }

  const mats: Partial<Record<Kind, ShaderMaterial>> = {};
  const rebuildMaterials = () => {
    for (const k of KINDS) {
      mats[k]?.dispose();
      const m = overlayMaterial(spec(style, k, blind, faction));
      m.uniforms.uBase.value = m.uniforms.uOpacity.value;
      m.uniforms.uOpacity.value = m.uniforms.uBase.value * (0.35 + 0.65 * intensity) * (k === 'last' ? 1 : 1);
      mats[k] = m;
      layers[k].mesh.material = m;
    }
  };
  const setOpacity = () => { for (const k of KINDS) { const m = mats[k]!; m.uniforms.uOpacity.value = m.uniforms.uBase.value * (0.35 + 0.65 * intensity); } };

  // ---- palette
  const pal = () => blind
    ? { move: 0x4aa8ff, capture: 0xff9a1a, selected: 0xffffff, lastFrom: 0x8fa6c4, lastTo: 0xc2d4ea }
    : style === 'runes'
      ? (faction === 'emberhold'
        ? { move: 0xff8a30, capture: 0xff3322, selected: 0xffd9a0, lastFrom: 0xc27a3a, lastTo: 0xe8a860 }
        : { move: 0x8fe0ff, capture: 0xff4a60, selected: 0xe0f6ff, lastFrom: 0x6a98b8, lastTo: 0xa8d8f0 })
      : style === 'brackets'
        ? { move: 0xffd27a, capture: 0xd8222c, selected: 0xfff0b8, lastFrom: 0xb98d4a, lastTo: 0xe8c27a }
        : { move: 0xffd27a, capture: 0xff4a3a, selected: 0xfff0b0, lastFrom: 0xc79a52, lastTo: 0xe8c27a };

  const tmp = new Matrix4();
  const col = new Color();
  const put = (k: Kind, i: number, sq: Square, size: number, color: number, phase: number) => {
    const L = layers[k];
    const p = squareToWorld(sq);
    tmp.makeScale(size, 1, size).setPosition(p.x, Y[k], p.z);
    L.mesh.setMatrixAt(i, tmp);
    col.setHex(color);
    L.mesh.setColorAt(i, col);
    L.phase.setX(i, phase);
  };
  const flush = (k: Kind) => {
    const L = layers[k];
    L.mesh.count = L.n;
    L.mesh.instanceMatrix.needsUpdate = true;
    if (L.mesh.instanceColor) L.mesh.instanceColor.needsUpdate = true;
    L.phase.needsUpdate = true;
  };

  // ---- state (so a style / palette switch can rebuild the instances)
  let targets: HintTarget[] = [];
  let hover: Square | null = null, hoverSnap = false;
  let selected: Square | null = null;
  let lastFrom: Square | null = null, lastTo: Square | null = null;
  const tints = new Map<Square, number>();

  const sizes = () => {
    switch (style) {
      case 'glow': return { move: 0.62, capture: 0.98, sel: 1.02, last: 0.96, tint: 1.0 };
      case 'brackets': return { move: 0.9, capture: 0.97, sel: 1.0, last: 0.9, tint: 0.97 };
      case 'tint': return { move: 0.94, capture: 0.94, sel: 0.94, last: 0.94, tint: 0.94 };
      default: return { move: 0.74, capture: 0.97, sel: 1.0, last: 0.62, tint: 0.97 };
    }
  };

  const rebuildHover = (flushNow = true) => {
    layers.hover.n = 0;
    if (hover) put('hover', layers.hover.n++, hover, hoverSnap ? 1.0 : 0.94, hoverSnap ? 0xfff7e0 : blind ? 0xe6f0ff : 0xe9dcc0, 0);
    if (flushNow) flush('hover');
  };
  const rebuild = () => {
    const c = pal(), z = sizes();
    layers.moves.n = layers.captures.n = 0;
    for (const tg of targets) {
      if (tg.capture) put('captures', layers.captures.n++, tg.square, z.capture, c.capture, Math.random() * 6.28);
      else put('moves', layers.moves.n++, tg.square, z.move, c.move, Math.random() * 6.28);
    }
    layers.selected.n = 0;
    if (selected) put('selected', layers.selected.n++, selected, z.sel, c.selected, 0);
    layers.last.n = 0;
    if (lastFrom) put('last', layers.last.n++, lastFrom, z.last, c.lastFrom, 0);
    if (lastTo) put('last', layers.last.n++, lastTo, z.last, c.lastTo, 0);
    rebuildHover(false);
    layers.tints.n = 0;
    for (const [sq, color] of tints) { if (layers.tints.n < CAP.tints) put('tints', layers.tints.n++, sq, z.tint, color, Math.random() * 6.28); }
    for (const k of KINDS) flush(k);
  };

  rebuildMaterials();
  rebuild();

  const offs: Array<() => void> = [];
  if (opts.settings) {
    offs.push(opts.settings.subscribe((s, key) => {
      if (key === 'highlightStyle') api.setStyle(s.highlightStyle);
      else if (key === 'highlightIntensity') api.setIntensity(s.highlightIntensity);
      else if (key === 'colorBlind') api.setColorBlind(s.colorBlind);
    }));
  }

  const api: Markers = {
    show(list) { targets = list.slice(0, CAP.moves + CAP.captures); rebuild(); },
    clear() { if (targets.length) { targets = []; rebuild(); } },
    setSelected(sq) {
      selected = sq;
      const f = sq ? opts.getFaction?.(sq) : undefined;
      if (f && f !== faction) { faction = f; if (style === 'runes') rebuildMaterials(); }
      rebuild();
    },
    setHover(sq, snap = false) {
      if (sq === hover && snap === hoverSnap) return;
      hover = sq; hoverSnap = snap;
      rebuildHover();
    },
    setLastMove(from, to) { lastFrom = from; lastTo = to ?? null; rebuild(); },
    setColorBlind(on) { if (on === blind) return; blind = on; rebuildMaterials(); rebuild(); },
    setTint(sq, color) { if (color === null) tints.delete(sq); else tints.set(sq, color); rebuild(); },
    setStyle(next) { if (next === style) return; style = next; rebuildMaterials(); rebuild(); },
    setIntensity(v) { intensity = Math.min(1, Math.max(0.2, v)); setOpacity(); },
    setFaction(f) { if (f === faction) return; faction = f; if (style === 'runes') { rebuildMaterials(); rebuild(); } },
    update(time) { for (const k of KINDS) if (layers[k].n) mats[k]!.uniforms.uTime.value = time; },
    dispose() {
      offs.forEach((f) => f());
      scene.remove(group);
      for (const k of KINDS) { mats[k]?.dispose(); layers[k].mesh.geometry.dispose(); layers[k].mesh.dispose(); }
      Object.values(t).forEach((x) => x.dispose());
    },
  };
  return api;
}
