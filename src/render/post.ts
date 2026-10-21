// STUB (lead) — replaced by vfx-shaders (postprocessing: bloom, SMAA, vignette).
import type { CreatePost } from '../contracts';

export const createPost: CreatePost = (renderer, scene, camera) => ({
  render() { renderer.render(scene, camera); },
  setSize(w, h) { renderer.setSize(w, h, false); },
  setQuality() {},
  bloomPulse() {},
});
