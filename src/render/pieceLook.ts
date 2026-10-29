// Piece silhouette edge: a faction-tinted darkening of the grazing-angle pixels of every piece material, so a pale piece
// never melts into a pale square and a dark one keeps a crisp outline. It is a fragment patch of the existing per-actor
// MeshStandardMaterial (no extra draw call, no inverted hull); strength 0 skips the work (Low tier). The patch chains with
// the fx shaders (fx/shaders/glsl.ts chains onBeforeCompile / cache keys), so install it before any effect clones a material.
import { Color, type Material, type Mesh, type Object3D, type WebGLProgramParametersWithUniforms, type WebGLRenderer } from 'three';
import type { Faction } from '../contracts';

const strength = { value: 1 };
const COLORS: Record<Faction, { value: Color }> = {
  emberhold: { value: new Color(0.09, 0.045, 0.02) }, // burnt umber
  rime: { value: new Color(0.02, 0.05, 0.11) }, // deep frost navy
};

export function setEdgeStrength(v: number): void { strength.value = v; }

export function installPieceLook(root: Object3D, faction: Faction): void {
  root.traverse((o) => {
    const mesh = o as Mesh;
    if (!mesh.isMesh) return;
    const mats = Array.isArray(mesh.material) ? mesh.material : [mesh.material];
    for (const mat of mats) patch(mat, faction);
  });
}

function patch(mat: Material, faction: Faction): void {
  if (!(mat as { isMeshStandardMaterial?: boolean }).isMeshStandardMaterial || mat.userData.bcEdge) return;
  mat.userData.bcEdge = true;
  const prev = mat.onBeforeCompile;
  const prevKey = mat.customProgramCacheKey?.bind(mat);
  const color = COLORS[faction];
  mat.onBeforeCompile = (shader: WebGLProgramParametersWithUniforms, renderer: WebGLRenderer) => {
    prev?.call(mat, shader, renderer);
    shader.uniforms.uEdgeK = strength;
    shader.uniforms.uEdgeCol = color;
    shader.fragmentShader = shader.fragmentShader
      .replace('#include <common>', '#include <common>\nuniform float uEdgeK;\nuniform vec3 uEdgeCol;')
      .replace('#include <opaque_fragment>', `
        if (uEdgeK > 0.001) {
          float bcF = 1.0 - clamp(abs(dot(normal, normalize(vViewPosition))), 0.0, 1.0);
          float bcE = smoothstep(0.42, 0.96, bcF);
          outgoingLight = mix(outgoingLight, uEdgeCol, clamp(bcE * uEdgeK * 0.85, 0.0, 0.92));
        }
        #include <opaque_fragment>`);
  };
  mat.customProgramCacheKey = () => (prevKey ? prevKey() : '') + '|bcEdge';
  mat.needsUpdate = true;
}
