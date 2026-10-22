import { Color, Vector3, type Material } from 'three';
import { cloneWithFx } from './glsl';
import { FX_COLORS } from '../common';

export interface SweepHandle { material: Material; uniforms: { uFxP: { value: number }; uFxC: { value: Vector3 }; uFxR: { value: number } }; }

/** Glowing crack mask sweeping outward from an impact point (world space). */
export function makeEmberMaterial(src: Material, center: Vector3, radius: number): SweepHandle {
  const uniforms = {
    uFxP: { value: 0 },
    uFxC: { value: center.clone() },
    uFxR: { value: radius },
    uFxColor: { value: new Color().copy(FX_COLORS.emberhold.main) },
    uFxHot: { value: new Color().copy(FX_COLORS.emberhold.hot) },
  };
  const material = cloneWithFx(src, {
    key: 'fxEmber',
    uniforms,
    decl: 'uniform float uFxP; uniform vec3 uFxC; uniform float uFxR; uniform vec3 uFxColor; uniform vec3 uFxHot;',
    apply: /* glsl */ `
      float fxD = distance(vFxW, uFxC) / uFxR;
      float fxFront = uFxP * 1.4;
      float fxN1 = fxNoise(vFxW * 6.5);
      float fxN2 = fxNoise(vFxW * 14.0 + 3.7);
      float fxReach = 1.0 - smoothstep(fxFront - 0.3, fxFront, fxD + (fxN1 - 0.5) * 0.3);
      float fxR1 = 1.0 - smoothstep(0.0, 0.07, abs(fxN1 - 0.5));
      float fxR2 = 1.0 - smoothstep(0.0, 0.05, abs(fxN2 - 0.5));
      float fxCrack = max(fxR1, fxR2 * 0.8) * fxReach;
      diffuseColor.rgb *= 1.0 - 0.4 * fxReach * uFxP;
      vec3 fxGlow = mix(uFxColor, uFxHot, fxR1 * fxR2);
      totalEmissiveRadiance += fxGlow * fxCrack * 3.2 + uFxColor * fxReach * 0.12;
    `,
  });
  return { material, uniforms };
}
