// Quality tiers (DECISIONS #9). Applying a tier fans out to the renderer, shadows, piece LOD, fx and post-processing.
//
// Auto mode:
//   1. device sniffing picks the first tier (see device.ts),
//   2. after loading, a real 2-3 s probe renders the actual scene (with gl.finish, so GPU time counts) and steps the tier
//      up or down: Low <-> Medium <-> High,
//   3. while playing, sustained fps < 40 for 5 s steps the tier down (with a toast); a lighter dynamic-resolution loop
//      nudges the render scale between 0.6 and 1.0 to hold the frame-rate target before that happens.
// An explicit tier in Settings always wins and disables the automatic steps.
import { GRAPHICS_PRESETS } from '../contracts';
import { graphicsForTier } from '../core/settings';
import type { FxApi, PlatformApi, PostPipeline, QualityTier, SettingsStore } from '../contracts';
import type { BoardImpl } from './board';
import type { DeviceInfo } from './device';
import type { Lighting } from './lighting';
import { PIXEL_RATIO_CAP, type RenderKit } from './scene';

export interface QualityManager {
  readonly tier: QualityTier;
  readonly device: DeviceInfo;
  /** Factor (0.6-1) the dynamic-resolution loop applies on top of Settings.graphics.resolutionScale. */
  readonly dynScale: number;
  apply(tier: QualityTier): void;
  /** Resolve the tier from settings (auto -> device guess, then the real probe) and apply it. */
  resolve(): Promise<QualityTier>;
  /** Real render probe (idle board); returns the tier the device sustains. */
  benchmark(): Promise<QualityTier>;
  /** Call every frame with the real frame time. `busy` = a capture cinematic is playing (lower fps tolerated). */
  update(dt: number, busy: boolean): void;
  /** Pause automatic downgrades (loading, menus, hidden tab). */
  setMonitoring(on: boolean): void;
}

export interface QualityDeps {
  kit: RenderKit;
  lighting: Lighting;
  board: BoardImpl;
  fx: FxApi;
  post: PostPipeline;
  platform: PlatformApi;
  settings: SettingsStore;
  device: DeviceInfo;
  /** Render one frame through the full pipeline (used by the probe). */
  renderFrame: (dt: number) => void;
  /** Re-apply the detailed graphics options after a tier change. */
  applyGraphics?: () => void;
  /** Shown when the tier is lowered automatically. */
  notify?: (message: string) => void;
}

/** Small self-removing toast (neutral styling; the UI layer may restyle `.bc-toast`). */
export function createToaster(parent: HTMLElement): (message: string) => void {
  let timer = 0;
  let el: HTMLDivElement | null = null;
  return (message) => {
    if (!el) {
      el = document.createElement('div');
      el.className = 'bc-toast';
      el.setAttribute('role', 'status');
      el.style.cssText = 'position:fixed;left:50%;bottom:calc(18px + env(safe-area-inset-bottom,0px));transform:translateX(-50%);z-index:9998;'
        + 'max-width:min(92vw,520px);padding:9px 16px;border-radius:999px;font:600 13px/1.3 system-ui,sans-serif;color:#f2e6c9;'
        + 'background:rgba(24,18,12,.92);border:1px solid rgba(214,170,96,.7);box-shadow:0 6px 24px rgba(0,0,0,.5);'
        + 'pointer-events:none;transition:opacity .35s;opacity:0;text-align:center;';
      parent.append(el);
    }
    el.textContent = message;
    requestAnimationFrame(() => { if (el) el.style.opacity = '1'; });
    window.clearTimeout(timer);
    timer = window.setTimeout(() => { if (el) el.style.opacity = '0'; }, 4200);
  };
}

const ORDER: QualityTier[] = ['low', 'medium', 'high'];

export function createQuality(d: QualityDeps): QualityManager {
  let tier: QualityTier = d.device.guess;
  let resolved: QualityTier | null = null; // auto result (probe), reused for later 'auto' switches
  let dynScale = 1;
  let monitoring = false;

  const apply = (t: QualityTier) => {
    tier = t;
    d.kit.setPixelRatioCap(PIXEL_RATIO_CAP[t]);
    d.board.setLod(t === 'high' ? 0 : 1);
    d.lighting.setTier(t);
    d.lighting.setShadows(GRAPHICS_PRESETS[t].shadows);
    d.fx.setQuality(t);
    d.post.setQuality(t);
    d.post.setSize(d.kit.width, d.kit.height);
    // Presets follow the tier unless the user customised the options.
    const cur = d.settings.get().graphics;
    // Low keeps full resolution (pixelation hurts more than it saves; the savings are shadows/post/LOD); dynamic resolution only reacts to real drops.
    if (cur.preset !== 'custom') d.settings.set('graphics', { ...graphicsForTier(t, cur), resolutionScale: t === 'low' ? 1 : GRAPHICS_PRESETS[t].resolutionScale });
    d.applyGraphics?.();
  };

  /** Median GPU-inclusive frame cost over `ms` of real rendering of the idle board. */
  const probe = (ms: number): Promise<number> => new Promise((resolve) => {
    const gl = d.kit.renderer.getContext();
    const start = performance.now();
    const samples: number[] = [];
    let last = start, frames = 0;
    const bail = setTimeout(() => resolve(Infinity), ms + 6000); // rAF throttled (background tab): treat as unknown
    const tick = () => {
      const now = performance.now();
      d.renderFrame(Math.min((now - last) / 1000, 0.1));
      gl.finish(); // include GPU time, not just command submission
      const cost = performance.now() - now;
      last = now;
      if (++frames > 6) samples.push(cost); // first frames upload buffers / textures
      if (frames > 3 && cost > 400) { clearTimeout(bail); resolve(cost); return; } // software GL / hopeless
      if (now - start < ms) { requestAnimationFrame(tick); return; }
      clearTimeout(bail);
      samples.sort((a, b) => a - b);
      resolve(samples.length ? samples[Math.floor(samples.length / 2)] : Infinity);
    };
    requestAnimationFrame(tick);
  });

  const benchmark = async (): Promise<QualityTier> => {
    let t = d.device.guess;
    apply(t);
    let cost = await probe(2200);
    if (!Number.isFinite(cost)) return t; // could not measure: stay on the safe guess
    // Step down while the frame does not fit comfortably in 60 fps (the iGPU target is Medium at >= 50 fps).
    while (cost > 15 && t !== 'low') {
      t = ORDER[ORDER.indexOf(t) - 1];
      apply(t);
      cost = await probe(1400);
      if (!Number.isFinite(cost)) return t;
    }
    // Step up when there is plenty of headroom (never on weak GPUs for High).
    if (t === 'low' && cost < 6.5 && !d.device.veryWeak) {
      apply('medium');
      const c2 = await probe(1400);
      if (Number.isFinite(c2) && c2 < 11) { t = 'medium'; cost = c2; } else apply('low');
    }
    if (t === 'medium' && cost < 6 && !d.device.weak) {
      apply('high');
      const c3 = await probe(1400);
      if (Number.isFinite(c3) && c3 < 11) t = 'high'; else apply('medium');
    }
    if (t === 'low' && cost > 22) dynScale = 0.8; // still too slow: start with a lower render scale
    return t;
  };

  // ---- sustained-fps monitor + dynamic resolution
  let slowFor = 0, fastFor = 0, belowFor = 0, ema = 60, cooldown = 0, graceUntil = 0;
  const isAuto = () => d.settings.get().quality === 'auto';
  const target = () => (d.settings.get().graphics.fpsCap === 30 ? 30 : 60);

  const manager: QualityManager = {
    get tier() { return tier; },
    get device() { return d.device; },
    get dynScale() { return dynScale; },
    apply,
    benchmark,
    setMonitoring(on) { monitoring = on; slowFor = fastFor = belowFor = 0; graceUntil = performance.now() + 3000; },
    async resolve() {
      const pref = d.settings.get().quality;
      if (pref !== 'auto') { apply(pref); return pref; }
      if (resolved === null) resolved = await benchmark();
      apply(resolved);
      return resolved;
    },
    update(dt, busy) {
      if (!monitoring || dt <= 0 || document.hidden) return;
      const now = performance.now();
      if (now < graceUntil) return;
      ema += (1 / Math.min(dt, 0.5) - ema) * 0.1;
      cooldown = Math.max(0, cooldown - dt);
      if (!isAuto()) return;
      const tgt = target();
      // --- dynamic resolution: hold the target before resorting to a tier drop
      if (ema < tgt * 0.88) { slowFor += dt; fastFor = 0; } else if (ema > tgt * 0.97) { fastFor += dt; slowFor = 0; } else { slowFor = fastFor = 0; }
      if (slowFor > 1.5 && dynScale > 0.6 && cooldown === 0) {
        dynScale = Math.max(0.6, dynScale - 0.1); slowFor = 0; cooldown = 1.2;
        d.applyGraphics?.();
      } else if (fastFor > 5 && dynScale < 1 && cooldown === 0) {
        dynScale = Math.min(1, dynScale + 0.05); fastFor = 0; cooldown = 2;
        d.applyGraphics?.();
      }
      // --- sustained low fps: drop a tier
      const floor = busy ? 26 : 40;
      belowFor = ema < floor ? belowFor + dt : 0;
      if (belowFor > 5 && tier !== 'low') {
        belowFor = 0;
        const next = ORDER[ORDER.indexOf(tier) - 1];
        resolved = next;
        dynScale = 1;
        apply(next);
        graceUntil = performance.now() + 4000;
        d.notify?.(`Graphics set to ${next === 'low' ? 'Low' : 'Medium'} for smoother play`);
      }
    },
  };

  d.settings.subscribe((s, key) => {
    if (key !== 'quality') return;
    if (s.quality !== 'auto') { dynScale = 1; apply(s.quality); } else void manager.resolve();
  });
  return manager;
}
