// Renderer + scene bootstrap: sRGB output, AgX tone mapping, soft shadows, per-tier pixel ratio cap.
import { AgXToneMapping, PCFShadowMap, Scene, SRGBColorSpace, WebGLRenderer } from 'three';
import type { QualityTier as Tier } from '../contracts';

export const PIXEL_RATIO_CAP: Record<Tier, number> = { high: 2, medium: 1.5, low: 1 };

export interface RenderKit {
  renderer: WebGLRenderer;
  scene: Scene;
  canvas: HTMLCanvasElement;
  readonly width: number;
  readonly height: number;
  setSize(width: number, height: number): void;
  setPixelRatioCap(cap: number): void;
  /** Render scale 0.5–1 applied on top of the capped device pixel ratio. */
  setResolutionScale(scale: number): void;
}

export function createRenderKit(canvas: HTMLCanvasElement): RenderKit {
  const renderer = new WebGLRenderer({ canvas, antialias: true, powerPreference: 'high-performance', stencil: false });
  renderer.outputColorSpace = SRGBColorSpace;
  renderer.toneMapping = AgXToneMapping;
  renderer.toneMappingExposure = 0.9;
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = PCFShadowMap;
  renderer.setClearColor(0x05070b, 1);

  const scene = new Scene();
  let cap = PIXEL_RATIO_CAP.medium;
  let scale = 1;
  let w = canvas.clientWidth || window.innerWidth;
  let h = canvas.clientHeight || window.innerHeight;

  const apply = () => {
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, cap) * scale);
    renderer.setSize(w, h, false);
  };
  apply();

  return {
    renderer, scene, canvas,
    get width() { return w; },
    get height() { return h; },
    setSize(width, height) { w = Math.max(1, width); h = Math.max(1, height); apply(); },
    setPixelRatioCap(c) { cap = c; apply(); },
    setResolutionScale(v) { const n = Math.min(1, Math.max(0.5, v)); if (n !== scale) { scale = n; apply(); } },
  };
}

