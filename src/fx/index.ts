// STUB (lead) — replaced by vfx-shaders. Every effect is a no-op; promises resolve immediately.
import type { FxApi } from '../contracts';

export function createFx(): FxApi {
  const done = async () => {};
  return {
    init: done, setQuality() {}, emit() {}, shockwave() {}, decal() {}, aura() {}, flash() {}, mist() {}, update() {},
    async shatter(o) { o.fragments.parent?.remove(o.fragments); o.onDone?.(); },
    iceSpikes: done, sweep: done, column: done,
    async dissolve(obj) { obj.visible = false; },
    trail() { return { stop() {} }; },
  };
}
