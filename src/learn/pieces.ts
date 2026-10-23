// Piece Library data: names (from the art bible), chess role, movement text, mini move diagrams and lore.
// Pure data + functions (no DOM / three), so it is unit-tested.
import type { Faction, Role } from '../contracts';
import { DISPLAY_NAME, FACTION_NAME, assetId } from '../contracts';

export const ROLE_ORDER: readonly Role[] = ['king', 'queen', 'rook', 'bishop', 'knight', 'pawn'];

export interface RoleInfo {
  label: string;
  /** One-line chess function. */
  function: string;
  value: string;
  /** How it moves, one bullet per rule. */
  moves: string[];
  /** Why it matters in play. */
  tip: string;
  /** How it fights in the cinematics (matches the attack style of the assets). */
  battle: string;
}

export const ROLE_INFO: Record<Role, RoleInfo> = {
  pawn: {
    label: 'Pawn', function: 'The front line. Weak alone, decisive in numbers; reaching the far rank makes it a queen.', value: 'worth 1',
    moves: ['Steps one square straight ahead.', 'On its first move it may step two.', 'Captures one square diagonally forward.', 'Promotes on the last rank.'],
    tip: 'Pawns cannot go backwards, so every advance is a promise.',
    battle: 'Melee: closes in and strikes with a short blade or spear.',
  },
  rook: {
    label: 'Rook', function: 'A fortress on rails. Dominates open files and ranks and guards the king when castling.', value: 'worth 5',
    moves: ['Slides any distance straight: forwards, back, left or right.', 'Cannot jump over pieces.', 'Takes part in castling with the king.'],
    tip: 'Put rooks on open files and connect them.',
    battle: 'Slam: hammers down on the target with its whole weight.',
  },
  knight: {
    label: 'Knight', function: 'The leaper. The only piece that jumps over others; superb at forks.', value: 'worth 3',
    moves: ['Moves in an L: two squares one way, one square across.', 'Jumps over any piece in between.', 'Always lands on the opposite square colour.'],
    tip: 'A knight in the centre reaches eight squares; on the edge only four.',
    battle: 'Leap: vaults across the gap and lands on the target.',
  },
  bishop: {
    label: 'Bishop', function: 'The diagonal sniper. Each bishop stays on one colour of square for the whole game.', value: 'worth 3',
    moves: ['Slides any distance diagonally.', 'Cannot jump over pieces.', 'Never changes square colour.'],
    tip: 'Two bishops together cover every square on the board.',
    battle: 'Ranged: strikes from a distance with a spell.',
  },
  queen: {
    label: 'Queen', function: 'The strongest piece: the reach of a rook and a bishop combined.', value: 'worth 9',
    moves: ['Slides any distance straight or diagonally.', 'Cannot jump over pieces.'],
    tip: 'Bring the queen out with purpose; a lost queen is rarely forgiven.',
    battle: 'Summon: calls a spectral weapon to cut down the target.',
  },
  king: {
    label: 'King', function: 'The piece you must protect. Lose it (checkmate) and the game is lost.', value: 'priceless',
    moves: ['Steps one square in any direction.', 'May never move into check.', 'Can castle with a rook once, if neither has moved.'],
    tip: 'Castle early; an exposed king is an open invitation.',
    battle: 'Melee: a heavy walker with a hard, single strike.',
  },
};

/** Faction lore. Original text only. */
export const LORE: Record<Faction, Record<Role, string>> = {
  emberhold: {
    pawn: 'Soot-faced levies of the forge-keeps. They hold the line with heater shields and short spears, and light the first brazier of every battle.',
    rook: 'A walking siege-furnace of riveted bronze, dragged to the front by chain-gangs. When it slams down, flagstones remember.',
    knight: 'Riders of the ash plains on soot-maned destriers. They leap the shield wall like sparks leaving a fire.',
    bishop: 'Reads the future in cinders and hurls it back as a spark-lance down the diagonal.',
    queen: 'Crowned in living flame. She does not wield a weapon so much as agree to be one.',
    king: 'Eldest of the forge-lords, a heavy walker, slow to anger and slower to fall.',
  },
  rime: {
    pawn: 'Frost-bound footmen raised from the drifts. They never tire, and they never ask why.',
    rook: 'A tower of blue glacier-ice, hauled across the field. It strikes like a calving glacier.',
    knight: 'A pale rider on a gaunt mount, arriving on a wind that smells of old graves.',
    bishop: 'Sings runes into the air until the ice remembers the shape of a spell.',
    queen: 'Rises like a tide of frost. What she touches goes still.',
    king: 'A ruler frozen into his throne-armour; his will cracks like river ice, and so do his enemies.',
  },
};

export function displayName(faction: Faction, role: Role): string { return DISPLAY_NAME[assetId(faction, role)]; }
export function factionName(faction: Faction): string { return FACTION_NAME[faction]; }

// ---------------------------------------------------------------- move diagrams
export type DiagramKind = 'move' | 'capture' | 'both' | 'first';
export interface DiagramCell { x: number; y: number; kind: DiagramKind }
export interface Diagram { size: number; piece: { x: number; y: number }; cells: DiagramCell[] }

const SIZE = 7;
const CENTER = 3;

/** A 7x7 diagram with the piece in the middle (y grows upwards, like the board from White's seat). */
export function moveDiagram(role: Role): Diagram {
  const cells: DiagramCell[] = [];
  const add = (dx: number, dy: number, kind: DiagramKind) => {
    const x = CENTER + dx, y = CENTER + dy;
    if (x >= 0 && x < SIZE && y >= 0 && y < SIZE) cells.push({ x, y, kind });
  };
  const ray = (dx: number, dy: number) => { for (let k = 1; k < SIZE; k++) add(dx * k, dy * k, 'both'); };
  switch (role) {
    case 'pawn':
      add(0, 1, 'move'); add(0, 2, 'first'); add(-1, 1, 'capture'); add(1, 1, 'capture');
      break;
    case 'rook': for (const [dx, dy] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) ray(dx, dy); break;
    case 'bishop': for (const [dx, dy] of [[1, 1], [1, -1], [-1, 1], [-1, -1]]) ray(dx, dy); break;
    case 'queen': for (const [dx, dy] of [[1, 0], [-1, 0], [0, 1], [0, -1], [1, 1], [1, -1], [-1, 1], [-1, -1]]) ray(dx, dy); break;
    case 'knight': for (const [dx, dy] of [[1, 2], [2, 1], [2, -1], [1, -2], [-1, -2], [-2, -1], [-2, 1], [-1, 2]]) add(dx, dy, 'both'); break;
    case 'king': for (const [dx, dy] of [[1, 0], [-1, 0], [0, 1], [0, -1], [1, 1], [1, -1], [-1, 1], [-1, -1]]) add(dx, dy, 'both'); break;
  }
  return { size: SIZE, piece: { x: CENTER, y: CENTER }, cells };
}
