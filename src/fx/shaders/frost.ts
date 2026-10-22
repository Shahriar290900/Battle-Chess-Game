import { Color, Vector3 } from 'three';
import { cloneWithFx } from './glsl';
import { FX_COLORS } from '../common';
import type { SweepHandle } from './ember';
import type { Material } from 'three';

/** White freeze sweeping outward from an impact point (world space), with a bright cyan leading edge. */
export function makeFrostMaterial(src: Material, center: Vector3, radius: number): SweepHandle {
  const uniforms = {
    uFxP: { value: 0 },
    uFxC: { value: center.clone() },
    uFxR: { value: radius },
    uFxColor: { value: new Color().copy(FX_COLORS.rime.hot) },
  };
  const material = cloneWithFx(src, {
    key: 'fxFrost',
    uniforms,
    decl: 'uniform float uFxP; uniform vec3 uFxC; uniform float uFxR; uniform vec3 uFxColor;',
    apply: /* glsl */ `
      float fxD = distance(vFxW, uFxC) / uFxR;
      float fxFront = uFxP * 1.4;
      float fxN = fxNoise(vFxW * 9.0) * 0.6 + fxNoise(vFxW * 22.0) * 0.4;
      float fxReach = 1.0 - smoothstep(fxFront - 0.2, fxFront, fxD + (fxN - 0.5) * 0.35);
      vec3 fxWn = inverseTransformDirection(normal, viewMatrix);
      float fxTop = 0.7 + 0.3 * clamp(fxWn.y * 0.5 + 0.5, 0.0, 1.0);
      float fxAmt = fxReach * mix(0.7, 1.0, fxN) * fxTop;
      diffuseColor.rgb = mix(diffuseColor.rgb, vec3(0.84, 0.93, 0.98), fxAmt * 0.88);
      roughnessFactor = mix(roughnessFactor, 0.8, fxAmt);
      metalnessFactor *= 1.0 - fxAmt * 0.85;
      float fxEdge = smoothstep(fxFront - 0.14, fxFront - 0.04, fxD) * (1.0 - smoothstep(fxFront - 0.04, fxFront, fxD)) * step(0.001, uFxP);
      totalEmissiveRadiance += uFxColor * (fxAmt * 0.18 + fxEdge * 1.6);
    `,
  });
  return { material, uniforms };
}
