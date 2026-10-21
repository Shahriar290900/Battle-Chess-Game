// Safety net around the post-processing pipeline (owned by vfx). If the composer produces an empty frame
// on this GPU/tier (observed: black output + GL_INVALID_OPERATION at low/medium tiers on some drivers),
// fall back to plain scene rendering with the renderer's own tone mapping, and retry on the next tier change.
import { AgXToneMapping, NoToneMapping, type PerspectiveCamera, type Scene, type WebGLRenderer } from 'three';
import type { PostPipeline, QualityTier } from '../contracts';
import { createPost } from './post';

export function createGuardedPost(renderer: WebGLRenderer, scene: Scene, camera: PerspectiveCamera, tier: QualityTier): PostPipeline {
  const inner = createPost(renderer, scene, camera, tier);
  const gl = renderer.getContext();
  let broken = false;
  let probe = true;
  const px = new Uint8Array(4);

  const frameHasContent = (): boolean => {
    const w = gl.drawingBufferWidth, h = gl.drawingBufferHeight;
    for (const [fx, fy] of [[0.5, 0.5], [0.5, 0.3], [0.3, 0.6], [0.7, 0.6], [0.5, 0.8]]) {
      gl.readPixels(Math.floor(w * fx), Math.floor(h * fy), 1, 1, gl.RGBA, gl.UNSIGNED_BYTE, px);
      if (px[3] > 0 && (px[0] | px[1] | px[2]) > 0) return true;
    }
    return false;
  };

  return {
    render(dt) {
      if (broken) { renderer.setRenderTarget(null); renderer.render(scene, camera); }
      else {
        inner.render(dt);
        if (probe) {
          probe = false;
          if (!frameHasContent()) {
            broken = true;
            renderer.setRenderTarget(null); // the failed composer may have left an off-screen target bound
            renderer.toneMapping = AgXToneMapping;
            console.warn('[post] composer produced an empty frame; using direct rendering until the quality tier changes');
          }
        }
      }
    },
    setSize(w, h) { inner.setSize(w, h); },
    setQuality(t) {
      if (broken) { broken = false; renderer.toneMapping = NoToneMapping; }
      inner.setQuality(t);
      probe = true;
    },
    bloomPulse(s, d) { inner.bloomPulse(s, d); },
  };
}
