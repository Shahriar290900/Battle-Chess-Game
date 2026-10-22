// Tiny registry so fx.flash() can drive the post pipeline's bloom pulse without importing render code.
type PulseFn = (strength: number, duration: number) => void;
let impl: PulseFn | null = null;

/** Called by src/render/post.ts when a pipeline is created. */
export function registerBloomPulse(fn: PulseFn | null): void { impl = fn; }
/** Used by fx.flash and friends. No-op until a pipeline registered. */
export function triggerBloomPulse(strength: number, duration: number): void { impl?.(strength, duration); }
