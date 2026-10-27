import { createAudioBus } from '../src/audio';
import { bus as events } from '../src/contracts';
import type { Faction, Role, SfxName } from '../src/contracts';

const audio = createAudioBus();
audio.attach(events);
(window as unknown as { audio: unknown }).audio = audio;

const F: Faction[] = ['emberhold', 'rime'];
const R: Role[] = ['pawn', 'knight', 'bishop', 'rook', 'queen', 'king'];
const names: SfxName[] = [
  ...F.map((f) => `move:step:${f}` as const), ...R.map((r) => `attack:whoosh:${r}` as const),
  ...F.map((f) => `impact:${f}` as const), ...F.map((f) => `shatter:${f}` as const),
  ...F.map((f) => `summon:${f}` as const), ...F.map((f) => `spell:${f}` as const),
  'check', 'mate', 'ui:click', 'ui:select', 'castle', 'promote',
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
