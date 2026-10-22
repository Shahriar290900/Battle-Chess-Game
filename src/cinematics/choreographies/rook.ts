// Rook - the slam (choreography §3). Hops 0.25 s per square with a puff on each landing, rises 1.2, hangs
// 0.15 s, crashes down. Emberhold: brazier fire burst on landing. Rime: 3 crown shards pin the target,
// then the tower topples onto it. Shockwave ring + board crack decal.
import { Vector3 } from 'three';
import { socketPos } from '../common';
import { HIT_STOP_MS, MAGNITUDE, TRAUMA, type Choreography } from './types';
import { burstAt, burstAtSocket } from './util';

export const rook: Choreography = (e) => {
  const { stage, attacker, dir, D, faction } = e;
  const puff = faction === 'emberhold' ? 'dustPuff' : 'frostMist';
  const n = Math.max(1, Math.round(e.dist));
  const approachAt = e.t0;
  let t = approachAt;
  const last = e.A.clone().addScaledVector(dir, n - 1);

  if (e.quick) {
    stage.place(attacker, last, t);
  } else {
    let prev = e.A.clone();
    for (let i = 1; i < n; i++) {
      const P = e.A.clone().addScaledVector(dir, i);
      t = stage.hop(attacker, prev, P, t, 0.25, 0.28, { puff });
      prev = P;
    }
  }

  const a = e.placeAttack(t);
  const imp = a.impactAt - a.attackAt;
  const hang = 0.15;
  const rise = Math.max(0.2, imp - 0.33);
  const slam = Math.max(0.1, imp - rise - hang);
  const slamAt = a.attackAt + rise + hang;

  stage.lift(attacker, 1.2, a.attackAt, rise, 'power2.out');
  stage.moveTo(attacker, e.S, a.attackAt, rise + hang, 'power1.inOut');
  stage.lift(attacker, 0, slamAt, slam, 'power3.in');

  if (faction === 'rime') {
    // 3 crown shards pin the target, then the tower topples onto it
    for (let k = 0; k < 3; k++) {
      stage.at(a.attackAt + rise * 0.55 + k * 0.07, () => {
        const from = socketPos(attacker, 'socket_head', new Vector3());
        const d = D.clone().sub(from).normalize();
        stage.emit('iceGlitter', from, { direction: d, count: 10, speed: 8, spread: 0.12, scale: 0.7 });
      });
    }
    burstAt(e, a.attackAt + rise + hang * 0.6, 'iceGlitter', D, { count: 12, scale: 0.6 }, 0.2);
    stage.tilt(attacker, 0.5, slamAt, slam, 'power3.in');
    stage.tilt(attacker, 0, a.impactAt + 0.05, 0.35, 'power2.out');
  }

  // landing: shockwave ring, crack decal, faction burst
  stage.at(a.impactAt, () => {
    e.ctx.fx.shockwave(D.clone(), faction, 2.6);
    e.ctx.fx.decal(D.clone(), 'crack');
  });
  if (faction === 'emberhold') {
    burstAt(e, a.impactAt, 'embers', D, { count: 40, speed: 4, spread: 1.2, scale: 1 }, 0.3);
    burstAtSocket(e, a.impactAt, 'sparks', 'socket_impact', { count: 24, scale: 0.8 });
    burstAt(e, a.impactAt, 'smoke', D, { count: 8, scale: 1 }, 0.2);
  } else {
    burstAt(e, a.impactAt, 'iceGlitter', D, { count: 36, speed: 4, spread: 1.2, scale: 1 }, 0.3);
    burstAt(e, a.impactAt, 'frostMist', D, { count: 10, scale: 1.2 }, 0.1);
  }

  const r = e.resolve(a.impactAt + 0.45, e.S, { after: a.end });
  return {
    approachAt, attackAt: a.attackAt, impactAt: a.impactAt, resolveAt: r.resolveAt, walkEnd: r.walkEnd, end: r.end,
    cues: [
      { at: 0, shot: e.pickShot('topDownSlam') },
      { at: slamAt, shot: e.pickShot('lowSide', { attackerAt: e.S }), blend: 0 }, // cut on the landing
    ],
    shatter: { magnitude: MAGNITUDE.rook }, trauma: TRAUMA.rook, hitStopMs: HIT_STOP_MS.rook, heavy: true,
    decal: 'crack',
  };
};
