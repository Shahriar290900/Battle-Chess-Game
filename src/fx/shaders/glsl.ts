import type { IUniform, Material, WebGLProgramParametersWithUniforms } from 'three';

export const NOISE_GLSL = /* glsl */ `
float fxHash(vec3 p){ p = fract(p*0.3183099+vec3(0.1)); p*=17.0; return fract(p.x*p.y*p.z*(p.x+p.y+p.z)); }
float fxNoise(vec3 x){
  vec3 i=floor(x); vec3 f=fract(x); f=f*f*(3.0-2.0*f);
  return mix(mix(mix(fxHash(i),fxHash(i+vec3(1,0,0)),f.x), mix(fxHash(i+vec3(0,1,0)),fxHash(i+vec3(1,1,0)),f.x),f.y),
             mix(mix(fxHash(i+vec3(0,0,1)),fxHash(i+vec3(1,0,1)),f.x), mix(fxHash(i+vec3(0,1,1)),fxHash(i+vec3(1,1,1)),f.x),f.y), f.z);
}
`;

export interface InjectSpec {
  key: string;
  uniforms: Record<string, IUniform>;
  /** Extra declarations (uniforms/functions) placed in the fragment `common` chunk. */
  decl: string;
  /** Code run right after emissivemap_fragment (diffuseColor, roughnessFactor, totalEmissiveRadiance in scope). */
  apply: string;
}

/**
 * Clone `src` (so the shared original is untouched) and inject a world-space fragment effect via onBeforeCompile.
 * Chains any previous onBeforeCompile / cache key so effects can stack. Only MeshStandard/Physical materials are
 * patched; other types are returned as plain clones.
 */
export function cloneWithFx(src: Material, spec: InjectSpec): Material {
  const m = src.clone();
  if (!(src as any).isMeshStandardMaterial) return m;
  const prevBC = src.onBeforeCompile;
  const prevKey = src.customProgramCacheKey?.bind(src);
  m.onBeforeCompile = (shader: WebGLProgramParametersWithUniforms, renderer) => {
    prevBC?.call(src, shader, renderer);
    Object.assign(shader.uniforms, spec.uniforms);
    shader.vertexShader = shader.vertexShader
      .replace('#include <common>', '#include <common>\nvarying vec3 vFxW;')
      .replace('#include <project_vertex>', '#include <project_vertex>\nvFxW = (modelMatrix * vec4(transformed, 1.0)).xyz;');
    shader.fragmentShader = shader.fragmentShader
      .replace('#include <common>', `#include <common>\nvarying vec3 vFxW;\n${NOISE_GLSL}\n${spec.decl}`)
      .replace('#include <emissivemap_fragment>', `#include <emissivemap_fragment>\n${spec.apply}`);
  };
  m.customProgramCacheKey = () => (prevKey ? prevKey() : '') + '|' + spec.key;
  m.needsUpdate = true;
  return m;
}
