// New-game flow in the character-select style: "Choose YOUR ALLEGIANCE" (two tall faction cards with king portraits),
// then "Choose YOUR FOE" (difficulty cards); for Two Players a single "how the board turns" choice.
import type { Faction, GameModeConfig, Role, SettingsStore, Side } from '../contracts';
import { AI_ELO_MAX, AI_ELO_MIN, AI_ELO_TIERS, FACTION_NAME, SIDE_FACTION } from '../contracts';
import { legacyLevelForElo, tierForElo } from '../core/ai/strength';
import { AI_ELO_STEP, sanitizeAiElo } from '../core/settings';
import type { RatingStore } from '../core/rating';
import { ICON, clear, h, pieceIcon, svg } from './dom';
import { backHint, button, rangeRow, tipOn } from './controls';
import type { Screen } from './screen';
import type { Portraits } from './portraits';

export interface FlowDeps {
  settings: SettingsStore;
  portraits(): Portraits;
  start(config: GameModeConfig & { aiElo?: number }): void;
  /** Local player rating (win-chance hints in the foe tooltips). */
  rating: RatingStore;
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
  /** Computer strength shown on the card (foe step). */
  elo?: number;
  art: Node;
  pick(): void;
}

const FACTIONS: Array<{ side: Side; faction: Faction; desc: string; tag: string; tip: string }> = [
  { side: 'w', faction: 'emberhold', desc: 'Forge-sworn knights of cinder and iron. They march first and carry the fire to the field.', tag: 'The First Host', tip: 'Emberhold|You play White and move first. Warm forge-fire colours.' },
  { side: 'b', faction: 'rime', desc: 'Frost-wrought legions of the long winter. They answer in silence and strike when the field is cold.', tag: 'The Winter Host', tip: 'Rime Host|You play Black and answer second. Cold, pale frost colours.' },
];

/** Named tiers over the Elo number (names and Elo values come from the contract; this adds the flavour text). */
const TIER_INFO: Array<{ role: Role; desc: string; tag: string; how: string }> = [
  { role: 'pawn', desc: 'A gentle skirmish. It hangs pieces and forgives almost every mistake.', tag: 'Learning the field', how: 'Hangs pieces and misses most threats. Best while you learn how the pieces move.' },
  { role: 'pawn', desc: 'It knows the moves and grabs free material, but cannot see a threat coming.', tag: 'First steps', how: 'Takes free pieces, still blunders often. Good for your first wins.' },
  { role: 'knight', desc: 'A casual club player. It sees simple tactics and punishes a careless blunder.', tag: 'A fair contest', how: 'Casual club strength: seldom hangs a piece, misses deeper plans.' },
  { role: 'bishop', desc: 'A solid club player. It calculates a few moves ahead and rarely gives pieces away.', tag: 'Tournament player', how: 'Strong club player. Plans a few moves ahead; tactics will be punished.' },
  { role: 'rook', desc: 'Sharp and patient. Weak squares will not go unnoticed.', tag: 'Expert', how: 'Expert level: strong tactics and endgames. Expect a real fight.' },
  { role: 'queen', desc: 'Master strength. It sets traps and converts every advantage.', tag: 'Master', how: 'Master level. Replies take a little longer.' },
  { role: 'king', desc: 'Near full strength. It will not tire, and it will not forgive.', tag: 'Relentless', how: 'Near maximum Stockfish strength. Replies may take a moment on slow devices.' },
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
  let elo = d.settings.get().aiElo;
  let setOnCard: (i: number) => void = () => undefined;

  // ---- fine-tune strength: `<< < 1350 · Knight > >>` in steps of 50, then Begin
  const note = h('p', { class: 'fine-note' });
  const fight = button('Begin', () => begin(elo), { cls: 'sel', tip: 'Begin|Start the game at the strength shown.' });
  const stepper = rangeRow('Fine-tune strength', AI_ELO_MIN, AI_ELO_MAX, AI_ELO_STEP, () => elo, (v) => { elo = sanitizeAiElo(v); syncFine(); },
    (v) => `${v} · ${tierForElo(v).name}`,
    'Fine-tune strength|Pick any rating from 400 to 3000 in steps of 50. The named tiers above are shortcuts. Hold an arrow to sweep.');
  const fine = h('div', { class: 'fine', hidden: true }, stepper.el, note, fight);
  el.insertBefore(fine, el.querySelector('.flow-hint'));

  function syncFine() {
    const r = d.rating.current();
    const chance = Math.round(d.rating.winChance(elo) * 100);
    note.textContent = `Your rating ${r.label}  ·  about ${chance}% to score against this foe`;
    setLabelText(fight, `Begin at ${elo}`);
    setOnCard(AI_ELO_TIERS.findIndex((t) => t === tierForElo(elo)));
    stepper.refresh();
  }
  const setLabelText = (b: HTMLElement, t: string) => { const l = b.querySelector('.lbl'); if (l) l.textContent = t; };
  function begin(e: number) {
    elo = sanitizeAiElo(e);
    d.settings.set('aiElo', elo);
    d.start({ kind: 'vs-ai', playerSide: side, aiLevel: legacyLevelForElo(elo), aiElo: elo });
  }

  function makeCard(c: CardSpec): HTMLButtonElement {
    const art = h('div', { class: 'art' }, c.art);
    const b = h('button', { class: `card fr ${c.cls ?? ''}`.trim(), type: 'button', role: 'listitem', 'data-nav': '', 'aria-label': c.name },
      art, h('div', { class: 'meta' }, c.elo !== undefined ? h('span', { class: 'elo', text: String(c.elo) }) : null,
        h('h3', { class: 'nm', text: c.name }), h('p', { class: 'ds', text: c.desc }), h('p', { class: 'tg', text: c.tag })));
    if (c.faction) b.dataset.faction = c.faction;
    tipOn(b, c.tip);
    b.addEventListener('click', c.pick);
    return b;
  }

  function show(specs: CardSpec[], activeIdx: number, layout: '' | 'four' | 'seven') {
    clear(cards);
    cards.classList.toggle('four', layout === 'four');
    cards.classList.toggle('seven', layout === 'seven');
    fine.hidden = layout !== 'seven';
    const els = specs.map(makeCard);
    const setOn = (i: number) => els.forEach((e, k) => e.classList.toggle('on', k === i));
    setOnCard = setOn;
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
      })), side === 'b' ? 1 : 0, '');
    } else if (step === 'foe') {
      kick.textContent = 'Choose'; ttl.textContent = 'Your Foe';
      elo = d.settings.get().aiElo;
      const r = d.rating.current();
      const odds = (elo: number) => Math.round(d.rating.winChance(elo) * 100);
      show(AI_ELO_TIERS.map((t, i) => ({
        cls: `t${i}`, name: t.name, elo: t.elo, desc: TIER_INFO[i].desc, tag: TIER_INFO[i].tag,
        tip: `${t.name} · ${t.elo} Elo|${TIER_INFO[i].how} At your rating (${r.label}) you would score about ${odds(t.elo)}%.`,
        art: pieceIcon(TIER_INFO[i].role, SIDE_FACTION[side === 'w' ? 'b' : 'w'], 'big'),
        pick: () => begin(t.elo),
      })), AI_ELO_TIERS.findIndex((t) => t === tierForElo(elo)), 'seven');
      syncFine();
    } else {
      kick.textContent = 'Two Players'; ttl.textContent = 'Turn of the Board';
      const follow = d.settings.get().cameraMode !== 'fixed';
      const go = (mode: 'follow' | 'fixed') => { d.settings.set('cameraMode', mode); d.start({ kind: 'hotseat', playerSide: 'w', aiLevel: d.settings.get().aiLevel }); };
      show([
        { name: 'Turn the Board', desc: 'The camera swings to each player after every move, so both sit on their own side.', tag: 'Pass and play', tip: 'Turn the Board|The camera follows the turn. Best when you hand the device back and forth.', art: svg(ICON.rotate, 'ic big'), pick: () => go('follow') },
        { name: 'Hold the Board', desc: 'The camera stays on the White side. Best for two players sharing a screen.', tag: 'Shared screen', tip: 'Hold the Board|The camera stays still, always from the White side.', art: svg(ICON.board, 'ic big'), pick: () => go('fixed') },
      ], follow ? 0 : 1, '');
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
