import { Color, type Material } from 'three';
import { cloneWithFx } from './glsl';
import { FX_COLORS } from '../common';
import type { Faction } from '../../contracts';

export interface DissolveHandle { material: Material; uniforms: { uFxP: { value: number } }; }

/** Noise-threshold dissolve with a faction-coloured glowing edge. progress 0 (intact) .. 1 (gone). */
export function makeDissolveMaterial(src: Material, faction: Faction): DissolveHandle {
  const edge = new Color().copy(faction === 'emberhold' ? FX_COLORS.emberhold.main : FX_COLORS.rime.hot);
  const uniforms = {
    uFxP: { value: 0 },
    uFxEdge: { value: edge },
    uFxPow: { value: faction === 'emberhold' ? 5.0 : 3.5 },
    uFxW: { value: 0.09 },
    uFxScale: { value: 7.0 },
  };
  const material = cloneWithFx(src, {
    key: 'fxDissolve',
    uniforms,
    decl: 'uniform float uFxP; uniform vec3 uFxEdge; uniform float uFxPow; uniform float uFxW; uniform float uFxScale;',
    apply: /* glsl */ `
      float fxDn = fxNoise(vFxW * uFxScale) * 0.65 + fxNoise(vFxW * uFxScale * 2.3) * 0.35;
      float fxTh = uFxP * 1.2 - 0.1;
      if (fxDn < fxTh) discard;
      float fxEdge = 1.0 - smoothstep(0.0, uFxW, fxDn - fxTh);
      totalEmissiveRadiance += uFxEdge * fxEdge * uFxPow * step(0.001, uFxP);
    `,
  });
  return { material, uniforms };
}
