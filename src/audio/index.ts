// Audio bus: WebAudio SFX (procedural) + looping music element routed through a gain node.
import type { AudioBus, EventBus, SfxName } from '../contracts';
import { SIDE_FACTION } from '../contracts';
import { createSfx, type SfxPlayer } from './sfx';

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

  function playMusic(): void {
    if (!el || !hasTrack || !musicOn || hidden) return;
    el.play().then(() => fadeTo(musicTarget())).catch(() => { /* blocked until a gesture */ });
  }

  function onVisibility(hide: boolean): void {
    hidden = hide;
    if (!el) return;
    if (hide) { fadeTo(0, 0.2); el.pause(); } else { playMusic(); fadeTo(musicTarget(), 0.6); }
  }

  const d = typeof document !== 'undefined' ? document : null;
  d?.addEventListener('visibilitychange', () => onVisibility(d.hidden));
  if (typeof window !== 'undefined') {
    window.addEventListener('bc:app-pause', () => onVisibility(true));
    window.addEventListener('bc:app-resume', () => onVisibility(false));
  }

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
        sourceReady = resolveSource();
      }
      if (ctx && ctx.state !== 'running') await ctx.resume().catch(() => {});
      await sourceReady;
      playMusic();
    },

    sfx(name: SfxName, opts) {
      sfxPlayer?.play(name, opts);
    },

    setMusicEnabled(on) {
      musicOn = on;
      if (on) { playMusic(); fadeTo(musicTarget()); }
      else { fadeTo(0, 0.5); const a = el; setTimeout(() => { if (!musicOn) a?.pause(); }, 550); }
    },

    setVolumes(music, sfx) {
      musicVol = Math.min(1, Math.max(0, music));
      sfxVol = Math.min(1, Math.max(0, sfx));
      if (sfxOut && ctx) sfxOut.gain.setTargetAtTime(sfxVol, ctx.currentTime, 0.02);
      fadeTo(musicTarget(), 0.15);
    },

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
      eb.on('move:step', (e) => bus.sfx(`move:step:${e.faction}`));
      eb.on('attack:whoosh', (e) => bus.sfx(`attack:whoosh:${e.role}`));
      eb.on('capture:begin', () => { duck = DUCK; fadeTo(musicTarget(), 0.4); });
      eb.on('capture:end', () => { duck = 1; fadeTo(musicTarget(), 0.9); });
      eb.on('capture:impact', (e) => bus.sfx(`impact:${e.defenderFaction}`, { volume: e.heavy ? 1 : 0.75 }));
      eb.on('capture:shatter', (e) => bus.sfx(`shatter:${e.defenderFaction}`));
      eb.on('summon', (e) => bus.sfx(`summon:${e.faction}`));
      eb.on('spell', (e) => bus.sfx(`spell:${e.faction}`));
      eb.on('castle', () => bus.sfx('castle'));
      eb.on('promotion', (e) => bus.sfx('promote', { pitch: SIDE_FACTION[e.side] === 'rime' ? 1.12 : 1 }));
      eb.on('check', () => bus.sfx('check'));
      eb.on('game:over', (e) => { if (e.reason === 'checkmate') bus.sfx('mate'); });
      eb.on('ui:select', () => bus.sfx('ui:select'));
      eb.on('ui:click', () => bus.sfx('ui:click'));
    },
  };
  return bus;
}
