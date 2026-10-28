// Audio bus: WebAudio SFX (procedural) + looping music element routed through a gain node.
import type { AudioBus, EventBus, Faction, Role, SfxName } from '../contracts';
import { SIDE_FACTION } from '../contracts';
import { createSfx, type SfxPlayer } from './sfx';
import { createSamplePlayer, preloadSfx, type PlayOpts, type SamplePlayer } from './samples';
import { createScore, type Score } from './score';
import {
  AUDIO_CATEGORIES, categoryOf, getCategoryVolume, onCategoryChange, setCategoryVolume as storeCategoryVolume,
  type AudioCategory, type SfxCategory,
} from './categories';

export { AUDIO_CATEGORIES, CATEGORY_LABEL, categoryOf, getCategoryVolume, setCategoryVolume } from './categories';
export type { AudioCategory } from './categories';

/** The AudioBus plus the category mixer (not part of the lead-owned contract; the settings UI may cast to this). */
export interface AudioBusExt extends AudioBus {
  /** Per-category gain 0..1 (Music / Effects / Ambience / Interface), persisted in localStorage. */
  setCategoryVolume(cat: AudioCategory, v: number): void;
  getCategoryVolume(cat: AudioCategory): number;
}

/** Per-role weight of the sliding grind: heavy pieces pitch down and bite harder. */
const SLIDE_PITCH: Record<Role, number> = { pawn: 1.12, knight: 1.0, bishop: 1.06, rook: 0.86, queen: 0.95, king: 0.8 };
const SLIDE_VOL: Record<Role, number> = { pawn: 0.8, knight: 0.85, bishop: 0.8, rook: 1, queen: 0.95, king: 1 };

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

export function createAudioBus(): AudioBusExt {
  let ctx: AudioContext | null = null;
  let sfxOut: GainNode | null = null;
  let musicGain: GainNode | null = null;
  const catOut = new Map<SfxCategory, GainNode>();
  const synth = new Map<SfxCategory, SfxPlayer>();
  let stopCatSub: (() => void) | null = null;
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

  const musicTarget = () => (musicOn && !hidden ? musicVol * getCategoryVolume('music') * duck : 0);

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
    if (hide) { samples?.stopAllLoops(0.05); fadeTo(0, 0.2); stopMusic(); } else { void ctx?.resume().catch(() => {}); playMusic(); fadeTo(musicTarget(), 0.6); }
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
    if (fallback) synthFor(fallback)?.play(fallback, opts);
  }
  function synthFor(name: SfxName): SfxPlayer | null {
    const cat = categoryOf(name);
    let p = synth.get(cat);
    if (!p && ctx && catOut.get(cat)) { p = createSfx(ctx, catOut.get(cat)!); synth.set(cat, p); }
    return p ?? null;
  }
  const SHATTER_TIER: Record<Role, string> = { pawn: ':light', knight: '', bishop: '', rook: ':heavy', queen: ':heavy', king: ':heavy' };
  const HEAVY: ReadonlySet<Role> = new Set<Role>(['rook', 'queen', 'king']);

  let events: EventBus | null = null;
  const bus: AudioBusExt = {
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
        for (const c of AUDIO_CATEGORIES) {
          if (c === 'music') continue;
          const g = ctx.createGain();
          g.gain.value = getCategoryVolume(c);
          g.connect(sfxOut);
          catOut.set(c, g);
        }
        stopCatSub?.();
        stopCatSub = onCategoryChange((c, v) => {
          if (c === 'music') { fadeTo(musicTarget(), 0.15); return; }
          const g = catOut.get(c);
          if (g && ctx) g.gain.setTargetAtTime(v, ctx.currentTime, 0.02);
          if (c === 'ambience' && v <= 0.001) samples?.stopAllLoops(0.05);
        });
        musicGain = ctx.createGain();
        musicGain.gain.value = 0;
        musicGain.connect(comp);
        samples = createSamplePlayer(ctx, (c) => catOut.get(c)!);
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

    setCategoryVolume(cat, v) { storeCategoryVolume(cat, v); },
    getCategoryVolume(cat) { return getCategoryVolume(cat); },

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
      events = eb;
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
        const af = e.attackerFaction;
        samples?.warm([`hit:${e.attacker}:${af}`, `shatter:${df}${SHATTER_TIER[e.defender]}`, `attack:whoosh:${e.attacker}${af === 'rime' ? ':rime' : ''}`,
          `slide:${af}`, `slide:${af}:start`, `slide:${af}:stop`, `armour:hit:${af}`, `armour:hit:${af}:heavy`,
          ...(e.attacker === 'rook' || e.attacker === 'knight' || e.attacker === 'queen' ? [`land:${af}:s2`, `land:${af}:s3`] : []),
          ...(e.defender === 'pawn' ? [`shield:flash:${df}`, `shield:break:${df}`] : []),
          ...(e.attacker === 'pawn' ? [`shield:flash:${af}`] : [])]);
        if (e.attacker === 'knight') play(`gallop:${e.attackerFaction}`, null, { delay: 0.15, volume: 0.9 });
      });
      eb.on('capture:end', unduck);
      eb.on('game:start', () => { unduck(); samples?.warm(['check', 'mate', 'castle', 'promote:emberhold', 'promote:rime', 'kneel', 'slide:emberhold', 'slide:rime']); });
      eb.on('capture:impact', (e) => play(`hit:${e.attacker}:${e.attackerFaction}`, `impact:${e.defenderFaction}`, { volume: e.heavy ? 1 : 0.8 }));
      eb.on('capture:shatter', (e) => play(`shatter:${e.defenderFaction}${SHATTER_TIER[e.defender]}`, `shatter:${e.defenderFaction}`));
      eb.on('summon', (e) => bus.sfx(`summon:${e.faction}`));
      eb.on('spell', (e) => bus.sfx(`spell:${e.faction}`));
      eb.on('castle', () => bus.sfx('castle'));
      eb.on('promotion', (e) => { const f: Faction = SIDE_FACTION[e.side]; play(`promote:${f}`, 'promote', { pitch: f === 'rime' ? 1.12 : 1 }); });
      eb.on('check', () => bus.sfx('check'));
      eb.on('game:over', (e) => {
        if (e.reason === 'checkmate') bus.sfx('mate');
        else if (e.reason !== 'resign') play('sting:draw', null); // stalemate / draw: a hollow, unresolved horn
      });
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
      // ---- contract v1.4: piece slides, shields, armour, landings
      eb.on('move:slide', (e) => {
        if (!samples) return;
        const id = `${e.faction}:${e.role}`;
        if (e.phase === 'start') {
          const o = { speed: e.speed, pitch: SLIDE_PITCH[e.role], volume: SLIDE_VOL[e.role] };
          if (samples.hasLoop(id)) { samples.updateLoop(id, o); return; }
          if (samples.startLoop(id, `slide:${e.faction}`, o)) play(`slide:${e.faction}:start`, null, { volume: 0.7 * SLIDE_VOL[e.role], pitch: SLIDE_PITCH[e.role] });
          else samples.warm([`slide:${e.faction}`, `slide:${e.faction}:start`, `slide:${e.faction}:stop`]); // not decoded yet: silent this once
        } else if (samples.hasLoop(id)) {
          samples.stopLoop(id);
          play(`slide:${e.faction}:stop`, null, { volume: SLIDE_VOL[e.role], pitch: SLIDE_PITCH[e.role] });
        }
      });
      eb.on('shield:flash', (e) => play(`shield:flash:${e.faction}`, null));
      eb.on('shield:break', (e) => play(`shield:break:${e.faction}`, null));
      eb.on('armour:hit', (e) => play(`armour:hit:${e.faction}${e.heavy ? ':heavy' : ''}`, null));
      eb.on('land', (e) => {
        const s = Math.min(1, Math.max(0, e.strength));
        const tier = s < 0.34 ? 1 : s < 0.67 ? 2 : 3;
        play(`land:${e.faction}:s${tier}`, null, { volume: 0.75 + 0.25 * s });
      });
    },
  };
  // Diagnostics for sandbox/tests (not part of the AudioBus contract).
  Object.assign(bus, {
    /** Fetch + decode critical SFX during the loading screen (works before unlock). */
    preload: (report?: (fraction: number) => void) => preloadSfx(report),
    debug: () => ({
      kind: hasTrack ? 'file' : 'score', state: ctx?.state, paused: el?.paused, loop: el?.loop, currentTime: el?.currentTime ?? 0,
      scoreRunning: score?.running ?? false, ctxTime: ctx?.currentTime ?? 0, gain: musicGain?.gain.value ?? 0, duck, hidden,
      loops: samples?.loopCount() ?? 0,
      categories: Object.fromEntries(AUDIO_CATEGORIES.map((c) => [c, getCategoryVolume(c)])),
    }),
    /** Sandbox: drive the slide loop directly (same path as the move:slide event). */
    slide: (faction: Faction, role: Role, phase: 'start' | 'stop', speed: number) => {
      events?.emit('move:slide', { faction, role, phase, speed });
    },
  });
  return bus;
}

export { preloadSfx } from './samples';
