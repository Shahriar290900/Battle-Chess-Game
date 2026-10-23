// Piece Library: a codex. Faction tabs on top, the piece list on the left, name / role / movement / lore in the
// middle (with a live mini-duel below), and the large 3D inspector on the right. On portrait phones the columns
// stack: model, text, duel. Both 3D views render through reduced-resolution panes that pause when hidden.
import type { Faction, Role } from '../contracts';
import { FACTIONS } from '../contracts';
import { btn, clear, h, tip } from './dom';
import { DUEL_ENEMIES, enemyFaction } from './duel';
import { createDuelView } from './duelview';
import { createInspector, INSPECTOR_CLIPS, type InspectorClip } from './inspector';
import { LORE, ROLE_INFO, ROLE_ORDER, displayName, factionName, moveDiagram } from './pieces';
import { EMPTY_FEN, type Session } from './session';
import { diagramEl } from './ui';

const CLIP_TIP: Record<InspectorClip, string> = {
  Idle: 'Idle|The resting pose.',
  Attack: 'Attack|Play this piece\'s strike.',
  Taunt: 'Taunt|The gesture it makes when giving check.',
  Surrender: 'Surrender|How it yields on checkmate.',
};

export function runLibrary(session: Session): void {
  const s = session.services;
  const panes = session.panes();
  const rigHandle = s.camera.borrow();
  rigHandle.set(s.camera.camera.position, s.camera.camera.position.clone().setY(40), s.camera.camera.fov); // park: nothing to draw
  s.board.syncToFen(EMPTY_FEN);
  s.fx.setStaticActors?.([]);

  let faction: Faction = 'emberhold';
  let role: Role = 'king';
  let enemy: Role | 'all' = 'all';

  const inspector = createInspector(s, panes);
  const duel = createDuelView(s, panes, rigHandle);
  session.addCleanup(async () => { inspector.dispose(); await duel.dispose(); });

  // ---------------------------------------------------------------- layout
  const tabs = FACTIONS.map((f) => h('button', {
    class: 'learn-tab', type: 'button', role: 'tab', 'aria-selected': 'false', 'data-tip': tip(factionName(f), f === 'emberhold' ? 'The forge-hosts of the White side.' : 'The frost-bound Black side.'),
    onClick: () => { faction = f; refresh(); },
  }, factionName(f)));
  const closeBtn = btn('Back to menu', tip('Back', 'Close the library and return to the main menu.'), () => { void session.close(); }, 'learn-quiet');
  const head = h('header', { class: 'learn-codex-head' },
    h('div', { class: 'learn-titles' }, h('h1', { class: 'learn-title', text: 'Piece Library' }), h('p', { class: 'learn-script', text: 'The hosts of the field' })),
    h('div', { class: 'learn-tabs', role: 'tablist', 'aria-label': 'Faction' }, ...tabs), closeBtn);

  const list = h('ul', { class: 'learn-piece-list' });
  const nav = h('nav', { class: 'learn-codex-list', 'aria-label': 'Pieces' }, list);
  const pieceButtons = ROLE_ORDER.map((r) => {
    const b = h('button', { class: 'learn-piece', type: 'button', 'aria-pressed': 'false', onClick: () => { role = r; refresh(); } });
    list.append(h('li', null, b));
    return { role: r, b };
  });

  const text = h('div', { class: 'learn-codex-body' });
  const enemyChips = [{ v: 'all' as const, label: 'All' }, ...DUEL_ENEMIES.map((r) => ({ v: r, label: r === 'king' ? 'King (mate)' : ROLE_INFO[r].label }))].map((o) => h('button', {
    class: 'learn-chip', type: 'button', 'aria-pressed': String(o.v === enemy),
    'data-tip': o.v === 'all' ? 'All opponents|Cycle through every enemy role.' : o.v === 'king' ? 'Enemy king|Give check and watch the king surrender.' : `${o.label}|Fight an enemy ${o.label.toLowerCase()}.`,
    onClick: () => { enemy = o.v; enemyChips.forEach((c, i) => c.setAttribute('aria-pressed', String(i === 0 ? enemy === 'all' : DUEL_ENEMIES[i - 1] === enemy))); duel.setEnemy(enemy); },
  }, o.label));
  const duelStatus = h('p', { class: 'learn-duel-status', 'aria-live': 'polite' });
  duel.status = (t, e) => { duelStatus.textContent = `${displayName(enemyFaction(faction), e)}: ${t}`; };
  const duelBox = h('section', { class: 'learn-duel', 'aria-label': 'Live duel' },
    h('h3', { class: 'learn-h3', text: 'In Battle' }), h('div', { class: 'learn-chips', role: 'group', 'aria-label': 'Opponent' }, ...enemyChips), duel.el, duelStatus);
  const article = h('article', { class: 'learn-codex-text' }, text, duelBox);

  const clipButtons = INSPECTOR_CLIPS.map((c) => h('button', { class: 'learn-chip', type: 'button', 'data-tip': CLIP_TIP[c], onClick: () => inspector.play(c) }, c));
  const spin = h('button', { class: 'learn-chip', type: 'button', 'aria-pressed': 'true', 'data-tip': tip('Auto-rotate', 'Turn the piece slowly when you are not dragging.'), onClick: () => { inspector.autoRotate = !inspector.autoRotate; spin.setAttribute('aria-pressed', String(inspector.autoRotate)); } }, 'Auto-rotate');
  const still = h('button', { class: 'learn-chip', type: 'button', 'aria-pressed': 'false', 'data-tip': tip('Freeze view', 'Stop drawing this view to save battery. Drag to wake it.'), onClick: () => { inspector.paused = !inspector.paused; still.setAttribute('aria-pressed', String(inspector.paused)); } }, 'Freeze');
  const toolbar = h('div', { class: 'learn-toolbar' },
    h('div', { class: 'learn-chips', role: 'group', 'aria-label': 'Animation' }, ...clipButtons),
    h('div', { class: 'learn-chips', role: 'group', 'aria-label': 'View' }, spin, still,
      btn('−', tip('Zoom out', 'Move the camera away from the piece.'), () => inspector.zoom(0.15), 'learn-chip'),
      btn('+', tip('Zoom in', 'Move the camera closer to the piece.'), () => inspector.zoom(-0.15), 'learn-chip'),
      btn('Reset view', tip('Reset view', 'Return to the default camera angle.'), () => inspector.resetView(), 'learn-chip')),
    h('p', { class: 'learn-hint', text: 'Drag to rotate. Scroll or pinch to zoom.' }));
  const aside = h('aside', { class: 'learn-codex-model', 'aria-label': 'Piece view' }, inspector.el, toolbar);

  const screen = h('section', { class: 'learn-screen learn-codex' }, head, nav, article, aside);
  session.root.append(screen);

  // ---------------------------------------------------------------- content
  function refresh() {
    const info = ROLE_INFO[role];
    tabs.forEach((t, i) => t.setAttribute('aria-selected', String(FACTIONS[i] === faction)));
    pieceButtons.forEach(({ role: r, b }) => {
      clear(b);
      b.append(h('span', { class: 'learn-piece-name', text: displayName(faction, r) }), h('span', { class: 'learn-piece-role', text: ROLE_INFO[r].label }));
      b.setAttribute('aria-pressed', String(r === role));
      b.setAttribute('data-tip', `${displayName(faction, r)}|${ROLE_INFO[r].label}: ${ROLE_INFO[r].function.split('.')[0]}.`);
    });
    clear(text);
    text.append(
      h('p', { class: 'learn-kicker', text: `${factionName(faction)} · ${info.label}` }),
      h('h2', { class: 'learn-codex-name', text: displayName(faction, role) }),
      h('p', { class: 'learn-meta', text: `${info.label}, ${info.value}` }),
      h('p', { class: 'learn-function', text: info.function }),
      h('h3', { class: 'learn-h3', text: 'How It Moves' }),
      h('div', { class: 'learn-moves' }, diagramEl(moveDiagram(role)), h('ul', null, ...info.moves.map((m) => h('li', { text: m })))),
      h('p', { class: 'learn-legend', text: 'Gold marks a quiet move, red a capture, and both together are marked in green.' }),
      h('p', { class: 'learn-tip', text: info.tip }),
      h('h3', { class: 'learn-h3', text: 'Lore' }),
      h('blockquote', { class: 'learn-lore', text: LORE[faction][role] }),
      h('p', { class: 'learn-battle', text: `In battle: ${info.battle}` }),
    );
    inspector.setPiece(faction, role);
    duel.setAttacker(faction, role);
  }
  refresh();
  (pieceButtons[0].b as HTMLElement).focus({ preventScroll: true });
  session.onBack = () => { void session.close(); return true; };
}
