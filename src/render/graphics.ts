// Adjustable graphics: applies Settings.graphics live to renderer resolution, shadows, post (bloom / SMAA), fx
// (particles / physics), ambient dressing, the kinematics layer, the FPS overlay and the frame limiter value.
import type { FxApi, GraphicsSettings, KinematicsApi, PostPipeline, QualityTier, SettingsStore } from '../contracts';
import type { BoardImpl } from './board';
import type { Lighting } from './lighting';
import type { RenderKit } from './scene';

export interface GraphicsDeps {
  settings: SettingsStore;
  kit: RenderKit;
  lighting: Lighting;
  post: PostPipeline;
  fx: FxApi;
  board: BoardImpl;
  kinematics: KinematicsApi;
  /** The tier currently in effect (for the pixel-ratio cap). */
  tier: () => QualityTier;
}

export function applyGraphics(d: GraphicsDeps, g: GraphicsSettings = d.settings.get().graphics): void {
  d.kit.setResolutionScale(g.resolutionScale);
  d.lighting.setShadows(g.shadows);
  d.lighting.setAmbient(g.ambient);
  d.board.setAmbient(g.ambient);
  d.post.setGraphics?.(g);
  d.fx.setGraphics?.(g);
  d.kinematics.setEnabled(g.secondaryMotion);
  d.post.setSize(d.kit.width, d.kit.height);
}

/** Small FPS readout in the corner; updates twice a second and costs nothing while hidden. */
export function createFpsOverlay(parent: HTMLElement): { frame(dt: number): void; setVisible(on: boolean): void } {
  const el = document.createElement('div');
  el.className = 'fps';
  el.hidden = true;
  parent.append(el);
  let acc = 0, frames = 0, on = false;
  return {
    setVisible(v) { on = v; el.hidden = !v; acc = 0; frames = 0; },
    frame(dt) {
      if (!on) return;
      acc += dt; frames++;
      if (acc >= 0.5) { el.textContent = `${Math.round(frames / acc)} FPS`; acc = 0; frames = 0; }
    },
  };
}
