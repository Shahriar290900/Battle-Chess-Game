// Sample-based SFX: lazy manifest, byte-budgeted AudioBuffer cache (LRU + pinned), pitch/gain jitter,
// priority-aware voice limiting and ducking. Pure WebAudio; no dependency on the music code.
export interface SfxEntry {
  files: string[];
  /** Linear mix gain (loudness-normalised files; this is the in-game balance). */
  gain?: number;
  /** 3 = cinematic hit (ducks low priority), 2 = normal, 1 = ambience-level (steps, UI, debris). */
  priority?: 1 | 2 | 3;
  /** Decode during the loading screen and keep resident. */
  preload?: boolean;
  /** Minimum seconds between two plays of this entry. */
  cooldown?: number;
}
interface Manifest { version: number; entries: Record<string, SfxEntry> }

export interface PlayOpts { volume?: number; pitch?: number; delay?: number }
export interface SamplePlayer {
  /** True if a sample voice was started (false: not ready / unknown key, caller should fall back to synth). */
  play(key: string, opts?: PlayOpts): boolean;
  /** Start fetching/decoding the files for these keys (no sound). */
  warm(keys: string[]): void;
  has(key: string): boolean;
}

const BASE = (typeof import.meta !== 'undefined' && import.meta.env?.BASE_URL) || '/';
const DIR = BASE + 'audio/sfx/';
const JITTER = 0.04;
const MAX_VOICES = 18;
/** Decoded PCM budget for non-pinned buffers (mono float32 @ 44.1 kHz ≈ 176 kB/s). */
const CACHE_BYTES = 22 * 1024 * 1024;

// ------------------------------------------------------------------ shared module state
let manifest: Manifest | null = null;
let manifestPromise: Promise<Manifest | null> | null = null;
const buffers = new Map<string, AudioBuffer>(); // insertion order = LRU order
const pinned = new Set<string>();
const inflight = new Map<string, Promise<AudioBuffer | null>>();
const failed = new Set<string>();
let decodeCtx: BaseAudioContext | null = null;
let liveCtx: BaseAudioContext | null = null;
let cacheBytes = 0;

const bytesOf = (b: AudioBuffer) => b.length * b.numberOfChannels * 4;

function decoder(): BaseAudioContext | null {
  if (liveCtx) return liveCtx;
  if (!decodeCtx && typeof OfflineAudioContext !== 'undefined') {
    try { decodeCtx = new OfflineAudioContext(1, 1, 44100); } catch { /* ignore */ }
  }
  return decodeCtx;
}

export function loadManifest(): Promise<Manifest | null> {
  if (!manifestPromise) {
    manifestPromise = fetch(DIR + 'manifest.json')
      .then((r) => (r.ok && !(r.headers.get('content-type') ?? '').includes('text/html') ? (r.json() as Promise<Manifest>) : null))
      .then((m) => { manifest = m; return m; })
      .catch(() => null);
  }
  return manifestPromise;
}

function touch(file: string, buf: AudioBuffer): void {
  buffers.delete(file);
  buffers.set(file, buf);
}

function evict(): void {
  if (cacheBytes <= CACHE_BYTES) return;
  for (const [file, buf] of buffers) {
    if (cacheBytes <= CACHE_BYTES) break;
    if (pinned.has(file)) continue;
    buffers.delete(file);
    cacheBytes -= bytesOf(buf);
  }
}

function ensure(file: string, pin = false): Promise<AudioBuffer | null> {
  if (pin) pinned.add(file);
  const have = buffers.get(file);
  if (have) { touch(file, have); return Promise.resolve(have); }
  if (failed.has(file)) return Promise.resolve(null);
  let p = inflight.get(file);
  if (!p) {
    p = (async () => {
      try {
        const r = await fetch(DIR + file);
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        const ab = await r.arrayBuffer();
        const dc = decoder();
        if (!dc) throw new Error('no decoder');
        const buf = await dc.decodeAudioData(ab);
        buffers.set(file, buf);
        cacheBytes += bytesOf(buf);
        evict();
        return buf;
      } catch (e) {
        failed.add(file);
        console.warn('[audio] sample failed', file, e);
        return null;
      } finally {
        inflight.delete(file);
      }
    })();
    inflight.set(file, p);
  }
  return p;
}

/**
 * Fetch + decode the critical hits during the loading screen (works before the AudioContext is unlocked,
 * because an OfflineAudioContext decodes to a context-independent AudioBuffer). Never rejects; capped at `maxMs`.
 */
export async function preloadSfx(report?: (fraction: number) => void, maxMs = 9000): Promise<void> {
  const work = (async () => {
    const m = await loadManifest();
    if (!m) { report?.(1); return; }
    const files = [...new Set(Object.values(m.entries).filter((e) => e.preload).map((e) => e.files[0]))];
    let done = 0;
    const queue = files.slice();
    const worker = async () => {
      for (let f = queue.shift(); f; f = queue.shift()) {
        await ensure(f, true);
        report?.(++done / files.length);
      }
    };
    await Promise.all([worker(), worker(), worker(), worker()]);
  })();
  await Promise.race([work, new Promise<void>((r) => setTimeout(r, maxMs))]);
  report?.(1);
}

// ------------------------------------------------------------------ player
interface Voice { src: AudioBufferSourceNode; priority: number; t0: number; key: string }

export function createSamplePlayer(ctx: AudioContext, out: AudioNode): SamplePlayer {
  liveCtx = ctx;
  void loadManifest();

  // Two buses so cinematic hits can duck the low-priority layer (footsteps, UI, debris).
  const hi = ctx.createGain();
  const lo = ctx.createGain();
  hi.connect(out);
  lo.connect(out);
  const voices = new Set<Voice>();
  const lastPlay = new Map<string, number>();
  const lastIdx = new Map<string, number>();
  let duckUntil = 0;

  function duckLow(secs: number): void {
    const now = ctx.currentTime;
    const g = lo.gain;
    g.cancelScheduledValues(now);
    g.setValueAtTime(g.value, now);
    g.linearRampToValueAtTime(0.3, now + 0.02);
    g.setValueAtTime(0.3, now + secs);
    g.linearRampToValueAtTime(1, now + secs + 0.5);
    duckUntil = now + secs + 0.3;
  }

  function steal(priority: number): boolean {
    let victim: Voice | null = null;
    for (const v of voices) {
      if (v.priority > priority) continue;
      if (!victim || v.priority < victim.priority || (v.priority === victim.priority && v.t0 < victim.t0)) victim = v;
    }
    if (!victim) return false;
    try { victim.src.stop(); } catch { /* already ended */ }
    voices.delete(victim);
    return true;
  }

  function pick(key: string, e: SfxEntry): string {
    const n = e.files.length;
    if (n === 1) return e.files[0];
    let i = Math.floor(Math.random() * n);
    if (i === lastIdx.get(key)) i = (i + 1 + Math.floor(Math.random() * (n - 1))) % n;
    lastIdx.set(key, i);
    return e.files[i];
  }

  return {
    has: (key) => !!manifest?.entries[key],

    warm(keys) {
      if (!manifest) return;
      for (const k of keys) { const e = manifest.entries[k]; if (e) for (const f of e.files) void ensure(f); }
    },

    play(key, opts) {
      const e = manifest?.entries[key];
      if (!e || ctx.state !== 'running') return false;
      const now = ctx.currentTime;
      if (now - (lastPlay.get(key) ?? -9) < (e.cooldown ?? 0.03)) return true; // swallowed, not a failure
      const file = pick(key, e);
      const buf = buffers.get(file);
      if (!buf) { void ensure(file); return false; }
      touch(file, buf);
      const priority = e.priority ?? 2;
      // Footsteps/UI are skipped outright while a big hit's tail is still ducking them.
      if (priority === 1 && now < duckUntil - 0.35) return true;
      if (voices.size >= MAX_VOICES && !steal(priority)) return true;

      const src = ctx.createBufferSource();
      src.buffer = buf;
      src.playbackRate.value = (opts?.pitch ?? 1) * (1 + (Math.random() * 2 - 1) * JITTER);
      const g = ctx.createGain();
      g.gain.value = (e.gain ?? 1) * (opts?.volume ?? 1) * (1 - Math.random() * 0.08);
      src.connect(g).connect(priority === 1 ? lo : hi);
      const v: Voice = { src, priority, t0: now, key };
      voices.add(v);
      src.onended = () => { voices.delete(v); try { g.disconnect(); } catch { /* ok */ } };
      const when = now + 0.005 + Math.max(0, opts?.delay ?? 0);
      src.start(when);
      lastPlay.set(key, now);
      if (priority === 3) duckLow(Math.min(1.4, buf.duration * 0.5 + 0.2));
      return true;
    },
  };
}
