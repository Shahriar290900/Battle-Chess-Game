// STUB (lead) — replaced by platform-audio.
import type { AudioBus } from '../contracts';

export function createAudioBus(): AudioBus {
  return {
    async unlock() {}, sfx() {}, setMusicEnabled() {}, setVolumes() {},
    hasMusic: () => false, async loadCustomTrack() {}, attach() {},
  };
}
