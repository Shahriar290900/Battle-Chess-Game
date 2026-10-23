// Pane manager: renders extra 3D views with the MAIN renderer into a small corner region of the main canvas, then
// copies the pixels into an ordinary <canvas> element in the page. The copy means panes live in normal DOM layout
// (scrolling, stacking on phones, overlays) with no see-through holes. Panes are capped at 30 fps, render at a
// reduced resolution and are skipped entirely while hidden / off-screen / tab in background / marked idle.
import { gsap } from 'gsap';
import { AgXToneMapping, Vector2, type PerspectiveCamera, type Scene, type WebGLRenderer } from 'three';

export interface Pane {
  /** The visible 2D canvas (add it to the DOM). */
  readonly el: HTMLCanvasElement;
  scene: Scene;
  camera: PerspectiveCamera;
  /** Return false to skip this frame (idle view: nothing changed). */
  needsRender?: () => boolean;
  /** Called just before the render (e.g. to show the hidden board root). */
  before?: () => void;
  after?: () => void;
  /** Longest side of the render region in device pixels (default 560). */
  maxSide?: number;
  /** Frames per second cap (default 30). */
  fps?: number;
  /** Observe visibility changes. */
  onVisible?: (visible: boolean) => void;
  readonly visible: boolean;
  dispose(): void;
}

export interface PaneManager {
  create(init: { scene: Scene; camera: PerspectiveCamera; maxSide?: number; fps?: number }): Pane;
  dispose(): void;
}

export function createPaneManager(renderer: WebGLRenderer): PaneManager {
  const panes = new Set<PaneImpl>();
  const size = new Vector2();
  let lastNow = 0;

  class PaneImpl implements Pane {
    readonly el = document.createElement('canvas');
    scene: Scene; camera: PerspectiveCamera;
    needsRender?: () => boolean; before?: () => void; after?: () => void; onVisible?: (v: boolean) => void;
    maxSide: number; fps: number;
    visible = false;
    private last = 0;
    private readonly g: CanvasRenderingContext2D;
    constructor(init: { scene: Scene; camera: PerspectiveCamera; maxSide?: number; fps?: number }) {
      this.scene = init.scene; this.camera = init.camera; this.maxSide = init.maxSide ?? 560; this.fps = init.fps ?? 30;
      this.el.className = 'learn-pane-canvas';
      this.g = this.el.getContext('2d')!;
    }
    isVisible(): boolean {
      if (document.hidden || !this.el.isConnected) return false;
      const r = this.el.getBoundingClientRect();
      return r.width > 4 && r.height > 4 && r.bottom > 0 && r.top < window.innerHeight && r.right > 0 && r.left < window.innerWidth;
    }
    render(now: number): void {
      const vis = this.isVisible();
      if (vis !== this.visible) { this.visible = vis; this.onVisible?.(vis); }
      if (!vis) return;
      if (now - this.last < 1000 / this.fps - 2) return;
      if (this.needsRender && !this.needsRender()) return;
      this.last = now;
      const r = this.el.getBoundingClientRect();
      const canvas = renderer.domElement;
      const ratio = renderer.getPixelRatio();
      // device-pixel region, reduced: never above maxSide, never above the canvas drawing buffer
      let k = Math.min(1, this.maxSide / Math.max(r.width, r.height));
      let pw = Math.max(16, Math.round(r.width * k)); let ph = Math.max(16, Math.round(r.height * k));
      pw = Math.min(pw, canvas.width); ph = Math.min(ph, canvas.height);
      k = pw / r.width;
      if (this.el.width !== pw || this.el.height !== ph) { this.el.width = pw; this.el.height = ph; }
      this.camera.aspect = pw / ph;
      this.camera.updateProjectionMatrix();
      renderer.getSize(size);
      const prevTM = renderer.toneMapping;
      this.before?.();
      renderer.setRenderTarget(null);
      renderer.toneMapping = AgXToneMapping; // the main pipeline tone-maps inside the post stack
      renderer.setViewport(0, 0, pw / ratio, ph / ratio);
      renderer.render(this.scene, this.camera);
      renderer.toneMapping = prevTM;
      renderer.setViewport(0, 0, size.x, size.y);
      this.after?.();
      this.g.drawImage(canvas, 0, canvas.height - ph, pw, ph, 0, 0, pw, ph);
    }
    dispose(): void { panes.delete(this); this.el.remove(); }
  }

  const tick = (time: number) => {
    const now = time * 1000;
    if (now === lastNow) return;
    lastNow = now;
    for (const p of panes) {
      try { p.render(now); } catch (e) { console.error('[learn] pane render failed', e); }
    }
  };
  gsap.ticker.add(tick);

  return {
    create(init) { const p = new PaneImpl(init); panes.add(p); return p; },
    dispose() { gsap.ticker.remove(tick); for (const p of [...panes]) p.dispose(); panes.clear(); },
  };
}
