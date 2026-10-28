import { createAudioBus } from '../src/audio';
import { bus as events } from '../src/contracts';
import type { Faction, Role, SfxName } from '../src/contracts';

import { AUDIO_CATEGORIES, CATEGORY_LABEL } from '../src/audio';

const audio = createAudioBus();
audio.attach(events);
(window as unknown as { audio: unknown }).audio = audio;

const dbg = () => (audio as unknown as { debug(): { loops: number } }).debug();
const F: Faction[] = ['emberhold', 'rime'];
const R: Role[] = ['pawn', 'knight', 'bishop', 'rook', 'queen', 'king'];
const names: SfxName[] = [
  ...F.map((f) => `move:step:${f}` as const), ...R.map((r) => `attack:whoosh:${r}` as const),
  ...F.map((f) => `impact:${f}` as const), ...F.map((f) => `shatter:${f}` as const),
  ...F.map((f) => `summon:${f}` as const), ...F.map((f) => `spell:${f}` as const),
  'check', 'mate', 'ui:click', 'ui:select', 'castle', 'promote',
  ...F.map((f) => `slide:${f}` as const), ...F.map((f) => `shield:flash:${f}` as const), ...F.map((f) => `shield:break:${f}` as const),
  ...F.map((f) => `armour:hit:${f}` as const), ...F.map((f) => `land:${f}` as const),
];

const app = document.getElementById('app')!;
const BASE = import.meta.env.BASE_URL;
interface ManEntry { files: string[]; gain: number; priority: number }
const logEl = document.createElement('pre');
logEl.id = 'log';
const btn = (label: string, fn: () => void) => {
  const b = document.createElement('button');
  b.textContent = label;
  b.onclick = async () => { await audio.unlock(); fn(); };
  app.appendChild(b);
};
for (const n of names) btn(n, () => audio.sfx(n));
app.appendChild(document.createElement('hr'));
let on = true;
btn('music toggle', () => { on = !on; audio.setMusicEnabled(on); status(); });
btn('duck (capture:begin)', () => events.emit('capture:begin', { attacker: 'rook', defender: 'pawn', attackerFaction: 'emberhold', defenderFaction: 'rime', square: 'e4' }));
btn('unduck (capture:end)', () => events.emit('capture:end', { square: 'e4' }));
// ---- category mixer (Music / Effects / Ambience / Interface)
app.appendChild(document.createElement('hr'));
const mixer = document.createElement('div');
mixer.id = 'mixer';
for (const c of AUDIO_CATEGORIES) {
  const lab = document.createElement('label');
  lab.style.marginRight = '14px';
  const r = document.createElement('input');
  r.type = 'range'; r.min = '0'; r.max = '1'; r.step = '0.05'; r.id = `cat-${c}`;
  r.value = String(audio.getCategoryVolume(c));
  r.oninput = async () => { await audio.unlock(); audio.setCategoryVolume(c, Number(r.value)); };
  lab.append(`${CATEGORY_LABEL[c]} `, r);
  mixer.appendChild(lab);
}
app.appendChild(mixer);

// ---- slide test: faction / role / speed slider drive the same move:slide events the cinematics emit
app.appendChild(document.createElement('hr'));
const slideBox = document.createElement('div');
slideBox.id = 'slide-test';
const sel = <T extends string>(id: string, opts: readonly T[]) => {
  const e = document.createElement('select');
  e.id = id;
  for (const o of opts) e.add(new Option(o, o));
  slideBox.appendChild(e);
  return e;
};
const selF = sel('slide-faction', F);
const selR = sel('slide-role', R);
const speed = document.createElement('input');
speed.type = 'range'; speed.min = '0.3'; speed.max = '6'; speed.step = '0.1'; speed.value = '2.2'; speed.id = 'slide-speed';
const speedLabel = document.createElement('span');
const sync = () => { speedLabel.textContent = ` ${Number(speed.value).toFixed(1)} sq/s `; };
sync();
const send = (phase: 'start' | 'stop') => events.emit('move:slide', { faction: selF.value as Faction, role: selR.value as Role, phase, speed: Number(speed.value) });
speed.oninput = async () => { sync(); if (dbg().loops > 0) send('start'); };
slideBox.append(speed, speedLabel);
const sbtn = (label: string, fn: () => void) => { const b = document.createElement('button'); b.textContent = label; b.onclick = async () => { await audio.unlock(); fn(); }; slideBox.appendChild(b); };
sbtn('slide start', () => send('start'));
sbtn('slide stop', () => send('stop'));
sbtn('glide 1.5 s', () => { send('start'); setTimeout(() => send('stop'), 1500); });
sbtn('forget stop (6 s failsafe)', () => send('start'));
sbtn('fight sequence', () => {
  const seq: Array<[number, () => void]> = [
    [0, () => send('start')], [900, () => send('stop')],
    [1100, () => events.emit('shield:flash', { faction: 'rime' })], [1250, () => events.emit('armour:hit', { faction: 'emberhold', heavy: false })],
    [1500, () => events.emit('land', { faction: 'emberhold', role: 'rook', strength: 0.9 })],
    [1700, () => events.emit('shield:break', { faction: 'rime' })],
  ];
  for (const [t, fn] of seq) setTimeout(fn, t);
});
app.appendChild(slideBox);
(window as unknown as { slideProbe: () => unknown }).slideProbe = () => dbg();

const file = document.createElement('input');
file.type = 'file'; file.accept = 'audio/*';
file.onchange = async () => { if (file.files?.[0]) { await audio.unlock(); await audio.loadCustomTrack(file.files[0]); status(); } };
app.appendChild(file);
const st = document.createElement('p');
app.appendChild(st);
function status() { st.textContent = `hasMusic=${audio.hasMusic()} enabled=${on}`; }
status();

// ---- every manifest key (sample-based SFX), plus a probe that fetches + decodes every file
app.appendChild(document.createElement('hr'));
const sampleBox = document.createElement('div');
app.appendChild(sampleBox);
app.appendChild(logEl);
async function loadManifest(): Promise<Record<string, ManEntry>> {
  const r = await fetch(BASE + 'audio/sfx/manifest.json');
  return (await r.json()).entries as Record<string, ManEntry>;
}
void loadManifest().then((m) => {
  const keys = Object.keys(m).sort();
  const h = document.createElement('h3');
  h.textContent = `${keys.length} sample keys`;
  sampleBox.appendChild(h);
  for (const k of keys) {
    const b = document.createElement('button');
    b.textContent = `${k} (${m[k].files.length})`;
    b.onclick = async () => { await audio.unlock(); audio.sfx(k as SfxName); };
    sampleBox.appendChild(b);
  }
});
/** Decode every file of every key; resolves {ok, failed, total, bytes}. Used by sandbox/audio/sfx-check.mjs. */
(window as unknown as { sfxProbe: () => Promise<unknown> }).sfxProbe = async () => {
  const m = await loadManifest();
  const files = [...new Set(Object.values(m).flatMap((e) => e.files))];
  const ctx = new OfflineAudioContext(1, 1, 44100);
  const failed: string[] = [];
  let bytes = 0;
  let seconds = 0;
  for (const f of files) {
    try {
      const r = await fetch(BASE + 'audio/sfx/' + f);
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const ab = await r.arrayBuffer();
      bytes += ab.byteLength;
      const buf = await ctx.decodeAudioData(ab);
      seconds += buf.duration;
      if (buf.duration < 0.05) throw new Error('too short');
    } catch (e) { failed.push(`${f}: ${String(e)}`); }
  }
  return { total: files.length, keys: Object.keys(m).length, failed, bytes, seconds };
};
