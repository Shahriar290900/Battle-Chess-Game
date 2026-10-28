import { describe, expect, it } from 'vitest';
import { AI_ELO_MAX, AI_ELO_MIN, AI_ELO_TIERS, LEGACY_LEVEL_ELO } from '../../src/contracts';
import {
  SF_ELO_MAX, SF_ELO_MIN, chooseWeakMove, collectCandidates, engineProfile, eloLabel, goCommand, legacyLevelForElo, mulberry32,
  parseInfo, softmaxPick, tierForElo, toElo, uciSetup,
} from '../../src/core/ai/strength';

describe('Elo -> engine options', () => {
  it('uses UCI_Elo with a scaled movetime from 1320 up', () => {
    const lo = engineProfile(1320), hi = engineProfile(3000), mid = engineProfile(2000);
    expect(lo).toMatchObject({ mode: 'limited', limitStrength: true, uciElo: 1320, movetimeMs: 300, multiPV: 1 });
    expect(hi).toMatchObject({ mode: 'limited', uciElo: 3000, movetimeMs: 2500 });
    expect(mid.movetimeMs).toBeGreaterThan(lo.movetimeMs);
    expect(mid.movetimeMs).toBeLessThan(hi.movetimeMs);
    expect(uciSetup(lo)).toEqual([
      'setoption name UCI_LimitStrength value true', 'setoption name UCI_Elo value 1320',
      'setoption name Skill Level value 20', 'setoption name MultiPV value 1',
    ]);
    expect(goCommand(hi)).toBe('go movetime 2500');
  });
  it('clamps UCI_Elo to the Stockfish range', () => {
    for (let e = AI_ELO_MIN; e <= AI_ELO_MAX; e += 50) {
      const p = engineProfile(e);
      if (p.uciElo !== null) expect(p.uciElo).toBeGreaterThanOrEqual(SF_ELO_MIN), expect(p.uciElo).toBeLessThanOrEqual(SF_ELO_MAX);
    }
    expect(engineProfile(99999).uciElo).toBe(3000);
    expect(engineProfile(-5).elo).toBe(AI_ELO_MIN);
  });
  it('below 1320: no limit-strength, Skill 0, shallow depth, calibrated randomness', () => {
    for (const e of [400, 800, 1200, 1300]) {
      const p = engineProfile(e);
      expect(p).toMatchObject({ mode: 'shallow', limitStrength: false, uciElo: null, skill: 0 });
      expect(p.depth).toBeGreaterThanOrEqual(1);
      expect(p.depth).toBeLessThanOrEqual(4);
      expect(uciSetup(p)[0]).toBe('setoption name UCI_LimitStrength value false');
      expect(uciSetup(p).join()).not.toContain('UCI_Elo');
      expect(goCommand(p)).toMatch(/^go depth \d movetime \d+$/);
    }
    expect(engineProfile(400)).toMatchObject({ depth: 1, multiPV: 6, randomMoveProb: 0.42, temperatureCp: 320 });
  });
  it('is monotonic: stronger Elo never means more randomness, more noise or a shallower search', () => {
    let prev = engineProfile(AI_ELO_MIN);
    for (let e = AI_ELO_MIN + 50; e < SF_ELO_MIN; e += 50) {
      const p = engineProfile(e);
      expect(p.randomMoveProb).toBeLessThanOrEqual(prev.randomMoveProb);
      expect(p.temperatureCp).toBeLessThanOrEqual(prev.temperatureCp);
      expect(p.depth!).toBeGreaterThanOrEqual(prev.depth!);
      expect(p.movetimeMs).toBeGreaterThanOrEqual(prev.movetimeMs);
      prev = p;
    }
    expect(engineProfile(1300).randomMoveProb).toBeLessThan(engineProfile(1200).randomMoveProb);
  });
  it('accepts legacy levels', () => {
    for (const [lvl, elo] of Object.entries(LEGACY_LEVEL_ELO)) expect(toElo(lvl as keyof typeof LEGACY_LEVEL_ELO)).toBe(elo);
    expect(engineProfile('hard').elo).toBe(LEGACY_LEVEL_ELO.hard);
    expect(toElo(NaN)).toBe(LEGACY_LEVEL_ELO.medium);
  });
  it('names tiers', () => {
    expect(tierForElo(2400).name).toBe('Warlord');
    expect(tierForElo(1350).name).toBe('Knight');
    expect(tierForElo(3000).name).toBe('Grandmaster');
    expect(eloLabel(2400)).toBe('Warlord · 2400');
    expect(AI_ELO_TIERS).toHaveLength(7);
    expect(legacyLevelForElo(600)).toBe('easy');
    expect(legacyLevelForElo(2600)).toBe('master');
  });
});

describe('choosing a weak move', () => {
  const info = (d: number, pv: number, score: string, mv: string) => `info depth ${d} seldepth ${d} multipv ${pv} score ${score} nodes 10 nps 1000 time 1 pv ${mv} e7e5`;
  it('parses info lines and keeps only the deepest iteration', () => {
    expect(parseInfo(info(3, 2, 'cp -35', 'd2d4'))).toEqual({ depth: 3, multipv: 2, cp: -35, uci: 'd2d4' });
    expect(parseInfo(info(3, 1, 'mate 2', 'd1h5'))?.cp).toBe(1500);
    expect(parseInfo('info string hello')).toBeNull();
    expect(parseInfo('info depth 2 multipv 1 score cp 10 lowerbound pv e2e4')).toBeNull();
    const c = collectCandidates([info(1, 1, 'cp 10', 'a2a3'), info(2, 2, 'cp -20', 'd2d4'), info(2, 1, 'cp 30', 'e2e4')]);
    expect(c).toEqual([{ uci: 'e2e4', cp: 30 }, { uci: 'd2d4', cp: -20 }]);
    expect(collectCandidates([info(2, 1, 'cp 30', 'e2e4'), info(2, 2, 'cp 0', 'd2d4')], 1)).toHaveLength(1);
  });
  it('softmax favours better lines, flatter at higher temperature', () => {
    const items = [{ cp: 100, id: 'a' }, { cp: 0, id: 'b' }];
    const frac = (T: number) => { const r = mulberry32(7); let a = 0; for (let i = 0; i < 4000; i++) if (softmaxPick(items, T, r).id === 'a') a++; return a / 4000; };
    expect(softmaxPick(items, 0, Math.random).id).toBe('a');
    expect(frac(20)).toBeGreaterThan(0.98);
    expect(frac(300)).toBeGreaterThan(0.5);
    expect(frac(300)).toBeLessThan(0.65);
  });
  it('random-move probability is honoured and the result is always legal', () => {
    const legal = ['a2a3', 'b2b3', 'c2c3', 'd2d4', 'e2e4', 'g1f3'];
    const cands = [{ uci: 'e2e4', cp: 40 }, { uci: 'd2d4', cp: 30 }];
    const p = engineProfile(400);
    const r = mulberry32(3);
    let randoms = 0; const N = 4000;
    for (let i = 0; i < N; i++) {
      const mv = chooseWeakMove(cands, legal, 'e2e4', p, r);
      expect(legal).toContain(mv);
      if (!cands.some((c) => c.uci === mv)) randoms++;
    }
    // random picks that land on a candidate are indistinguishable, so the observed rate sits a little below p * (1 - 2/6)
    expect(randoms / N).toBeGreaterThan(p.randomMoveProb * 0.5);
    expect(randoms / N).toBeLessThan(p.randomMoveProb);
    expect(chooseWeakMove([], legal, 'g1f3', p, () => 0.99)).toBe('g1f3');
  });
});
