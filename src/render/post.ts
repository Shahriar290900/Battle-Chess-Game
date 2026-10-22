import {
  BloomEffect, EffectComposer, EffectPass, KernelSize, RenderPass, SMAAEffect, SMAAPreset, ToneMappingEffect, ToneMappingMode, VignetteEffect,
} from 'postprocessing';
import { AgXToneMapping, ShaderChunk, HalfFloatType, NeutralToneMapping, NoToneMapping, UnsignedByteType } from 'three';
import { GRAPHICS_PRESETS, type CreatePost, type GraphicsSettings, type PostPipeline } from '../contracts';
import { registerBloomPulse } from '../fx/bloomBus';

/**
 * Composer pipeline: Render -> EffectPass[Bloom, ToneMapping, Vignette] -> (SMAA pass on High only).
 * The whole chain is rebuilt on every tier change (never toggles pass flags), so the last pass always renders to screen.
 * Falls back to plain renderer.render() if the composer cannot be built.
 */
// Half-float HDR buffers overflow to Inf on very bright specular highlights (smooth ice/bronze under strong lights);
// Inf/NaN then smears black across the whole frame through the bloom blur. Clamp scene colour before it is written.
// Must run before materials compile (createPost is called at start-up).
const CLAMP_FROM = 'gl_FragColor = vec4( outgoingLight, diffuseColor.a );';
if (ShaderChunk.opaque_fragment.includes(CLAMP_FROM)) {
  ShaderChunk.opaque_fragment = ShaderChunk.opaque_fragment.replace(CLAMP_FROM, 'gl_FragColor = vec4( min( max( outgoingLight, vec3( 0.0 ) ), vec3( 32.0 ) ), diffuseColor.a );');
}

export const createPost: CreatePost = (renderer, scene, camera, tier) => {
  const gl = renderer.getContext();
  const isGL2 = typeof WebGL2RenderingContext !== 'undefined' && gl instanceof WebGL2RenderingContext;
  const ext = renderer.extensions;
  // HalfFloat render targets need EXT_color_buffer_float or EXT_color_buffer_half_float; otherwise stay 8-bit.
  const halfOk = isGL2 && (ext.has('EXT_color_buffer_float') || ext.has('EXT_color_buffer_half_float'));

  // Tone mapping moves into the composer so HDR emissive values survive until bloom/tonemap.
  const tm = renderer.toneMapping;
  const tmMode = tm === AgXToneMapping ? ToneMappingMode.AGX : tm === NeutralToneMapping ? ToneMappingMode.NEUTRAL : ToneMappingMode.ACES_FILMIC;
  renderer.toneMapping = NoToneMapping;

  let composer: EffectComposer | null = null;
  let bloom: BloomEffect | null = null;
  let size: { w: number; h: number } | null = null;
  let gfx: GraphicsSettings = { ...GRAPHICS_PRESETS[tier] };
  let built = { bloom: false, aa: false, lite: false };
  let pulse = { s: 0, d: 0, t: 0 };
  const bloomBase = () => (gfx.preset === 'low' ? 0.7 : gfx.preset === 'medium' ? 0.8 : 0.9);
  const DPR_CAP = 2;

  const dispose = () => { try { composer?.dispose(); } catch { /* ignore */ } composer = null; bloom = null; };

  const applyResolution = () => {
    const scale = Math.min(1, Math.max(0.5, gfx.resolutionScale));
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, DPR_CAP) * scale);
    if (size) { if (composer) composer.setSize(size.w, size.h, false); else renderer.setSize(size.w, size.h, false); }
  };

  // The whole chain is rebuilt whenever bloom / SMAA / bloom-cost class change, so the last pass always renders to screen.
  const build = () => {
    dispose();
    const lite = gfx.preset === 'low' || gfx.resolutionScale < 0.8;
    const c = new EffectComposer(renderer, { frameBufferType: halfOk ? HalfFloatType : UnsignedByteType, multisampling: 0 });
    c.addPass(new RenderPass(scene, camera));
    const effects: any[] = [];
    let b: BloomEffect | null = null;
    if (gfx.bloom) {
      b = new BloomEffect({
        intensity: bloomBase(), luminanceThreshold: 0.85, luminanceSmoothing: 0.25, mipmapBlur: true, radius: 0.7,
        levels: lite ? 4 : 6, kernelSize: KernelSize.MEDIUM,
      });
      b.resolution.scale = lite ? 0.5 : 1;
      effects.push(b);
    }
    effects.push(new ToneMappingEffect({ mode: tmMode }), new VignetteEffect({ offset: 0.32, darkness: 0.55 }));
    c.addPass(new EffectPass(camera, ...effects));
    if (gfx.antialias) c.addPass(new EffectPass(camera, new SMAAEffect({ preset: SMAAPreset.MEDIUM })));
    composer = c; bloom = b;
    built = { bloom: gfx.bloom, aa: gfx.antialias, lite };
    if (size) c.setSize(size.w, size.h, false);
  };

  const safeBuild = () => {
    try { build(); } catch (err) {
      console.warn('[post] composer unavailable, falling back to direct render', err);
      dispose();
      renderer.toneMapping = tm; // direct render needs its own tone mapping back
    }
  };
  const apply = () => {
    const lite = gfx.preset === 'low' || gfx.resolutionScale < 0.8;
    if (!composer || built.bloom !== gfx.bloom || built.aa !== gfx.antialias || built.lite !== lite) { applyResolution(); safeBuild(); } else { applyResolution(); if (bloom) bloom.intensity = bloomBase(); }
  };
  applyResolution();
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
    setSize(width, height) {
      size = { w: width, h: height };
      if (composer) composer.setSize(width, height, false); else renderer.setSize(width, height, false);
    },
    setQuality(t) { gfx = { ...GRAPHICS_PRESETS[t] }; apply(); },
    setGraphics(g) { gfx = { ...g }; apply(); },
    bloomPulse: pulseFn,
  } satisfies PostPipeline;
};
