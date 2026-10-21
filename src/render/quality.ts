// Quality tiers (DECISIONS #9). Auto tier = 2 s GPU benchmark on desktop, Low on mobile/APK; the Settings
// override wins. Applying a tier fans out to the renderer, shadows, piece LOD, fx and post-processing.
import type { FxApi, PlatformApi, PostPipeline, QualityTier, SettingsStore } from '../contracts';
import type { BoardImpl } from './board';
import type { Lighting } from './lighting';
import { PIXEL_RATIO_CAP, type RenderKit } from './scene';

export interface QualityManager {
  readonly tier: QualityTier;
  apply(tier: QualityTier): void;
  /** Resolve the tier from settings (auto → mobile ? low : benchmark) and apply it. */
  resolve(): Promise<QualityTier>;
  /** 2 s render benchmark; returns the tier the device can sustain. */
  benchmark(): Promise<QualityTier>;
}

export interface QualityDeps {
  kit: RenderKit;
  lighting: Lighting;
  board: BoardImpl;
  fx: FxApi;
  post: PostPipeline;
  platform: PlatformApi;
  settings: SettingsStore;
  /** Render one frame through the full pipeline (used by the benchmark). */
  renderFrame: (dt: number) => void;
}

export function createQuality(d: QualityDeps): QualityManager {
  let tier: QualityTier = d.platform.isMobile ? 'low' : 'medium';
  let autoTier: QualityTier | null = d.platform.isMobile ? 'low' : null;

  const apply = (t: QualityTier) => {
    tier = t;
    d.kit.setPixelRatioCap(PIXEL_RATIO_CAP[t]);
    d.lighting.setShadowSize(t === 'low' ? 1024 : 2048);
    d.board.setLod(t === 'low' ? 1 : 0);
    d.lighting.setTier(t);
    d.fx.setQuality(t);
    d.post.setQuality(t);
    d.post.setSize(d.kit.width, d.kit.height);
  };

  const benchmark = (): Promise<QualityTier> => new Promise((resolve) => {
    const gl = d.kit.renderer.getContext();
    apply('high');
    const start = performance.now();
    const samples: number[] = [];
    let last = start;
    let frames = 0;
    const bail = setTimeout(() => finish('medium'), 4000); // rAF throttled (background tab): stay safe
    const finish = (t: QualityTier) => { clearTimeout(bail); resolve(t); };
    const tick = () => {
      const now = performance.now();
      const t0 = now;
      d.renderFrame(Math.min((now - last) / 1000, 0.1));
      gl.finish(); // include GPU time, not just command submission
      const cost = performance.now() - t0;
      if (++frames > 6) samples.push(cost);
      last = now;
      // Software GL / very weak GPUs: do not sit through seconds-long frames.
      if (frames > 3 && cost > 400) { finish('low'); return; }
      if (now - start < 2000) { requestAnimationFrame(tick); return; }
      samples.sort((a, b) => a - b);
      const median = samples.length ? samples[Math.floor(samples.length / 2)] : 10;
      finish(median < 6.5 ? 'high' : median < 15 ? 'medium' : 'low');
    };
    requestAnimationFrame(tick);
  });

  const manager: QualityManager = {
    get tier() { return tier; },
    apply,
    benchmark,
    async resolve() {
      const pref = d.settings.get().quality;
      if (pref !== 'auto') { apply(pref); return pref; }
      if (autoTier === null) autoTier = await benchmark();
      apply(autoTier);
      return autoTier;
    },
  };

  d.settings.subscribe((s, key) => {
    if (key !== 'quality') return;
    if (s.quality !== 'auto') apply(s.quality);
    else void manager.resolve();
  });
  return manager;
}
