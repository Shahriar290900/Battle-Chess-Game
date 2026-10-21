// Bishop - the spell (choreography §3). Stays put or advances to 1.5 units; channels at socket_cast for
// 0.6 s, then Emberhold: censer swing releases a rolling fire wave, the target cracks with glowing seams
// and bursts; Rime: runes converge into a beam, the target freezes (frost sweep) then shatters.
// The bishop glides onto the square after the burst.
import { Vector3 } from 'three';
import { flatDist, socketPos } from '../common';
import { overShoulder } from '../shots';
import { HIT_STOP_MS, MAGNITUDE, TRAUMA, type Choreography } from './types';

const CHANNEL = 0.6;

export const bishop: Choreography = (e) => {
  const { stage, attacker, defender, faction, D, dir } = e;
  const ember = faction === 'emberhold';
  const approachAt = e.t0;
  let t = approachAt;
  if (flatDist(e.A, e.S) > 0.1) {
    if (e.quick) stage.place(attacker, e.S, t);
    else t = stage.walk(attacker, e.A, e.S, t, { speed: 2.2, minDur: 0.4 });
  }

  const a = e.placeAttack(t);
  const channelEnd = Math.min(a.attackAt + CHANNEL, a.impactAt - 0.1);
  const travel = Math.max(0.15, a.impactAt - channelEnd);

  // channel: gathering particles at socket_cast
  stage.at(a.attackAt, () => {
    stage.bus('spell', { faction });
    const cast = socketPos(attacker, 'socket_cast', new Vector3());
    stage.emit(ember ? 'embers' : 'iceGlitter', cast, { follow: attacker.sockets.socket_cast ?? attacker.sockets.socket_weapon_R ?? attacker.root, duration: CHANNEL, count: 30, scale: 0.7 });
  });

  // release: fire wave along the diagonal / frost beam
  stage.at(channelEnd, () => {
    const cast = socketPos(attacker, 'socket_cast', new Vector3());
    const len = Math.max(0.5, flatDist(cast, D));
    const to = D.clone().setY(0.8).sub(cast).normalize();
    if (ember) stage.emit('fireWave', cast, { direction: dir.clone(), duration: travel, speed: len / travel, count: 60, spread: 0.25, scale: 1 });
    else stage.emit('frostBeam', cast, { direction: to, duration: travel, speed: len / travel, count: 60, spread: 0.08, scale: 1 });
  });

  // hit: glowing cracks (ember) / freeze (frost); HitReact held; shatter follows
  const sweepDur = ember ? 0.5 : 0.4;
  stage.at(a.impactAt, () => stage.safe(() => e.ctx.fx.sweep(defender, ember ? 'ember' : 'frost', sweepDur)));

  const shatterDelay = sweepDur + 0.05;
  const r = e.resolve(a.impactAt + 0.12 + shatterDelay + 0.1, e.S, { after: a.end });
  return {
    approachAt, attackAt: a.attackAt, impactAt: a.impactAt, resolveAt: r.resolveAt, walkEnd: r.walkEnd, end: r.end,
    cues: [{ at: 0, shot: overShoulder(e.inputs) }],
    shatter: { magnitude: MAGNITUDE.bishop }, trauma: TRAUMA.bishop, hitStopMs: HIT_STOP_MS.bishop, heavy: false,
    shatterDelay, holdHitReact: true,
  };
};
