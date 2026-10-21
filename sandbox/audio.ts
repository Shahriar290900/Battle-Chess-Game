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
