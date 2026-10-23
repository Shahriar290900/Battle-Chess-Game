// New-game flow in the character-select style: "Choose YOUR ALLEGIANCE" (two tall faction cards with king portraits),
// then "Choose YOUR FOE" (difficulty cards); for Two Players a single "how the board turns" choice.
import type { AiLevel, Faction, GameModeConfig, Role, SettingsStore, Side } from '../contracts';
import { FACTION_NAME, SIDE_FACTION } from '../contracts';
import { ICON, clear, h, pieceIcon, svg } from './dom';
import { backHint, tipOn } from './controls';
import type { Screen } from './screen';
import type { Portraits } from './portraits';

export interface FlowDeps {
  settings: SettingsStore;
  portraits(): Portraits;
  start(config: GameModeConfig): void;
  /** Leave the flow (back to the previous screen). */
  exit(): void;
}

interface CardSpec {
  cls?: string;
  faction?: Faction;
  name: string;
  desc: string;
  tag: string;
  tip: string;
  art: Node;
  pick(): void;
}

const FACTIONS: Array<{ side: Side; faction: Faction; desc: string; tag: string; tip: string }> = [
  { side: 'w', faction: 'emberhold', desc: 'Forge-sworn knights of cinder and iron. They march first and carry the fire to the field.', tag: 'The First Host', tip: 'Emberhold|You play White and move first. Warm forge-fire colours.' },
  { side: 'b', faction: 'rime', desc: 'Frost-wrought legions of the long winter. They answer in silence and strike when the field is cold.', tag: 'The Winter Host', tip: 'Rime Host|You play Black and answer second. Cold, pale frost colours.' },
];

const LEVELS: Array<{ level: AiLevel; name: string; role: Role; desc: string; tag: string; tip: string }> = [
  { level: 'easy', name: 'Easy', role: 'pawn', desc: 'A gentle skirmish. It favours simple plans and forgives your mistakes.', tag: 'Learning the field', tip: 'Easy|Plays quickly and misses tactics. Best while learning.' },
  { level: 'medium', name: 'Medium', role: 'knight', desc: 'A balanced rival that sees a few moves ahead and punishes blunders.', tag: 'A fair contest', tip: 'Medium|A solid club player. Thinks a little longer.' },
  { level: 'hard', name: 'Hard', role: 'rook', desc: 'Tactically sharp and patient. Weak squares will not go unnoticed.', tag: 'Veteran', tip: 'Hard|Strong tactical play. Expect a real fight.' },
  { level: 'master', name: 'Master', role: 'queen', desc: 'Full strength. It will not tire, and it will not forgive.', tag: 'Relentless', tip: 'Master|Maximum Stockfish strength. Replies may take a moment on slow devices.' },
];

type Step = 'allegiance' | 'foe' | 'table';

export function createFlow(d: FlowDeps): Screen & { open(kind: 'vs-ai' | 'hotseat'): void } {
  const kick = h('p', { class: 'kick', text: 'Choose' });
  const ttl = h('h2', { class: 'ttl', text: 'Your Allegiance' });
  const cards = h('div', { class: 'cards', role: 'list' });
  const el = h('div', { class: 'scr flow in', role: 'dialog', 'aria-label': 'New game' },
    h('div', { class: 'hd' }, kick, ttl, h('div', { class: 'rule' })), cards,
    h('div', { class: 'flow-hint kbd-only' }, h('i', { class: 'kbd', text: 'Left' }), h('i', { class: 'kbd', text: 'Right' }), 'Browse', h('i', { class: 'kbd', text: 'Enter' }), 'Choose'),
    backHint(() => api.back() || d.exit()));
  let step: Step = 'allegiance';
  let side: Side = d.settings.get().playerSide;

  function makeCard(c: CardSpec): HTMLButtonElement {
    const art = h('div', { class: 'art' }, c.art);
    const b = h('button', { class: `card fr ${c.cls ?? ''}`.trim(), type: 'button', role: 'listitem', 'data-nav': '', 'aria-label': c.name },
      art, h('div', { class: 'meta' }, h('h3', { class: 'nm', text: c.name }), h('p', { class: 'ds', text: c.desc }), h('p', { class: 'tg', text: c.tag })));
    if (c.faction) b.dataset.faction = c.faction;
    tipOn(b, c.tip);
    b.addEventListener('click', c.pick);
    return b;
  }

  function show(specs: CardSpec[], activeIdx: number, four: boolean) {
    clear(cards);
    cards.classList.toggle('four', four);
    const els = specs.map(makeCard);
    const setOn = (i: number) => els.forEach((e, k) => e.classList.toggle('on', k === i));
    els.forEach((e, i) => {
      e.addEventListener('pointerenter', (ev) => { if (ev.pointerType === 'mouse') setOn(i); });
      e.addEventListener('focus', () => setOn(i));
    });
    setOn(activeIdx);
    els[activeIdx].setAttribute('data-autofocus', '');
    cards.append(...els);
  }

  function render() {
    if (step === 'allegiance') {
      kick.textContent = 'Choose'; ttl.textContent = 'Your Allegiance';
      const portraits = d.portraits();
      show(FACTIONS.map((f) => ({
        faction: f.faction, name: FACTION_NAME[f.faction], desc: f.desc, tag: `${f.tag} · ${f.side === 'w' ? 'White' : 'Black'}`, tip: f.tip,
        art: portraits[f.faction] ? h('img', { src: portraits[f.faction], alt: '', draggable: 'false' }) : pieceIcon('king', f.faction, 'big'),
        pick: () => { side = f.side; d.settings.set('playerSide', f.side); step = 'foe'; render(); focusActive(); },
      })), side === 'b' ? 1 : 0, false);
    } else if (step === 'foe') {
      kick.textContent = 'Choose'; ttl.textContent = 'Your Foe';
      const cur = d.settings.get().aiLevel;
      show(LEVELS.map((l, i) => ({
        cls: `lv${i}`, name: l.name, desc: l.desc, tag: l.tag, tip: l.tip, art: pieceIcon(l.role, SIDE_FACTION[side === 'w' ? 'b' : 'w'], 'big'),
        pick: () => { d.settings.set('aiLevel', l.level); d.start({ kind: 'vs-ai', playerSide: side, aiLevel: l.level }); },
      })), Math.max(0, LEVELS.findIndex((l) => l.level === cur)), true);
    } else {
      kick.textContent = 'Two Players'; ttl.textContent = 'Turn of the Board';
      const follow = d.settings.get().cameraMode !== 'fixed';
      const go = (mode: 'follow' | 'fixed') => { d.settings.set('cameraMode', mode); d.start({ kind: 'hotseat', playerSide: 'w', aiLevel: d.settings.get().aiLevel }); };
      show([
        { name: 'Turn the Board', desc: 'The camera swings to each player after every move, so both sit on their own side.', tag: 'Pass and play', tip: 'Turn the Board|The camera follows the turn. Best when you hand the device back and forth.', art: svg(ICON.rotate, 'ic big'), pick: () => go('follow') },
        { name: 'Hold the Board', desc: 'The camera stays on the White side. Best for two players sharing a screen.', tag: 'Shared screen', tip: 'Hold the Board|The camera stays still, always from the White side.', art: svg(ICON.board, 'ic big'), pick: () => go('fixed') },
      ], follow ? 0 : 1, false);
    }
  }
  const focusActive = () => (cards.querySelector('[data-autofocus]') as HTMLElement | null)?.focus({ preventScroll: true });

  const api = {
    el,
    open(kind: 'vs-ai' | 'hotseat') { step = kind === 'vs-ai' ? 'allegiance' : 'table'; side = d.settings.get().playerSide; render(); },
    onShow() { /* render() ran in open() */ },
    back() {
      if (step === 'foe') { step = 'allegiance'; render(); focusActive(); return true; }
      d.exit();
      return true;
    },
  };
  return api;
}
