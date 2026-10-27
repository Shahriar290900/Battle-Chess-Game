// Audio bus: WebAudio SFX (procedural) + looping music element routed through a gain node.
import type { AudioBus, EventBus, Faction, Role, SfxName } from '../contracts';
import { SIDE_FACTION } from '../contracts';
import { createSfx, type SfxPlayer } from './sfx';
import { createSamplePlayer, preloadSfx, type PlayOpts, type SamplePlayer } from './samples';
import { createScore, type Score } from './score';

const DB_NAME = 'battle-chess';
const STORE = 'audio';
const KEY = 'custom-track';
const DUCK = 0.5; // about -6 dB
const FADE = 1.2;

function idb(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, 1);
    req.onupgradeneeded = () => req.result.createObjectStore(STORE);
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}
async function idbGet(): Promise<Blob | undefined> {
  try {
    const db = await idb();
    return await new Promise((res, rej) => {
      const r = db.transaction(STORE).objectStore(STORE).get(KEY);
      r.onsuccess = () => res(r.result as Blob | undefined);
      r.onerror = () => rej(r.error);
    });
  } catch { return undefined; }
}
async function idbPut(blob: Blob): Promise<void> {
  try {
    const db = await idb();
    await new Promise<void>((res, rej) => {
      const tx = db.transaction(STORE, 'readwrite');
      tx.objectStore(STORE).put(blob, KEY);
      tx.oncomplete = () => res();
      tx.onerror = () => rej(tx.error);
    });
  } catch (e) { console.warn('[audio] could not persist custom track', e); }
}

/** Bundled theme exists? (Vite dev server answers 200 text/html for missing files, so check the type.) */
async function bundledThemeUrl(): Promise<string | null> {
  const url = import.meta.env.BASE_URL + 'audio/theme.mp3';
  try {
    const r = await fetch(url, { method: 'HEAD' });
    const type = r.headers.get('content-type') ?? '';
    if (r.ok && !type.includes('text/html')) return url;
  } catch { /* offline / blocked */ }
  return null;
}

export function createAudioBus(): AudioBus {
  let ctx: AudioContext | null = null;
  let sfxOut: GainNode | null = null;
  let musicGain: GainNode | null = null;
  let sfxPlayer: SfxPlayer | null = null;
  let samples: SamplePlayer | null = null;
  let el: HTMLAudioElement | null = null;
  let objectUrl: string | null = null;
  let hasTrack = false;
  let musicOn = true;
  let musicVol = 0.55;
  let sfxVol = 0.8;
  let duck = 1;
  let hidden = false;
  let sourceReady: Promise<void> | null = null;
  let unlocked = false;
  let score: Score | null = null;
  let duckTimer: ReturnType<typeof setTimeout> | null = null;

  const musicTarget = () => (musicOn && !hidden ? musicVol * duck : 0);

  function fadeTo(target: number, secs = FADE): void {
    if (!ctx || !musicGain) return;
    const g = musicGain.gain;
    const now = ctx.currentTime;
    g.cancelScheduledValues(now);
    g.setValueAtTime(g.value, now);
    g.linearRampToValueAtTime(target, now + secs);
  }

  function ensureElement(): HTMLAudioElement | null {
    if (!ctx || !musicGain) return null;
    if (!el) {
      el = new Audio();
      el.loop = true;
      el.preload = 'auto';
      el.crossOrigin = 'anonymous';
      ctx.createMediaElementSource(el).connect(musicGain);
    }
    return el;
  }

  function setSource(url: string, revoke: boolean): void {
    const a = ensureElement();
    if (!a) return;
    if (objectUrl) URL.revokeObjectURL(objectUrl);
    objectUrl = revoke ? url : null;
    a.src = url;
    hasTrack = true;
  }

  async function resolveSource(): Promise<void> {
    const bundled = await bundledThemeUrl();
    if (bundled) { setSource(bundled, false); return; }
    const blob = await idbGet();
    if (blob) setSource(URL.createObjectURL(blob), true);
  }

  /** Start whichever source is active: file track if present, else the generated score. */
  function playMusic(): void {
    if (!ctx || !musicOn || hidden) return;
    if (ctx.state !== 'running') void ctx.resume().catch(() => {});
    if (hasTrack && el) {
      score?.stop();
      if (el.paused) el.play().catch(() => { /* retried on next gesture/event */ });
      fadeTo(musicTarget());
    } else if (score) {
      score.start();
      fadeTo(musicTarget());
    }
  }

  function stopMusic(): void {
    score?.stop();
    el?.pause();
  }

  function onVisibility(hide: boolean): void {
    hidden = hide;
    if (!ctx) return;
    if (hide) { fadeTo(0, 0.2); stopMusic(); } else { void ctx?.resume().catch(() => {}); playMusic(); fadeTo(musicTarget(), 0.6); }
  }

  const d = typeof document !== 'undefined' ? document : null;
  d?.addEventListener('visibilitychange', () => onVisibility(d.hidden));
  if (typeof window !== 'undefined') {
    window.addEventListener('bc:app-pause', () => onVisibility(true));
    window.addEventListener('bc:app-resume', () => onVisibility(false));
  }

  /** Sample first (designed CC0 layers); procedural synth only if the file is missing or still decoding. */
  function play(key: string, fallback: SfxName | null, opts?: PlayOpts): void {
    if (samples?.play(key, opts)) return;
    if (fallback) sfxPlayer?.play(fallback, opts);
  }
  const SHATTER_TIER: Record<Role, string> = { pawn: ':light', knight: '', bishop: '', rook: ':heavy', queen: ':heavy', king: ':heavy' };
  const HEAVY: ReadonlySet<Role> = new Set<Role>(['rook', 'queen', 'king']);

  const bus: AudioBus = {
    async unlock() {
      if (!unlocked) {
        unlocked = true;
        const AC = window.AudioContext ?? (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
        ctx = new AC();
        const comp = ctx.createDynamicsCompressor();
        comp.connect(ctx.destination);
        sfxOut = ctx.createGain();
        sfxOut.gain.value = sfxVol;
        sfxOut.connect(comp);
        musicGain = ctx.createGain();
        musicGain.gain.value = 0;
        musicGain.connect(comp);
        sfxPlayer = createSfx(ctx, sfxOut);
        samples = createSamplePlayer(ctx, sfxOut);
        score = createScore(ctx, musicGain);
        sourceReady = resolveSource();
      }
      if (ctx && ctx.state !== 'running') await ctx.resume().catch(() => {});
      await sourceReady;
      playMusic();
    },

    sfx(name: SfxName, opts) {
      play(name, name, opts);
    },

    setMusicEnabled(on) {
      musicOn = on;
      if (on) { playMusic(); fadeTo(musicTarget()); }
      else { fadeTo(0, 0.5); setTimeout(() => { if (!musicOn) stopMusic(); }, 600); }
    },

    setVolumes(music, sfx) {
      musicVol = Math.min(1, Math.max(0, music));
      sfxVol = Math.min(1, Math.max(0, sfx));
      if (sfxOut && ctx) sfxOut.gain.setTargetAtTime(sfxVol, ctx.currentTime, 0.02);
      fadeTo(musicTarget(), 0.15);
    },

    /** True only for file tracks (theme / custom); the generated score does not count. */
    hasMusic: () => hasTrack,

    async loadCustomTrack(file) {
      await idbPut(file);
      if (!ctx) { return; } // picked up on unlock()
      await sourceReady;
      // A bundled theme wins only if present; an explicit user choice overrides it.
      setSource(URL.createObjectURL(file), true);
      playMusic();
    },

    attach(eb: EventBus) {
      eb.on('move:step', (e) => {
        const key = e.role === 'knight' ? `step:knight:${e.faction}` : HEAVY.has(e.role) ? `step:heavy:${e.faction}` : `move:step:${e.faction}`;
        play(key, `move:step:${e.faction}`);
      });
      eb.on('attack:whoosh', (e) => play(`attack:whoosh:${e.role}${e.faction === 'rime' ? ':rime' : ''}`, `attack:whoosh:${e.role}`));
      const unduck = () => { if (duckTimer) clearTimeout(duckTimer); duckTimer = null; duck = 1; fadeTo(musicTarget(), 0.9); };
      eb.on('capture:begin', (e) => {
        duck = DUCK; fadeTo(musicTarget(), 0.4); if (duckTimer) clearTimeout(duckTimer); duckTimer = setTimeout(unduck, 25000);
        // Decode the hit + shatter now (seconds ahead of the blow) so they never fall back to the synth.
        const df = e.defenderFaction;
        samples?.warm([`hit:${e.attacker}:${e.attackerFaction}`, `shatter:${df}${SHATTER_TIER[e.defender]}`, `attack:whoosh:${e.attacker}${e.attackerFaction === 'rime' ? ':rime' : ''}`]);
        if (e.attacker === 'knight') play(`gallop:${e.attackerFaction}`, null, { delay: 0.15, volume: 0.9 });
      });
      eb.on('capture:end', unduck);
      eb.on('game:start', () => { unduck(); samples?.warm(['check', 'mate', 'castle', 'promote:emberhold', 'promote:rime', 'kneel']); });
      eb.on('capture:impact', (e) => play(`hit:${e.attacker}:${e.attackerFaction}`, `impact:${e.defenderFaction}`, { volume: e.heavy ? 1 : 0.8 }));
      eb.on('capture:shatter', (e) => play(`shatter:${e.defenderFaction}${SHATTER_TIER[e.defender]}`, `shatter:${e.defenderFaction}`));
      eb.on('summon', (e) => bus.sfx(`summon:${e.faction}`));
      eb.on('spell', (e) => bus.sfx(`spell:${e.faction}`));
      eb.on('castle', () => bus.sfx('castle'));
      eb.on('promotion', (e) => { const f: Faction = SIDE_FACTION[e.side]; play(`promote:${f}`, 'promote', { pitch: f === 'rime' ? 1.12 : 1 }); });
      eb.on('check', () => bus.sfx('check'));
      eb.on('game:over', (e) => { if (e.reason === 'checkmate') bus.sfx('mate'); });
      eb.on('ui:select', () => bus.sfx('ui:select'));
      eb.on('ui:click', () => bus.sfx('ui:click'));
      // Combat flavour events (emitted by cinematics/fx); silent on the synth fallback.
      eb.on('clash', (e) => play(`clash:${e.attackerFaction}${e.heavy ? ':heavy' : ''}`, `impact:${e.attackerFaction}`, { volume: e.heavy ? 1 : 0.9 }));
      eb.on('weapon:drop', (e) => play(`drop:${e.faction}`, null));
      eb.on('debris:impact', (e) => {
        const tier = e.strength < 0.34 ? 1 : e.strength < 0.67 ? 2 : 3;
        play(`debris:${e.faction}:s${tier}`, null, { volume: 0.7 + 0.3 * Math.min(1, Math.max(0, e.strength)) });
      });
      eb.on('taunt', (e) => play(e.role === 'knight' ? `rear:${e.faction}` : `taunt:${e.faction}`, null));
      eb.on('surrender', () => play('kneel', null));
    },
  };
  // Diagnostics for sandbox/tests (not part of the AudioBus contract).
  Object.assign(bus, {
    /** Fetch + decode critical SFX during the loading screen (works before unlock). */
    preload: (report?: (fraction: number) => void) => preloadSfx(report),
    debug: () => ({
      kind: hasTrack ? 'file' : 'score', state: ctx?.state, paused: el?.paused, loop: el?.loop, currentTime: el?.currentTime ?? 0,
      scoreRunning: score?.running ?? false, ctxTime: ctx?.currentTime ?? 0, gain: musicGain?.gain.value ?? 0, duck, hidden,
    }),
  });
  return bus;
}

export { preloadSfx } from './samples';
