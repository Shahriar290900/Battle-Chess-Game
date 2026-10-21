// STUB (lead) — replaced by platform-audio.
import type { PlatformApi } from '../contracts';

export function createPlatform(): PlatformApi {
  const isMobile = /Android|iPhone|iPad|Mobile/i.test(navigator.userAgent);
  return { isNative: false, isMobile, async init() {}, onBack() {} };
}
