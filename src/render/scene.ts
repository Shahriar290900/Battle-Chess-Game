// Renderer + scene bootstrap: sRGB output, AgX tone mapping (gentle shoulder, no crushed shadows or clipped highlights), PCF shadows that are refreshed on demand,
// a per-tier pixel-ratio cap and a runtime resolution scale. Sizing follows window.visualViewport (mobile URL bars), orientation
// changes and safe areas; the canvas always fills the visual viewport.
import { AgXToneMapping, PCFShadowMap, Scene, SRGBColorSpace, WebGLRenderer } from 'three';
import type { QualityTier as Tier } from '../contracts';

/** Cap on devicePixelRatio per tier. iGPUs and phones render at 1x (phones at most 1.25x on Medium/High, never above). */
export const PIXEL_RATIO_CAP: Record<Tier, number> = { high: 1.75, medium: 1.25, low: 1 };

/** Baseline exposure of the Standard contrast preset (render/look.ts scales it for Soft / Vivid). */
export const EXPOSURE = 1.0;

export interface RenderKit {
  renderer: WebGLRenderer;
  scene: Scene;
  canvas: HTMLCanvasElement;
  readonly width: number;
  readonly height: number;
  /** Effective pixel ratio currently applied (capped dpr x resolution scale). */
  readonly pixelRatio: number;
  setSize(width: number, height: number): void;
  setPixelRatioCap(cap: number): void;
  /** Render scale 0.5-1 applied on top of the capped device pixel ratio. */
  setResolutionScale(scale: number): void;
  /** Called after every size / pixel-ratio change (post-processing resizes its buffers here). */
  onResize: ((w: number, h: number) => void) | null;
}

export function createRenderKit(canvas: HTMLCanvasElement, opts: { antialias?: boolean } = {}): RenderKit {
  const renderer = new WebGLRenderer({
    canvas, antialias: !!opts.antialias, powerPreference: 'high-performance', stencil: false, alpha: false,
    preserveDrawingBuffer: false, failIfMajorPerformanceCaveat: false,
  });
  renderer.outputColorSpace = SRGBColorSpace;
  renderer.toneMapping = AgXToneMapping;
  renderer.toneMappingExposure = EXPOSURE;
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = PCFShadowMap;
  renderer.setClearColor(0x26283a, 1);

  const scene = new Scene();
  let cap = PIXEL_RATIO_CAP.medium;
  let scale = 1;
  let w = canvas.clientWidth || window.innerWidth;
  let h = canvas.clientHeight || window.innerHeight;
  let ratio = 1;

  const kit: RenderKit = {
    renderer, scene, canvas,
    get width() { return w; },
    get height() { return h; },
    get pixelRatio() { return ratio; },
    onResize: null,
    setSize(width, height) { w = Math.max(1, Math.round(width)); h = Math.max(1, Math.round(height)); apply(); },
    setPixelRatioCap(c) { if (c !== cap) { cap = c; apply(); } },
    setResolutionScale(v) { const n = Math.min(1, Math.max(0.5, v)); if (Math.abs(n - scale) > 1e-3) { scale = n; apply(); } },
  };
  function apply() {
    const r = Math.min(window.devicePixelRatio || 1, cap) * scale;
    ratio = r;
    renderer.setPixelRatio(r);
    renderer.setSize(w, h, false);
    kit.onResize?.(w, h);
  }
  apply();
  return kit;
}

/** CSS-pixel size of the visible area: visualViewport tracks the mobile URL bar and pinch state, innerWidth/Height does not. */
export function viewportSize(): { w: number; h: number } {
  const vv = window.visualViewport;
  const w = Math.round(vv?.width ?? window.innerWidth);
  const h = Math.round(vv?.height ?? window.innerHeight);
  return { w: Math.max(1, w), h: Math.max(1, h) };
}

/**
 * Keep the canvas sized to the visible viewport. Debounced to one call per frame; also reacts to orientation changes (some WebViews
 * report the new size a few hundred ms late, so a second pass runs after the change settles).
 */
export function watchViewport(onChange: (w: number, h: number) => void): () => void {
  let raf = 0, last = '';
  const run = () => {
    raf = 0;
    const { w, h } = viewportSize();
    const key = `${w}x${h}`;
    if (key === last) return;
    last = key;
    onChange(w, h);
  };
  const schedule = () => { if (!raf) raf = requestAnimationFrame(run); };
  const late = () => { schedule(); setTimeout(schedule, 150); setTimeout(schedule, 450); };
  window.addEventListener('resize', schedule);
  window.addEventListener('orientationchange', late);
  window.visualViewport?.addEventListener('resize', schedule);
  screen.orientation?.addEventListener?.('change', late);
  run();
  return () => {
    window.removeEventListener('resize', schedule);
    window.removeEventListener('orientationchange', late);
    window.visualViewport?.removeEventListener('resize', schedule);
    screen.orientation?.removeEventListener?.('change', late);
    if (raf) cancelAnimationFrame(raf);
  };
}
