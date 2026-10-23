// How to Play: interactive lessons on preset positions. Pure data (chess.js only), unit-tested:
// every FEN is legal, every reference solution is a legal move that satisfies the lesson's own check.
import { Chess } from 'chess.js';
import type { MoveResult, PromotionRole, Role, Square } from '../contracts';
import { Rules } from '../core/rules';

export type LessonGroup = 'pieces' | 'rules' | 'mates' | 'tactics';
export const GROUP_TITLE: Record<LessonGroup, string> = { pieces: 'The Pieces', rules: 'Rules of the Field', mates: 'Ending the Game', tactics: 'First Tactics' };
export const GROUP_ORDER: readonly LessonGroup[] = ['pieces', 'rules', 'mates', 'tactics'];

export interface LessonMove { from: Square; to: Square; promotion?: PromotionRole }

export interface WrongVerdict { text: string; /** Play the move on the board, then reset the lesson. */ demo?: boolean }

export interface Lesson {
  id: string;
  group: LessonGroup;
  title: string;
  /** One-line summary on the book spine. */
  blurb: string;
  fen: string;
  /** Explanation paragraphs. */
  intro: string[];
  /** The instruction line. */
  task: string;
  /** Squares tinted gold (the pieces in play). */
  focus: Square[];
  /** Squares tinted green (where to go). */
  goal: Square[];
  /** Reference solutions (at least one). */
  solutions: LessonMove[];
  /** Custom acceptance test (defaults to matching `solutions`). Receives the played move and the position before it. */
  accept?: (res: MoveResult, before: Rules) => boolean;
  /** Hints keyed `from+to` (e.g. "e2e3") for specific tempting mistakes. */
  hints?: Record<string, string>;
  /** Hint when the piece tried cannot move like that. */
  illegalHint: string;
  /** Hint for a legal move that is not the lesson's answer. */
  wrongHint: string;
  explainWrong?: (res: MoveResult) => WrongVerdict | null;
  success: string | ((res: MoveResult) => string);
  /** A "remember" line shown with the stamp. */
  tip: string;
}

// ---------------------------------------------------------------- chess helpers
const flipTurn = (fen: string): string => { const p = fen.split(' '); p[1] = p[1] === 'w' ? 'b' : 'w'; p[3] = '-'; return p.join(' '); };
const VALUE: Record<string, number> = { p: 1, n: 3, b: 3, r: 5, q: 9, k: 100 };

/** Enemy pieces (value >= 3) attacked by the piece on `sq` in `fen`. */
export function attackedBy(fen: string, sq: Square): Square[] {
  const c = new Chess(fen);
  const me = c.get(sq as never);
  if (!me) return [];
  const out: Square[] = [];
  for (const row of c.board()) for (const p of row) {
    if (!p || p.color === me.color || VALUE[p.type] < 3) continue;
    if (c.attackers(p.square, me.color).includes(sq as never)) out.push(p.square);
  }
  return out;
}

/** Number of legal moves of the piece on `sq` when it is that piece's side to move. */
export function mobilityOf(fen: string, sq: Square): number {
  const c = new Chess(fen);
  const p = c.get(sq as never);
  if (!p) return 0;
  const f = p.color === c.turn() ? fen : flipTurn(fen);
  return new Chess(f).moves({ square: sq as never }).length;
}

export function defendersOf(fen: string, sq: Square): Square[] {
  const c = new Chess(fen);
  const p = c.get(sq as never);
  return p ? (c.attackers(sq as never, p.color) as Square[]) : [];
}

const mv = (from: Square, to: Square, promotion?: PromotionRole): LessonMove => ({ from, to, promotion });
const ROLE_NOUN: Record<Role, string> = { pawn: 'pawn', rook: 'rook', knight: 'knight', bishop: 'bishop', queen: 'queen', king: 'king' };

export const LESSONS: Lesson[] = [
  // ------------------------------------------------------------ pieces
  {
    id: 'pawn-step', group: 'pieces', title: 'Pawn: the double step', blurb: 'One step, or two on the first move.',
    fen: '4k3/8/8/8/8/8/4P3/4K3 w - - 0 1',
    intro: ['A pawn walks straight ahead, one square at a time. But on its very first move it may take a double step.'],
    task: 'Advance the pawn two squares to e4.',
    focus: ['e2'], goal: ['e4'], solutions: [mv('e2', 'e4')],
    hints: { e2e3: 'That is the ordinary single step. On its first move a pawn can leap two squares: try e4.' },
    illegalHint: 'Pawns only move straight ahead. Select the pawn and follow the glowing discs.',
    wrongHint: 'Almost. Move the pawn two squares forward, to e4.',
    success: 'Two squares in one move: the pawn claims the centre.',
    tip: 'The double step is only available from the pawn\'s starting square.',
  },
  {
    id: 'pawn-capture', group: 'pieces', title: 'Pawn: capturing', blurb: 'Pawns strike diagonally.',
    fen: '4k3/8/8/3p1p2/4P3/8/8/4K3 w - - 0 1',
    intro: ['Pawns move straight, but they capture one square diagonally forward. Two enemy pawns stand within reach.'],
    task: 'Capture either black pawn with your pawn.',
    focus: ['e4'], goal: ['d5', 'f5'], solutions: [mv('e4', 'd5'), mv('e4', 'f5')],
    accept: (r) => r.role === 'pawn' && !!r.captured,
    hints: { e4e5: 'A pawn cannot capture straight ahead. Look at the diagonals: d5 and f5.' },
    illegalHint: 'A pawn captures only one square diagonally forward.',
    wrongHint: 'Take one of the black pawns, diagonally.',
    success: 'Captured. The pawn slants forward to take its prey.',
    tip: 'Pawns walk straight but capture diagonally.',
  },
  {
    id: 'rook', group: 'pieces', title: 'Rook', blurb: 'Straight lines, any distance.',
    fen: '4k3/3p4/8/8/3R4/8/8/4K3 w - - 0 1',
    intro: ['The rook slides in straight lines, as far as the road is clear. The enemy pawn stands at the end of the d-file.'],
    task: 'Capture the pawn on d7 with your rook.',
    focus: ['d4'], goal: ['d7'], solutions: [mv('d4', 'd7')],
    illegalHint: 'A rook moves only in straight lines: forwards, back, left or right.',
    wrongHint: 'Slide the rook up the file to the pawn on d7.',
    success: 'The rook thunders down the file.',
    tip: 'Rooks love open files with nothing in the way.',
  },
  {
    id: 'knight', group: 'pieces', title: 'Knight', blurb: 'The L-shaped leaper.',
    fen: '4k3/8/8/5b2/3PPP2/4N3/8/4K3 w - - 0 1',
    intro: ['The knight moves in an L: two squares one way and one across. It is the only piece that jumps, so the wall of pawns in front is no obstacle.'],
    task: 'Leap over the pawns and capture the bishop on f5.',
    focus: ['e3'], goal: ['f5'], solutions: [mv('e3', 'f5')],
    illegalHint: 'A knight moves in an L: two squares one way, one square sideways.',
    wrongHint: 'Find the L that lands on f5.',
    success: 'Over the wall and onto the bishop.',
    tip: 'Knights jump, so closed positions suit them.',
  },
  {
    id: 'bishop', group: 'pieces', title: 'Bishop', blurb: 'Diagonal sniper.',
    fen: '4k3/8/7n/8/8/8/8/2B1K3 w - - 0 1',
    intro: ['The bishop slides along diagonals for any distance. The enemy knight sits at the far end of its diagonal.'],
    task: 'Capture the knight on h6 with your bishop.',
    focus: ['c1'], goal: ['h6'], solutions: [mv('c1', 'h6')],
    illegalHint: 'A bishop moves only diagonally.',
    wrongHint: 'Follow the long diagonal from c1 to h6.',
    success: 'A clean shot across the board.',
    tip: 'A bishop always stays on the same colour of square.',
  },
  {
    id: 'queen', group: 'pieces', title: 'Queen', blurb: 'Rook and bishop in one.',
    fen: '4k3/8/8/7r/8/8/8/3QK3 w - - 0 1',
    intro: ['The queen combines the rook and the bishop: any distance, straight or diagonal. She sees a rook on h5.'],
    task: 'Capture the rook on h5 with your queen.',
    focus: ['d1'], goal: ['h5'], solutions: [mv('d1', 'h5')],
    illegalHint: 'The queen moves in straight lines and diagonals, never like a knight.',
    wrongHint: 'Use the long diagonal from d1 to h5.',
    success: 'The queen reaches across the field.',
    tip: 'The queen is strong, so do not risk her for a pawn.',
  },
  {
    id: 'king', group: 'pieces', title: 'King', blurb: 'One step in any direction.',
    fen: '4k3/8/8/8/8/8/4p3/4K3 w - - 0 1',
    intro: ['The king steps one square in any direction. It is the most important piece, but it can still fight when it is safe.'],
    task: 'Capture the pawn on e2 with your king.',
    focus: ['e1'], goal: ['e2'], solutions: [mv('e1', 'e2')],
    illegalHint: 'The king moves exactly one square.',
    wrongHint: 'Step onto e2 and take the pawn.',
    success: 'The king takes the pawn that dared come so close.',
    tip: 'A king may never step onto a square the enemy attacks.',
  },

  // ------------------------------------------------------------ rules
  {
    id: 'capture', group: 'rules', title: 'Capturing', blurb: 'Take the piece nobody protects.',
    fen: '4k3/6b1/4p3/3n4/3Q4/8/8/4K3 w - - 0 1',
    intro: ['You capture by moving onto an enemy piece. But look first: a piece defended by another can be retaken, and then you lose yours.'],
    task: 'Your queen can take a knight or a bishop. Capture the one that is not protected.',
    focus: ['d4'], goal: ['g7'], solutions: [mv('d4', 'g7')],
    hints: { d4d5: 'That knight is protected by the pawn on e6; you would lose your queen. Find a piece nobody protects.' },
    illegalHint: 'The queen moves in straight lines and diagonals.',
    wrongHint: 'Check which enemy piece has no defender, and take that one.',
    success: 'Free material. Always check what protects a piece before you take it.',
    tip: 'Before capturing, ask: can they take back?',
  },
  {
    id: 'check', group: 'rules', title: 'Check', blurb: 'Attack the king.',
    fen: '4k3/8/8/8/8/8/8/R3K3 w - - 0 1',
    intro: ['When a piece attacks the enemy king, it is check. The king must respond at once. The checking piece will even provoke him.'],
    task: 'Give check with your rook.',
    focus: ['a1'], goal: ['a8'], solutions: [mv('a1', 'a8')],
    accept: (r) => r.check,
    illegalHint: 'A rook moves in straight lines. Which line attacks the king on e8?',
    wrongHint: 'That does not attack the king. Aim the rook along the back rank.',
    success: 'Check! The king is attacked and must act.',
    tip: 'Check is a threat, not a win: the king may escape.',
  },
  {
    id: 'escape', group: 'rules', title: 'Escaping check', blurb: 'Move, block or capture.',
    fen: 'R3r1k1/8/8/8/2B5/8/5PPP/4K3 w - - 0 1',
    intro: ['Your king is in check from the rook on e8. There are exactly three ways out: move the king, block the line, or capture the attacker.'],
    task: 'Get out of check any way you like.',
    focus: ['e1'], goal: [], solutions: [mv('e1', 'd1'), mv('c4', 'e2'), mv('a8', 'e8')],
    accept: () => true,
    illegalHint: 'You are in check: only a move that ends the check is allowed.',
    wrongHint: 'Deal with the check first.',
    success: (r) => (r.role === 'king' ? 'You stepped out of the line of fire.' : r.captured ? 'You captured the attacker.' : 'You blocked the line.'),
    tip: 'Move the king, block the line or capture the attacker.',
  },
  {
    id: 'castle-k', group: 'rules', title: 'Castling: kingside', blurb: 'King and rook, together.',
    fen: '4k3/pppp1ppp/8/8/8/8/PPPP1PPP/R3K2R w KQ - 0 1',
    intro: ['Once per game the king can tuck itself away with a rook. Move the king two squares toward the rook and the rook hops over to its other side.'],
    task: 'Castle on the kingside (short): move the king two squares toward the h-rook.',
    focus: ['e1', 'h1'], goal: ['g1'], solutions: [mv('e1', 'g1')],
    accept: (r) => r.isCastle && r.to === 'g1',
    illegalHint: 'Castling needs a clear path. Select the king and look for the square two steps toward the rook.',
    wrongHint: 'Try castling: the king goes to g1.',
    success: 'Castled. The king is safer and the rook is in play.',
    tip: 'Castling is allowed only if neither piece has moved and the king does not cross an attacked square.',
  },
  {
    id: 'castle-q', group: 'rules', title: 'Castling: queenside', blurb: 'The long way.',
    fen: '4k3/pppp1ppp/8/8/8/8/PPPP1PPP/R3K2R w KQ - 0 1',
    intro: ['Castling queenside (long) works the same way, toward the a-rook. The king moves two squares and the rook lands beside it.'],
    task: 'Castle on the queenside: move the king two squares toward the a-rook.',
    focus: ['e1', 'a1'], goal: ['c1'], solutions: [mv('e1', 'c1')],
    accept: (r) => r.isCastle && r.to === 'c1',
    illegalHint: 'Select the king and look for the square two steps toward the a-rook.',
    wrongHint: 'Try castling long: the king goes to c1.',
    success: 'Castled long. The rook lands on d1.',
    tip: 'Long castling needs three empty squares; short needs two.',
  },
  {
    id: 'en-passant', group: 'rules', title: 'En passant', blurb: 'The capture in passing.',
    fen: '4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 1',
    intro: ['Black\'s pawn has just stepped two squares and landed beside yours. For this one move only, you may capture it as if it had stepped just one square.'],
    task: 'Capture the pawn on d5 en passant: move your pawn to d6.',
    focus: ['e5', 'd5'], goal: ['d6'], solutions: [mv('e5', 'd6')],
    accept: (r) => r.isEnPassant,
    hints: { e5e6: 'You may push on, but the special chance vanishes next turn. Capture the pawn that just passed by.' },
    illegalHint: 'Your pawn captures diagonally forward: look at d6.',
    wrongHint: 'Take the passing pawn: move to d6.',
    success: 'The pawn on d5 is removed even though you landed on d6.',
    tip: 'En passant is only possible immediately after the double step.',
  },
  {
    id: 'promotion', group: 'rules', title: 'Promotion', blurb: 'Reach the far rank.',
    fen: '8/4P1k1/8/8/8/8/8/4K3 w - - 0 1',
    intro: ['A pawn that reaches the last rank is promoted to a queen, rook, bishop or knight. It is the pawn\'s great reward.'],
    task: 'Push the pawn to e8 and choose what it becomes.',
    focus: ['e7'], goal: ['e8'], solutions: [mv('e7', 'e8', 'queen')],
    accept: (r) => !!r.promotion,
    illegalHint: 'The pawn steps straight ahead. The last rank is one step away.',
    wrongHint: 'Step the pawn up to e8.',
    success: (r) => `The pawn is reborn as a ${ROLE_NOUN[r.promotion ?? 'queen']}.`,
    tip: 'Nearly everyone promotes to a queen.',
  },

  // ------------------------------------------------------------ mates
  {
    id: 'mate-back-rank', group: 'mates', title: 'Back-rank mate', blurb: 'The king trapped behind his own pawns.',
    fen: '6k1/5ppp/8/8/8/8/5PPP/3R2K1 w - - 0 1',
    intro: ['The black king is boxed in by his own pawns. A rook on the back rank gives check and he has nowhere to go: checkmate.'],
    task: 'Deliver checkmate with the rook.',
    focus: ['d1'], goal: ['d8'], solutions: [mv('d1', 'd8')],
    accept: (r) => r.mate,
    illegalHint: 'The rook slides straight along the d-file.',
    wrongHint: 'Find the move that attacks the king with no escape: the back rank.',
    success: 'Checkmate! The king and his army surrender.',
    tip: 'Give your own king a flight square (a luft) so this never happens to you.',
  },
  {
    id: 'mate-two-rooks', group: 'mates', title: 'Two rooks: the ladder', blurb: 'One rook cuts, the other strikes.',
    fen: '7k/R7/8/8/8/8/8/1R4K1 w - - 0 1',
    intro: ['One rook seals off the seventh rank, so the king cannot step down. The second rook delivers check along the back rank.'],
    task: 'Checkmate the king with the free rook.',
    focus: ['a7', 'b1'], goal: ['b8'], solutions: [mv('b1', 'b8')],
    accept: (r) => r.mate,
    illegalHint: 'The rook moves straight. Which file reaches the back rank?',
    wrongHint: 'The rook on a7 already guards the seventh rank. Use the other rook.',
    success: 'Checkmate. Two rooks sweep the board like a ladder.',
    tip: 'Rooks work best in pairs: one cuts off, one checks.',
  },
  {
    id: 'stalemate', group: 'mates', title: 'Stalemate', blurb: 'No moves, but no check: a draw.',
    fen: '7k/8/6K1/8/8/8/8/3Q4 w - - 0 1',
    intro: ['If the player to move has no legal move but is not in check, the game is a draw: stalemate. Winning players must take care.'],
    task: 'Checkmate Black without stalemating him.',
    focus: ['d1'], goal: ['d8'], solutions: [mv('d1', 'd8')],
    accept: (r) => r.mate,
    explainWrong: (r) => (r.stalemate ? { text: 'Stalemate! Black has no legal move but is not in check: the game is drawn. Watch the mist, then try again.', demo: true } : null),
    illegalHint: 'The queen moves in straight lines and diagonals.',
    wrongHint: 'That is not mate. Find a check where the king cannot escape.',
    success: 'Checkmate, and not a stalemate.',
    tip: 'Before every move, check that the enemy king still has somewhere to go.',
  },

  // ------------------------------------------------------------ tactics
  {
    id: 'fork', group: 'tactics', title: 'The fork', blurb: 'One piece, two targets.',
    fen: 'r3k3/8/8/3N4/8/8/8/4K3 w - - 0 1',
    intro: ['A fork attacks two pieces at once. Knights are the great forkers: their L-shaped attack hits squares the other pieces cannot guard together.'],
    task: 'Find the knight move that attacks the king and the rook together.',
    focus: ['d5', 'e8', 'a8'], goal: ['c7'], solutions: [mv('d5', 'c7')],
    accept: (r) => r.role === 'knight' && attackedBy(r.fenAfter, r.to).length >= 2,
    illegalHint: 'A knight moves in an L: two squares one way, one sideways.',
    wrongHint: 'Look for the square from which the knight attacks both the king and the rook.',
    success: 'Fork! The king must move and the rook falls.',
    tip: 'Look for a square that attacks two valuable pieces at once.',
  },
  {
    id: 'pin', group: 'tactics', title: 'The pin', blurb: 'A piece that cannot move.',
    fen: '4k3/8/2n5/8/8/8/4B3/4K3 w - - 0 1',
    intro: ['A pin freezes a piece because moving it would expose something more valuable behind it. Pin the knight to its king.'],
    task: 'Move the bishop so that the knight on c6 cannot move.',
    focus: ['e2', 'c6', 'e8'], goal: ['b5'], solutions: [mv('e2', 'b5')],
    accept: (r) => mobilityOf(r.fenAfter, 'c6') === 0 && r.role === 'bishop',
    illegalHint: 'A bishop moves along diagonals only.',
    wrongHint: 'Line up the bishop, the knight and the king on one diagonal.',
    success: 'Pinned! The knight is frozen: moving it would expose the king.',
    tip: 'A pinned piece is a target: attack it again.',
  },
  {
    id: 'protect', group: 'tactics', title: 'Protecting a piece', blurb: 'Make every capture a trade.',
    fen: '4k3/6b1/8/8/3N4/8/8/R3K3 w - - 0 1',
    intro: ['The bishop on g7 is eyeing your knight, which has no defender. Protect it: if the bishop takes, you take back.'],
    task: 'Defend the knight on d4 with another piece, without moving the knight.',
    focus: ['d4', 'g7'], goal: [], solutions: [mv('a1', 'd1'), mv('a1', 'a4')],
    accept: (r) => r.role !== 'knight' && defendersOf(r.fenAfter, 'd4').length > 0,
    illegalHint: 'Select your rook and see which squares let it guard the knight.',
    wrongHint: 'Keep the knight where it is and bring a defender to guard d4.',
    success: 'Protected. If the bishop takes, your rook takes back.',
    tip: 'Count attackers and defenders on every piece, yours and theirs.',
  },
  {
    id: 'open-centre', group: 'tactics', title: 'Opening: take the centre', blurb: 'Pawns on e4 or d4.',
    fen: 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1',
    intro: ['The first principle of the opening: control the centre. Pawns on e4 or d4 take space and open lines for your bishops and queen.'],
    task: 'Play a centre pawn: e4 or d4.',
    focus: ['e2', 'd2'], goal: ['e4', 'd4'], solutions: [mv('e2', 'e4'), mv('d2', 'd4')],
    hints: { a2a4: 'A flank pawn does little for the centre. Try e4 or d4.', h2h4: 'A flank pawn does little for the centre. Try e4 or d4.' },
    illegalHint: 'Select a pawn and follow the glowing discs.',
    wrongHint: 'Claim the middle of the board: e4 or d4.',
    success: 'A strong start: the centre is yours to command.',
    tip: 'Control the centre, develop your pieces, castle early.',
  },
  {
    id: 'open-develop', group: 'tactics', title: 'Opening: develop a piece', blurb: 'Bring knights and bishops out.',
    fen: 'rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2',
    intro: ['Second principle: develop. Move knights and bishops off the back rank toward the centre rather than moving the same piece twice or sending the queen out early.'],
    task: 'Develop a knight or a bishop.',
    focus: ['g1', 'b1', 'f1'], goal: ['f3', 'c3', 'c4'], solutions: [mv('g1', 'f3'), mv('b1', 'c3'), mv('f1', 'c4')],
    accept: (r) => (r.role === 'knight' || r.role === 'bishop') && r.from[1] === '1',
    hints: { d1h5: 'The queen is precious. Bring out the knights and bishops first.' },
    illegalHint: 'Select a knight or bishop and follow the glowing discs.',
    wrongHint: 'Bring a knight or bishop off the back rank.',
    success: 'Developed. More pieces in play means more power.',
    tip: 'Do not move the same piece twice in the opening without a reason.',
  },
];

export const LESSON_IDS = LESSONS.map((l) => l.id);
export const lessonById = (id: string): Lesson | undefined => LESSONS.find((l) => l.id === id);
export const lessonsInGroup = (g: LessonGroup): Lesson[] => LESSONS.filter((l) => l.group === g);

export function successText(lesson: Lesson, res: MoveResult): string {
  return typeof lesson.success === 'function' ? lesson.success(res) : lesson.success;
}

/** Does a played move solve the lesson? */
export function isSolved(lesson: Lesson, res: MoveResult, before: Rules): boolean {
  if (lesson.accept) return lesson.accept(res, before);
  return lesson.solutions.some((s) => s.from === res.from && s.to === res.to && (!s.promotion || s.promotion === res.promotion));
}

/** Play a reference move on a fresh position and return its result (used by tests and the sandbox autoplay). */
export function playReference(lesson: Lesson, m: LessonMove = lesson.solutions[0]): { res: MoveResult | null; rules: Rules } {
  const rules = new Rules(lesson.fen);
  return { res: rules.move(m.from, m.to, m.promotion), rules };
}
