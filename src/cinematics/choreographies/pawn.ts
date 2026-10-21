// Pawn - melee duel (choreography §3). Emberhold Shieldbearer: draw, shield-bash stagger, overhead chop.
// Rime Thrall: cleaver drag-scrape (frost trail on the floor), lunging two-hand hack.
// En passant: sidestep along the rank, horizontal slash, then step forward onto `to`.
import { Vector3 } from 'three';
import { lowSide } from '../shots';
import { HIT_STOP_MS, MAGNITUDE, TRAUMA, type Choreography } from './types';
import { windUp, burstAt, burstAtSocket, trailBetween } from './util';

export const pawn: Choreography = (e) => {
  const { stage, attacker, defender, dir, D } = e;
  const approachAt = e.t0;
  let t = approachAt;
  let from = e.A.clone();

  if (e.isEnPassant) {
    // sidestep along the rank, away from the victim, to make room for the horizontal slash
    const P = e.A.clone().addScaledVector(dir, -0.35);
    t = stage.moveTo(attacker, P, t, e.quick ? 0.1 : 0.25, 'power2.out');
    from = P;
  }

  if (e.quick) {
    stage.place(attacker, e.S, t);
  } else if (e.faction === 'rime') {
    const walkEnd = t + Math.max(0.35, from.distanceTo(e.S) / 2.2);
    trailBetween(e, t, walkEnd + 0.9);
    for (let k = 0; k < 3; k++) burstAt(e, t + (k + 1) * (walkEnd - t) / 4, 'frostMist', from.clone().lerp(e.S, (k + 1) / 4), { count: 4, scale: 0.5 });
    t = stage.walk(attacker, from, e.S, t, { speed: 2.2, minDur: 0.35 });
    burstAt(e, t, 'frostMist', e.S, { count: 6, scale: 0.6 });
    stage.at(t, () => e.ctx.fx.decal(e.S.clone(), 'frost')); // cleaver drag-scrape mark
  } else {
    t = stage.walk(attacker, from, e.S, t, { speed: 2.2, minDur: 0.35 });
  }

  if (e.faction === 'emberhold') {
    // draw: hand to hip, 0.3 s
    burstAtSocket(e, t + 0.12, 'sparks', 'socket_weapon_R', { count: 8, scale: 0.5 });
    t += e.quick ? 0.15 : 0.3;
  }

  const a = e.placeAttack(t);
  windUp(e, a.attackAt, a.impactAt);
  const imp = a.impactAt - a.attackAt;

  if (e.faction === 'emberhold') {
    // shield-bash staggers the target just before the chop lands
    stage.moveTo(defender, new Vector3(D.x + dir.x * 0.14, 0, D.z + dir.z * 0.14), a.attackAt + imp * 0.3, 0.12, 'power2.out');
    burstAt(e, a.attackAt + imp * 0.3, 'sparks', D.clone().addScaledVector(dir, -0.3), { count: 6, scale: 0.4 }, 0.7);
    burstAtSocket(e, a.impactAt, 'sparks', 'socket_impact', { count: 16, scale: 0.6 });
  } else {
    burstAtSocket(e, a.impactAt, 'iceGlitter', 'socket_impact', { count: 16, scale: 0.6 });
  }

  const r = e.resolve(a.impactAt + 0.35, e.S, { after: a.end });
  return {
    approachAt, attackAt: a.attackAt, impactAt: a.impactAt, resolveAt: r.resolveAt, walkEnd: r.walkEnd, end: r.end,
    cues: [{ at: 0, shot: lowSide(e.inputs) }],
    shatter: { magnitude: MAGNITUDE.pawn }, trauma: TRAUMA.pawn, hitStopMs: HIT_STOP_MS.pawn, heavy: false,
  };
};
