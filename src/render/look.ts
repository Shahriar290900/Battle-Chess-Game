// Readability look (Settings.contrast): exposure, saturation, rim strength and the piece silhouette edge, applied live.
//
//   soft      lower exposure and saturation, gentle rim: the calmest picture
//   standard  the tuned default (AgX, key:fill about 2:1, mid-contrast squares)
//   vivid     brighter, richer colour and a stronger rim/outline
//
// Exposure goes through renderer.toneMappingExposure (it reaches the composer's tone-mapping pass too), saturation through the
// post pipeline's colour-grade effect (a CSS filter on the canvas when the pipeline renders straight to the canvas on Low),
// the cool rim through Lighting.setRimStrength and the silhouette edge through the shared uniform of pieceLook.
import type { ContrastMode, QualityTier } from '../contracts';
import type { Lighting } from './lighting';
import type { PostPipelineImpl } from './post';
import { setEdgeStrength } from './pieceLook';
import { EXPOSURE } from './scene';
import type { WebGLRenderer } from 'three';

export interface LookPreset { exposure: number; saturation: number; rim: number; edge: number }

export const LOOK_PRESETS: Record<ContrastMode, LookPreset> = {
  soft: { exposure: 0.92, saturation: 0.9, rim: 0.7, edge: 0.55 },
  standard: { exposure: EXPOSURE, saturation: 1, rim: 1, edge: 1 },
  vivid: { exposure: 1.1, saturation: 1.2, rim: 1.35, edge: 1.35 },
};

export interface Look {
  readonly mode: ContrastMode;
  set(mode: ContrastMode): void;
  /** Re-apply after the pipeline was rebuilt (graphics / tier changes). */
  refresh(): void;
}

export function createLook(d: { renderer: WebGLRenderer; lighting: Lighting; post: PostPipelineImpl; canvas: HTMLElement; tier: () => QualityTier; initial?: ContrastMode }): Look {
  let mode: ContrastMode = d.initial ?? 'standard';
  const apply = () => {
    const p = LOOK_PRESETS[mode];
    d.renderer.toneMappingExposure = p.exposure;
    d.lighting.setRimStrength(p.rim);
    // The outline is a High / Medium feature; Low renders without it (it needs the extra fragment work and bloom to sit well).
    setEdgeStrength(d.tier() === 'low' ? 0 : p.edge);
    const handled = d.post.setSaturation(p.saturation);
    d.canvas.style.filter = handled || Math.abs(p.saturation - 1) < 0.01 ? '' : `saturate(${p.saturation})`;
  };
  apply();
  return {
    get mode() { return mode; },
    set(next) { mode = next; apply(); },
    refresh: apply,
  };
}
