// Dev perf instrumentation. Cheap enough to leave on (a handful of performance.now() calls per frame):
//   - `?perf` shows an overlay: fps, frame ms (avg / p95), renderer.info (calls, triangles, programs, textures, geometries)
//     and per-system CPU ms (fx, mixers, kinematics, render, ...). Add `&sync` to gl.finish() after render so the
//     "render" slot includes GPU time (slower, but tells where the frame really goes).
//   - `window.__perf` (always) exposes start()/stop() for perf/bench.mjs: windowed statistics of a scenario.
import type { WebGLRenderer } from 'three';

export interface PerfReport {
  frames: number;
  seconds: number;
  fps: number;
  frameMsAvg: number;
  frameMsP50: number;
  frameMsP95: number;
  frameMsMax: number;
  systems: Record<string, number>;
  calls: number;
  triangles: number;
  programs: number;
  textures: number;
  geometries: number;
}

export interface Perf {
  /** Start timing a system for this frame. */
  begin(name: string): void;
  /** Stop timing it (accumulates into the current frame). */
  end(name: string): void;
  /** Call once per rendered frame, after everything has run (measures real elapsed time itself). */
  frame(): void;
  /** Call right before the frame renders: resets renderer.info (autoReset is off so composers count every pass). */
  frameStart(): void;
  start(): void;
  stop(): PerfReport;
  readonly enabled: boolean;
  /** Smoothed fps over the last ~1 s (always maintained; used by auto-quality too). */
  readonly fps: number;
}

export function createPerf(renderer: WebGLRenderer, parent: HTMLElement | null): Perf {
  const params = new URLSearchParams(location.search);
  const enabled = params.has('perf');
  const sync = params.has('sync');
  const gl = renderer.getContext();
  renderer.info.autoReset = false;

  const t0 = new Map<string, number>();
  const frameSys = new Map<string, number>();
  const avgSys = new Map<string, number>(); // exponential average for the overlay

  let fpsAcc = 0, fpsFrames = 0, fps = 60, lastT = 0;
  let rec: { dts: number[]; sys: Map<string, number>; calls: number; tris: number; start: number } | null = null;
  let infoShown = { calls: 0, tris: 0 };

  let el: HTMLDivElement | null = null;
  let uiAcc = 0;
  if (enabled && parent) {
    el = document.createElement('div');
    el.style.cssText = 'position:fixed;left:6px;top:calc(6px + env(safe-area-inset-top,0px));z-index:9999;pointer-events:none;'
      + 'font:11px/1.35 ui-monospace,Menlo,monospace;color:#9fffa8;background:rgba(0,0,0,.62);padding:5px 8px;border-radius:4px;white-space:pre;';
    parent.append(el);
  }

  const perf: Perf = {
    enabled,
    get fps() { return fps; },
    begin(name) { t0.set(name, performance.now()); },
    end(name) {
      const s = t0.get(name);
      if (s === undefined) return;
      frameSys.set(name, (frameSys.get(name) ?? 0) + (performance.now() - s));
    },
    frameStart() { renderer.info.reset(); },
    frame() {
      // Real wall-clock frame time (the loop's dt is capped / smoothed, which would hide a slow GPU or software GL).
      const nowT = performance.now();
      const dt = lastT ? Math.min((nowT - lastT) / 1000, 5) : 0.016;
      lastT = nowT;
      if (sync && enabled) { perf.begin('gpuWait'); gl.finish(); perf.end('gpuWait'); }
      const info = renderer.info;
      infoShown = { calls: info.render.calls, tris: info.render.triangles };
      fpsAcc += dt; fpsFrames++;
      if (fpsAcc >= 1) { fps = fpsFrames / fpsAcc; fpsAcc = 0; fpsFrames = 0; }
      for (const [k, v] of frameSys) {
        if (rec) rec.sys.set(k, (rec.sys.get(k) ?? 0) + v);
        avgSys.set(k, (avgSys.get(k) ?? v) * 0.92 + v * 0.08);
      }
      frameSys.clear();
      if (rec) { rec.dts.push(dt * 1000); rec.calls = Math.max(rec.calls, infoShown.calls); rec.tris = Math.max(rec.tris, infoShown.tris); }
      if (el) {
        uiAcc += dt;
        if (uiAcc >= 0.5) {
          uiAcc = 0;
          const sys = [...avgSys].map(([k, v]) => `${k.padEnd(9)} ${v.toFixed(2)} ms`).join('\n');
          el.textContent = `${fps.toFixed(0)} fps  ${(1000 / Math.max(fps, 1)).toFixed(1)} ms\n`
            + `calls ${infoShown.calls}  tris ${(infoShown.tris / 1000).toFixed(0)}k\n`
            + `prog ${info.programs?.length ?? 0}  tex ${info.memory.textures}  geo ${info.memory.geometries}\n${sys}`;
        }
      }
    },
    start() { rec = { dts: [], sys: new Map(), calls: 0, tris: 0, start: performance.now() }; },
    stop() {
      const r = rec ?? { dts: [], sys: new Map(), calls: 0, tris: 0, start: performance.now() };
      rec = null;
      const dts = [...r.dts].sort((a, b) => a - b);
      const n = dts.length || 1;
      const sum = dts.reduce((a, b) => a + b, 0);
      const systems: Record<string, number> = {};
      for (const [k, v] of r.sys) systems[k] = +(v / n).toFixed(3);
      return {
        frames: dts.length,
        seconds: +((performance.now() - r.start) / 1000).toFixed(2),
        fps: +(1000 / (sum / n || 1)).toFixed(1),
        frameMsAvg: +(sum / n).toFixed(2),
        frameMsP50: +(dts[Math.floor(n * 0.5)] ?? 0).toFixed(2),
        frameMsP95: +(dts[Math.min(n - 1, Math.floor(n * 0.95))] ?? 0).toFixed(2),
        frameMsMax: +(dts[n - 1] ?? 0).toFixed(2),
        systems,
        calls: r.calls,
        triangles: r.tris,
        programs: renderer.info.programs?.length ?? 0,
        textures: renderer.info.memory.textures,
        geometries: renderer.info.memory.geometries,
      };
    },
  };
  (window as unknown as Record<string, unknown>).__perf = perf;
  (window as unknown as Record<string, unknown>).__gpuInfo = () => {
    const ext = gl.getExtension('WEBGL_debug_renderer_info');
    return ext ? { vendor: gl.getParameter(ext.UNMASKED_VENDOR_WEBGL), renderer: gl.getParameter(ext.UNMASKED_RENDERER_WEBGL) } : { vendor: gl.getParameter(gl.VENDOR), renderer: gl.getParameter(gl.RENDERER) };
  };
  return perf;
}
