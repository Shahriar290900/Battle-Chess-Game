// Seeded generator for tests/games/*.pgn. Plays weighted-random games with chess.js, tracks which
// rules features each game exercises, and greedily keeps the smallest set that covers everything
// replay.test.ts asserts: both castlings for both sides, en passant, under-promotion, every
// attacker x defender capture pair (defender king is impossible in legal chess), checkmate, stalemate.
//
//   node tests/tools/generate-games.mjs [maxGames=8000]
import { Chess } from 'chess.js';
import { mkdirSync, readdirSync, rmSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const OUT = join(dirname(fileURLToPath(import.meta.url)), '..', 'games');
const ROLE = { p: 'pawn', n: 'knight', b: 'bishop', r: 'rook', q: 'queen', k: 'king' };
const ROLES = Object.values(ROLE);

function mulberry32(a) {
  return () => {
    a |= 0; a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

export const REQUIRED = [
  'castle:w:k', 'castle:w:q', 'castle:b:k', 'castle:b:q', 'en-passant',
  'promo:rook', 'promo:bishop', 'promo:knight', 'promo:queen', 'mate', 'stalemate',
  ...ROLES.flatMap((a) => ROLES.filter((d) => d !== 'king').map((d) => `capture:${a}>${d}`)),
];

function playGame(seed, fen) {
  const rnd = mulberry32(seed);
  const chess = fen ? new Chess(fen) : new Chess();
  const feats = new Set();
  for (let ply = 0; ply < 320 && !chess.isGameOver(); ply++) {
    const moves = chess.moves({ verbose: true });
    const weights = moves.map((m) => {
      let w = 1;
      if (m.captured) w += 5;
      if (m.isEnPassant()) w += 20;
      if (m.promotion) w += 25;
      if (m.isKingsideCastle() || m.isQueensideCastle()) w += 12;
      if (m.san.includes('+')) w += 2;
      return w;
    });
    let r = rnd() * weights.reduce((a, b) => a + b, 0);
    let pick = moves[moves.length - 1];
    for (let i = 0; i < moves.length; i++) { r -= weights[i]; if (r <= 0) { pick = moves[i]; break; } }
    if (pick.isKingsideCastle()) feats.add(`castle:${pick.color}:k`);
    if (pick.isQueensideCastle()) feats.add(`castle:${pick.color}:q`);
    if (pick.isEnPassant()) feats.add('en-passant');
    if (pick.promotion) feats.add(`promo:${ROLE[pick.promotion]}`);
    if (pick.captured) feats.add(`capture:${ROLE[pick.piece]}>${ROLE[pick.captured]}`);
    chess.move(pick.san);
  }
  if (chess.isCheckmate()) feats.add('mate');
  if (chess.isStalemate()) feats.add('stalemate');
  return { chess, feats };
}

function headers(chess, name, seed) {
  chess.setHeader('Event', name);
  chess.setHeader('Site', 'Battle Chess test suite');
  chess.setHeader('Date', '2026.01.01');
  chess.setHeader('Round', String(seed));
  chess.setHeader('White', 'Emberhold');
  chess.setHeader('Black', 'Rime Host');
  const res = chess.isCheckmate() ? (chess.turn() === 'w' ? '0-1' : '1-0') : chess.isGameOver() ? '1/2-1/2' : '*';
  chess.setHeader('Result', res);
  return chess.pgn();
}

const max = Number(process.argv[2] ?? 8000);
const candidates = [];
for (let seed = 1; seed <= max; seed++) {
  const { chess, feats } = playGame(seed);
  candidates.push({ seed, chess, feats });
}
// Scripted scenarios (deterministic, short).
const scripted = [];
{
  const fool = new Chess();
  for (const m of ['f3', 'e5', 'g4', 'Qh4#']) fool.move(m);
  scripted.push({ name: 'scripted-fools-mate', chess: fool, feats: new Set(['mate']) });
  const stale = new Chess('7k/8/6K1/8/8/8/8/5Q2 w - - 0 1');
  stale.move('Qf7');
  scripted.push({ name: 'scripted-stalemate', chess: stale, feats: new Set(['stalemate']) });
}

const need = new Set(REQUIRED);
const chosen = [];
for (const s of scripted) { chosen.push(s); s.feats.forEach((f) => need.delete(f)); }
while (need.size) {
  let best = null; let bestScore = 0;
  for (const c of candidates) {
    let score = 0;
    for (const f of c.feats) if (need.has(f)) score++;
    // Prefer shorter games on ties.
    if (score > bestScore || (score === bestScore && best && score > 0 && c.chess.history().length < best.chess.history().length)) { best = c; bestScore = score; }
  }
  if (!best) break;
  chosen.push({ name: `seeded-${best.seed}`, seed: best.seed, chess: best.chess, feats: best.feats });
  best.feats.forEach((f) => need.delete(f));
}
if (need.size) { console.error('UNCOVERED:', [...need].join(', ')); process.exitCode = 1; }

mkdirSync(OUT, { recursive: true });
for (const f of readdirSync(OUT)) if (f.endsWith('.pgn')) rmSync(join(OUT, f));
chosen.forEach((c, i) => {
  const file = `${String(i + 1).padStart(2, '0')}-${c.name}.pgn`;
  writeFileSync(join(OUT, file), headers(c.chess, c.name, c.seed ?? 0) + '\n');
  console.log(file, c.chess.history().length, 'plies', [...c.feats].filter((f) => REQUIRED.includes(f)).length, 'features');
});
console.log('games:', chosen.length, 'uncovered:', need.size);
