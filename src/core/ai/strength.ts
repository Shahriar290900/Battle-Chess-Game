// Elo -> engine strength. Pure functions (no DOM, no worker) so the mapping is unit-tested.
//
// ============================== STOCKFISH MAPPING (computer Elo -> UCI options) ==============================
//
//   Elo        mode      UCI options                                            search                      weakening on top
//   ---------  --------  -----------------------------------------------------  --------------------------  ---------------------------------------
//   1320-3000  limited   UCI_LimitStrength=true, UCI_Elo=<elo> (SF range         go movetime 300 ms @1320    none (Stockfish's own skill model)
//                        1320..3190), Skill Level 20, MultiPV 1                  -> 2500 ms @3000 (geometric)
//   400-1319   shallow   UCI_LimitStrength=false, Skill Level 0, MultiPV k       go depth d movetime <=350   we pick among the k PV lines with a
//                        (k = 6 @400 -> 2 @1319)                                d = 1 @400/600, 2 @800/1000, softmax(cp / T) and play a random legal
//                                                                               3 @1200, 4 @1319            move with probability p (calibration table)
//
//   Calibration anchors for the shallow branch (linear interpolation between rows, depth/MultiPV rounded):
//
//   Elo    depth  MultiPV  T (cp)  p(random)  max ms     feel
//   -----  -----  -------  ------  ---------  ------     ----------------------------------------------------
//   400    1      6        320     0.42       150        true beginner: hangs pieces, ignores threats
//   600    1      6        230     0.26       150        still hangs pieces, grabs free material when it sees it
//   800    2      5        150     0.14       200        sees one-move threats, often blunders a piece
//   1000   2      4        100     0.07       250        casual player: simple tactics, misses two-movers
//   1200   3      3        60      0.03       300        casual club player: rarely hangs material
//   1319   4      2        40      0.00       350        edge of the Stockfish-limited range
//
// Calibration (approximate, headless self-play vs Stockfish UCI_Elo 1320 at 300 ms, 16-20 games per rung): 400 and 600
// scored 0-3%, 800 about 5-9%, 1000 about 15% (target for a 320-point gap ~12%). The 1200 and 1319 rows were first
// too strong (55% and 78% vs 1320), were weakened afterwards and NOT re-measured (the machine was overloaded), so
// treat the top two rows as +-150 Elo. The scale is internally ordered; it is not an official rating.
//
// The built-in fallback engine (alpha-beta, used if the WASM worker cannot load) follows the same idea with its own
// table (see fallback.ts, `fallbackProfile`), so strength ordering holds there too.
import { AI_ELO_MAX, AI_ELO_MIN, AI_ELO_TIERS, LEGACY_LEVEL_ELO } from '../../contracts';
import type { AiLevel } from '../../contracts';

/** Stockfish 19 UCI_Elo range. */
export const SF_ELO_MIN = 1320;
export const SF_ELO_MAX = 3190;

export type Rng = () => number;

/** Small deterministic PRNG (tests, calibration runs). */
export function mulberry32(seed: number): Rng {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/** Elo number or legacy level -> a clamped Elo. */
export function toElo(level: number | AiLevel): number {
  const raw = typeof level === 'number' ? level : LEGACY_LEVEL_ELO[level];
  const n = typeof raw === 'number' && Number.isFinite(raw) ? raw : LEGACY_LEVEL_ELO.medium;
  return Math.min(AI_ELO_MAX, Math.max(AI_ELO_MIN, Math.round(n)));
}

/** Nearest named tier (UI sugar over the Elo number). */
export function tierForElo(elo: number): { name: string; elo: number } {
  let best: { name: string; elo: number } = AI_ELO_TIERS[0];
  for (const t of AI_ELO_TIERS) if (Math.abs(t.elo - elo) < Math.abs(best.elo - elo)) best = t;
  return best;
}

/** "Warlord · 2400" (nearest tier name + the exact number). */
export function eloLabel(elo: number): string {
  return `${tierForElo(elo).name} · ${Math.round(elo)}`;
}

/** Legacy level closest to an Elo (keeps the deprecated Settings.aiLevel / GameModeConfig.aiLevel populated). */
export function legacyLevelForElo(elo: number): AiLevel {
  let best: AiLevel = 'medium';
  let d = Infinity;
  for (const k of Object.keys(LEGACY_LEVEL_ELO) as AiLevel[]) {
    const dd = Math.abs(LEGACY_LEVEL_ELO[k] - elo);
    if (dd < d) { d = dd; best = k; }
  }
  return best;
}

/** Linear interpolation over rows `[x, ...values]`, clamped at both ends. */
export function interpolate(rows: ReadonlyArray<readonly number[]>, x: number): number[] {
  if (x <= rows[0][0]) return rows[0].slice(1);
  const last = rows[rows.length - 1];
  if (x >= last[0]) return last.slice(1);
  for (let i = 1; i < rows.length; i++) {
    if (x <= rows[i][0]) {
      const a = rows[i - 1], b = rows[i];
      const t = (x - a[0]) / (b[0] - a[0]);
      return a.slice(1).map((v, k) => v + (b[k + 1] - v) * t);
    }
  }
  return last.slice(1);
}

export interface EngineProfile {
  elo: number;
  /** 'limited' = Stockfish UCI_Elo; 'shallow' = Skill 0 + low depth + our own weakening. */
  mode: 'limited' | 'shallow';
  limitStrength: boolean;
  /** UCI_Elo value (limited mode only). */
  uciElo: number | null;
  skill: number;
  multiPV: number;
  /** Depth cap (shallow mode only). */
  depth: number | null;
  movetimeMs: number;
  /** Softmax temperature in centipawns over the MultiPV lines (0 = always the best line). */
  temperatureCp: number;
  /** Probability of playing a uniformly random legal move. */
  randomMoveProb: number;
}

// [elo, depth, multiPV, temperature cp, p(random), max movetime ms]
const SHALLOW_ANCHORS: ReadonlyArray<readonly number[]> = [
  [400, 1, 6, 320, 0.42, 150],
  [600, 1, 6, 250, 0.3, 150],
  [800, 1, 5, 170, 0.15, 200],
  [1000, 2, 5, 150, 0.12, 250],
  [1200, 2, 4, 125, 0.11, 300],
  [1319, 2, 3, 100, 0.06, 350],
];

export function engineProfile(level: number | AiLevel): EngineProfile {
  const elo = toElo(level);
  if (elo >= SF_ELO_MIN) {
    const uciElo = Math.min(SF_ELO_MAX, Math.max(SF_ELO_MIN, elo));
    const t = Math.min(1, Math.max(0, (elo - SF_ELO_MIN) / (AI_ELO_MAX - SF_ELO_MIN)));
    const movetimeMs = Math.round(300 * Math.pow(2500 / 300, t));
    return { elo, mode: 'limited', limitStrength: true, uciElo, skill: 20, multiPV: 1, depth: null, movetimeMs, temperatureCp: 0, randomMoveProb: 0 };
  }
  const [depth, mpv, temp, rand, ms] = interpolate(SHALLOW_ANCHORS, elo);
  return {
    elo, mode: 'shallow', limitStrength: false, uciElo: null, skill: 0,
    multiPV: Math.round(mpv), depth: Math.round(depth), movetimeMs: Math.round(ms),
    temperatureCp: Math.round(temp), randomMoveProb: Math.round(rand * 1000) / 1000,
  };
}

/** `setoption` lines to send before each search (state persists in the engine, so always send the full set). */
export function uciSetup(p: EngineProfile): string[] {
  const lines = [`setoption name UCI_LimitStrength value ${p.limitStrength}`];
  if (p.uciElo !== null) lines.push(`setoption name UCI_Elo value ${p.uciElo}`);
  lines.push(`setoption name Skill Level value ${p.skill}`, `setoption name MultiPV value ${p.multiPV}`);
  return lines;
}

export function goCommand(p: EngineProfile): string {
  return p.depth === null ? `go movetime ${p.movetimeMs}` : `go depth ${p.depth} movetime ${p.movetimeMs}`;
}

// ------------------------------------------------------------------ choosing among MultiPV lines
export interface PvCandidate { uci: string; cp: number }

const CP_CLAMP = 1500;

/** Parse `info ... multipv N score cp X|mate Y ... pv e2e4 ...` (null if it carries no score/pv). */
export function parseInfo(line: string): { depth: number; multipv: number; cp: number; uci: string } | null {
  if (!line.startsWith('info ') || line.includes(' lowerbound') || line.includes(' upperbound')) return null;
  const tok = line.split(/\s+/);
  const get = (k: string) => { const i = tok.indexOf(k); return i >= 0 ? tok[i + 1] : undefined; };
  const depth = Number(get('depth'));
  const pvIdx = tok.indexOf('pv');
  const si = tok.indexOf('score');
  if (!Number.isFinite(depth) || pvIdx < 0 || si < 0) return null;
  const kind = tok[si + 1];
  const val = Number(tok[si + 2]);
  if (!Number.isFinite(val)) return null;
  const cp = kind === 'mate' ? (val > 0 ? CP_CLAMP : -CP_CLAMP) : Math.max(-CP_CLAMP, Math.min(CP_CLAMP, val));
  const multipv = get('multipv') === undefined ? 1 : Number(get('multipv'));
  return { depth, multipv, cp, uci: tok[pvIdx + 1] };
}

/** Keep the lines of the deepest iteration seen. */
export function collectCandidates(infoLines: string[], limit = Infinity): PvCandidate[] {
  let maxDepth = -1;
  const byPv = new Map<number, { depth: number; cp: number; uci: string }>();
  for (const l of infoLines) {
    const i = parseInfo(l);
    if (!i) continue;
    if (i.depth > maxDepth) { maxDepth = i.depth; byPv.clear(); }
    if (i.depth === maxDepth) byPv.set(i.multipv, i);
  }
  return [...byPv.entries()].sort((a, b) => a[0] - b[0]).slice(0, limit).map(([, v]) => ({ uci: v.uci, cp: v.cp }));
}

/** Softmax pick: weight = exp((cp - best) / T). T <= 0 returns the best line. */
export function softmaxPick<T extends { cp: number }>(items: T[], temperatureCp: number, rng: Rng): T {
  const best = items.reduce((a, b) => (b.cp > a.cp ? b : a));
  if (temperatureCp <= 0 || items.length === 1) return best;
  const w = items.map((c) => Math.exp((c.cp - best.cp) / temperatureCp));
  let r = rng() * w.reduce((a, b) => a + b, 0);
  for (let i = 0; i < items.length; i++) { r -= w[i]; if (r <= 0) return items[i]; }
  return best;
}

/**
 * Final move choice for the shallow (<1320) branch: random legal move with probability `randomMoveProb`, otherwise a
 * softmax pick among the PV candidates. Falls back to `bestmove` when the engine reported no usable lines.
 */
export function chooseWeakMove(cands: PvCandidate[], legalUci: string[], bestmove: string, p: EngineProfile, rng: Rng): string {
  if (legalUci.length && rng() < p.randomMoveProb) return legalUci[Math.floor(rng() * legalUci.length)];
  const ok = cands.filter((c) => legalUci.includes(c.uci));
  if (!ok.length) return bestmove;
  return softmaxPick(ok, p.temperatureCp, rng).uci;
}
