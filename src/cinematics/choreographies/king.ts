// King - the decisive blow (choreography §3). Slow heavy walk (speed 1.4). Emberhold: lifts the greatsword
// overhead for a single cleave, time slows to 0.2 for 0.8 s. Rime: raises a fist, ice spikes erupt under the
// target and lift it, then a backhand shatters it mid-air.
import { Vector3 } from 'three';
import { socketPos } from '../common';
import type { WarpPlan } from '../timeWarp';
import { HIT_STOP_MS, MAGNITUDE, TRAUMA, type Choreography } from './types';
import { windUp, burstAt, burstAtSocket } from './util';

export const king: Choreography = (e) => {
  const { stage, attacker, defender, faction, D } = e;
  const ember = faction === 'emberhold';
  const approachAt = e.t0;
  let t = approachAt;
  if (e.quick) stage.place(attacker, e.S, t);
  else t = stage.walk(attacker, e.A, e.S, t, { speed: 1.4, minDur: 0.6, maxDur: 2.2, stepEvery: 0.5, dust: true, thud: 0.08 });

  const a = e.placeAttack(t);
  windUp(e, a.attackAt, a.impactAt);
  let warp: WarpPlan | undefined;

  if (ember) {
    // time slows to 0.2 for 0.8 s at the cleave
    warp = { segments: [{ scale: 0.03, seconds: HIT_STOP_MS.king / 1000 }, { scale: 0.2, seconds: e.quick ? 0.35 : 0.8 }], ramp: 0.6 };
    burstAtSocket(e, a.impactAt - 0.35, 'embers', 'socket_weapon_R', { count: 24, scale: 0.8 }); // blade kindles overhead
    stage.at(a.impactAt, () => {
      e.ctx.fx.shockwave(D.clone(), faction, 2.0);
      e.ctx.fx.decal(D.clone(), 'scorch');
    });
    burstAt(e, a.impactAt, 'sparks', D, { count: 40, speed: 6, spread: 1.2 }, 0.7);
    burstAt(e, a.impactAt, 'smoke', D, { count: 6, scale: 1.2 }, 0.3);
  } else {
    // ice spikes erupt under the target and lift it; the backhand then shatters it mid-air
    const spikesAt = Math.max(a.attackAt, a.impactAt - 0.8);
    stage.at(spikesAt, () => {
      stage.bus('spell', { faction });
      stage.bus('armour:hit', { faction: e.defFaction, heavy: true }); // the spikes punch up through the plate
      stage.safe(() => e.ctx.fx.iceSpikes(D.clone(), 7));
      e.ctx.fx.decal(D.clone(), 'frost');
    });
    stage.lift(defender, 0.55, spikesAt, 0.5, 'back.out(1.6)');
    burstAt(e, spikesAt, 'iceGlitter', D, { count: 24, speed: 3, spread: 0.8 }, 0.2);
    stage.at(a.impactAt, () => {
      const p = socketPos(attacker, 'socket_impact', new Vector3());
      stage.emit('iceGlitter', p, { count: 20, scale: 0.8 });
      e.ctx.fx.shockwave(D.clone(), faction, 1.6);
    });
  }

  const r = e.resolve(a.impactAt + 0.45, e.S, { after: a.end });
  return {
    approachAt, attackAt: a.attackAt, impactAt: a.impactAt, resolveAt: r.resolveAt, walkEnd: r.walkEnd, end: r.end,
    cues: [{ at: 0, shot: e.pickShot('lowHero', { attackerAt: e.S }), blend: 0.7 }],
    shatter: { magnitude: MAGNITUDE.king }, trauma: TRAUMA.king, hitStopMs: HIT_STOP_MS.king, heavy: true, warp,
  };
};
