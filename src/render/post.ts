import {
  BloomEffect, EffectComposer, EffectPass, KernelSize, RenderPass, SMAAEffect, SMAAPreset, ToneMappingEffect, ToneMappingMode,
} from 'postprocessing';
import { ACESFilmicToneMapping, AgXToneMapping, ShaderChunk, HalfFloatType, NeutralToneMapping, NoToneMapping, UnsignedByteType, type ToneMapping } from 'three';
import { GRAPHICS_PRESETS, type CreatePost, type GraphicsSettings, type PostPipeline } from '../contracts';
import { registerBloomPulse } from '../fx/bloomBus';

/**
 * Pipeline per tier (the pixel ratio and resolution scale belong to the render kit, which calls setSize after changing them):
 *   - bloom off and no SMAA (Low)        : NO composer. The scene renders straight to the canvas with the renderer's own tone mapping,
 *                                          so there is no off-screen colour buffer, no extra pass and no bloom cost.
 *   - bloom on (Medium)                  : Render -> EffectPass[Bloom (half-res, 4-5 mips) + ToneMapping]
 *   - bloom + SMAA (High)                : the same, then an SMAA pass.
 * The vignette is a CSS overlay (see createVignette): it costs nothing on the GPU.
 * The chain is rebuilt whenever bloom / SMAA / bloom-cost class change, so the last pass always renders to screen. If the composer
 * cannot be built the pipeline degrades to direct rendering (no postGuard needed any more: the black-frame bug was Inf/NaN in the
 * half-float buffer, clamped below).
 */
// Half-float HDR buffers overflow to Inf on very bright specular highlights (smooth ice/bronze under strong lights);
// Inf/NaN then smears black across the whole frame through the bloom blur. Clamp scene colour before it is written.
// Must run before materials compile (createPost is called at start-up).
const CLAMP_FROM = 'gl_FragColor = vec4( outgoingLight, diffuseColor.a );';
if (ShaderChunk.opaque_fragment.includes(CLAMP_FROM)) {
  ShaderChunk.opaque_fragment = ShaderChunk.opaque_fragment.replace(CLAMP_FROM, 'gl_FragColor = vec4( min( max( outgoingLight, vec3( 0.0 ) ), vec3( 32.0 ) ), diffuseColor.a );');
}

const modeFor = (tm: ToneMapping) =>
  tm === AgXToneMapping ? ToneMappingMode.AGX : tm === NeutralToneMapping ? ToneMappingMode.NEUTRAL : tm === ACESFilmicToneMapping ? ToneMappingMode.ACES_FILMIC : ToneMappingMode.ACES_FILMIC;

/** Screen-space darkening toward the corners as a CSS radial gradient over the canvas. Never touches the GPU frame. */
export function createVignette(parent: HTMLElement, before?: Element | null): { setStrength(v: number): void; el: HTMLDivElement } {
  const el = document.createElement('div');
  el.className = 'bc-vignette';
  el.style.cssText = 'position:fixed;inset:0;pointer-events:none;';
  const set = (v: number) => {
    el.style.background = `radial-gradient(ellipse 78% 74% at 50% 52%, rgba(6,8,16,0) 52%, rgba(6,8,16,${(0.42 * v).toFixed(3)}) 100%)`;
  };
  set(1);
  parent.insertBefore(el, before ?? null);
  return { el, setStrength: set };
}

export const createPost: CreatePost = (renderer, scene, camera, tier) => {
  const gl = renderer.getContext();
  const isGL2 = typeof WebGL2RenderingContext !== 'undefined' && gl instanceof WebGL2RenderingContext;
  const ext = renderer.extensions;
  // HalfFloat render targets need EXT_color_buffer_float or EXT_color_buffer_half_float; otherwise stay 8-bit.
  const halfOk = isGL2 && (ext.has('EXT_color_buffer_float') || ext.has('EXT_color_buffer_half_float'));

  // The renderer keeps its own tone mapping for direct rendering; the composer takes it over while active.
  const directTone = renderer.toneMapping === NoToneMapping ? ACESFilmicToneMapping : renderer.toneMapping;
  const tmMode = modeFor(directTone);

  let composer: EffectComposer | null = null;
  let bloom: BloomEffect | null = null;
  let size: { w: number; h: number } | null = null;
  let gfx: GraphicsSettings = { ...GRAPHICS_PRESETS[tier] };
  let built = { bloom: false, aa: false, lite: false };
  let pulse = { s: 0, d: 0, t: 0 };
  const bloomBase = () => (gfx.preset === 'low' ? 0.7 : gfx.preset === 'medium' ? 0.75 : 0.85);

  const dispose = () => { try { composer?.dispose(); } catch { /* ignore */ } composer = null; bloom = null; };
  const goDirect = () => { renderer.setRenderTarget(null); renderer.toneMapping = directTone; };

  const wantsComposer = () => gfx.bloom || gfx.antialias;
  const liteBloom = () => gfx.preset === 'low' || gfx.preset === 'medium' || gfx.resolutionScale < 0.8;

  const build = () => {
    dispose();
    if (!wantsComposer()) { goDirect(); built = { bloom: false, aa: false, lite: false }; return; }
    const lite = liteBloom();
    const c = new EffectComposer(renderer, { frameBufferType: halfOk ? HalfFloatType : UnsignedByteType, multisampling: 0, depthBuffer: true, stencilBuffer: false });
    c.addPass(new RenderPass(scene, camera));
    const effects: ConstructorParameters<typeof EffectPass>[1][] = [];
    let b: BloomEffect | null = null;
    if (gfx.bloom) {
      b = new BloomEffect({
        intensity: bloomBase(), luminanceThreshold: 0.9, luminanceSmoothing: 0.22, mipmapBlur: true, radius: 0.7,
        levels: lite ? 4 : 6, kernelSize: KernelSize.MEDIUM,
      });
      b.resolution.scale = lite ? 0.5 : 1;
      effects.push(b);
    }
    effects.push(new ToneMappingEffect({ mode: tmMode }));
    c.addPass(new EffectPass(camera, ...effects));
    if (gfx.antialias) c.addPass(new EffectPass(camera, new SMAAEffect({ preset: SMAAPreset.MEDIUM })));
    composer = c; bloom = b;
    renderer.toneMapping = NoToneMapping; // the composer tone-maps (HDR emissive survives until bloom)
    built = { bloom: gfx.bloom, aa: gfx.antialias, lite };
    if (size) c.setSize(size.w, size.h, false);
  };

  const safeBuild = () => {
    try { build(); } catch (err) {
      console.warn('[post] composer unavailable, falling back to direct render', err);
      dispose();
      goDirect();
    }
  };
  const apply = () => {
    if (!composer && !wantsComposer()) { goDirect(); return; }
    if (!composer || built.bloom !== gfx.bloom || built.aa !== gfx.antialias || built.lite !== liteBloom()) safeBuild();
    else if (bloom) bloom.intensity = bloomBase();
  };
  safeBuild();

  const pulseFn = (strength: number, duration: number) => { pulse = { s: strength, d: Math.max(0.01, duration), t: 0 }; };
  registerBloomPulse(pulseFn);

  return {
    render(dt) {
      if (!composer) { renderer.render(scene, camera); return; }
      if (pulse.s > 0 && bloom) {
        pulse.t += dt;
        const k = Math.max(0, 1 - pulse.t / pulse.d);
        bloom.intensity = bloomBase() + pulse.s * k * k;
        if (pulse.t >= pulse.d) { pulse.s = 0; bloom.intensity = bloomBase(); }
      }
      composer.render(dt);
    },
    /** Size in CSS pixels; the renderer's current pixel ratio (set by the render kit) decides the buffer size. */
    setSize(width, height) {
      size = { w: width, h: height };
      if (composer) composer.setSize(width, height, false);
    },
    setQuality(t) { gfx = { ...GRAPHICS_PRESETS[t] }; apply(); },
    setGraphics(g) { gfx = { ...g }; apply(); },
    bloomPulse: pulseFn,
  } satisfies PostPipeline;
};
