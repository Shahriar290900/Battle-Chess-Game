// Queen - the summoned great-weapon (choreography §3). Hero orbit from behind the queen.
// 1. summon (0.6 s): particles spiral from the pedestal into socket_weapon_R, weapon_summon scales 0 -> 1.15 -> 1
// 2. advance with a ribbon trail
// 3. Emberhold: spin + overhead ground slam (shockwave, fire column, debris). Rime: gliding sweeping cut that
//    leaves a frozen crescent; the target shatters along the cut plane.
// 4. the weapon dissolves after Victory.
import { Vector3 } from 'three';
import { WEAPON_SUMMON_NODE } from '../../contracts';
import { lerp, socketPos, TAU } from '../common';
import { HIT_STOP_MS, MAGNITUDE, TRAUMA, type Choreography } from './types';
import { windUp, burstAt, trailBetween } from './util';

export const queen: Choreography = (e) => {
  const { stage, attacker, faction, D, dir, perp } = e;
  const ember = faction === 'emberhold';
  const node = attacker.model.getObjectByName(WEAPON_SUMMON_NODE);
  const approachAt = e.t0;
  let t = approachAt;

  // ---- 1. summon
  const summon = e.quick ? 0.4 : 0.6;
  stage.at(t, () => {
    if (node) node.visible = true;
    stage.bus('summon', { faction });
    stage.emit('summonSpiral', e.A.clone(), { duration: summon, count: 36, scale: 1, follow: attacker.sockets.socket_weapon_R });
  });
  stage.proxy(t, summon * 0.75, 'power2.out', (p) => attacker.setWeaponSummon(1.15 * p));
  stage.proxy(t + summon * 0.75, summon * 0.25, 'power1.out', (p) => attacker.setWeaponSummon(1.15 - 0.15 * p));
  stage.at(t + summon, () => stage.emit(ember ? 'embers' : 'iceGlitter', socketPos(attacker, 'socket_weapon_R', new Vector3()), { count: 18, scale: 0.8 }));
  t += summon;

  // ---- 2. advance with the weapon trailing
  const G0 = D.clone().addScaledVector(dir, -0.9).addScaledVector(perp, -0.9);
  const G1 = D.clone().addScaledVector(dir, -0.6).addScaledVector(perp, 0.9);
  const goal = ember ? e.S : G0;
  const advStart = t;
  if (e.quick) stage.place(attacker, goal, t);
  else t = stage.walk(attacker, e.A, goal, t, { speed: 2.2, minDur: 0.5, maxDur: 1.4 });

  // ---- 3. strike
  const a = e.placeAttack(t);
  windUp(e, a.attackAt, a.impactAt);
  trailBetween(e, advStart, a.impactAt + 0.5);
  let from = goal;
  let cutNormal: Vector3 | undefined;

  if (ember) {
    // spin, then the overhead slam
    let base = Number.NaN;
    stage.proxy(Math.max(t, a.impactAt - 0.95), 0.55, 'power2.inOut', (p) => {
      if (Number.isNaN(base)) base = attacker.getYaw();
      attacker.setYaw(base + TAU * p);
    });
    stage.at(a.impactAt, () => {
      e.ctx.fx.shockwave(D.clone(), faction, 3.2);
      e.ctx.fx.decal(D.clone(), 'scorch');
      e.ctx.fx.decal(D.clone(), 'crack');
      stage.safe(() => e.ctx.fx.column(D.clone(), faction, 0.9));
    });
    burstAt(e, a.impactAt, 'sparks', D, { count: 60, speed: 6, spread: 1.4, scale: 1 }, 0.3);
    burstAt(e, a.impactAt, 'embers', D, { count: 50, speed: 5, spread: 1.6, scale: 1 }, 0.2);
    burstAt(e, a.impactAt, 'smoke', D, { count: 10, scale: 1.4 }, 0.2);
  } else {
    // gliding sweeping cut: slide across the front of the target while the glaive arcs through it
    const gs = Math.max(t, a.impactAt - 0.55);
    stage.arc(attacker, (p, out) => out.set(lerp(G0.x, G1.x, p), 0, lerp(G0.z, G1.z, p)), gs, 0.9, 'power1.inOut', { faceTarget: D });
    for (let k = 0; k < 6; k++) {
      const u = k / 5;
      stage.at(a.impactAt - 0.15 + u * 0.3, () => {
        const pos = D.clone().addScaledVector(perp, lerp(-0.8, 0.8, u)).addScaledVector(dir, -0.25);
        pos.y = 1.25 - 0.55 * u; // frozen crescent hangs in the air along the sweep
        stage.emit('iceGlitter', pos, { count: 8, scale: 0.7, speed: 0.6, spread: 0.1 });
      });
    }
    stage.at(a.impactAt, () => { e.ctx.fx.shockwave(D.clone(), faction, 1.8); e.ctx.fx.decal(D.clone(), 'frost'); });
    from = G1;
    cutNormal = new Vector3().addScaledVector(dir, 0.2).addScaledVector(perp, 0.25).setY(0.95).normalize();
  }

  // ---- 4. resolve, then the weapon dissolves
  const r = e.resolve(a.impactAt + 0.45, from, { after: a.end, victoryMax: e.quick ? 0.6 : 1.0 });
  const dissolveAt = Math.max(r.walkEnd, r.end - 0.3);
  const dissolveDur = e.quick ? 0.4 : 0.6;
  stage.at(dissolveAt, () => {
    if (node) stage.safe(() => e.ctx.fx.dissolve(node, faction, dissolveDur));
  });
  if (!node) stage.proxy(dissolveAt, dissolveDur, 'power1.in', (p) => attacker.setWeaponSummon(1 - p));
  stage.onSettle(() => { if (node) node.visible = true; attacker.setWeaponSummon(0); });

  return {
    approachAt, attackAt: a.attackAt, impactAt: a.impactAt, resolveAt: r.resolveAt, walkEnd: r.walkEnd,
    end: Math.max(r.end, dissolveAt + dissolveDur),
    cues: [{ at: 0, shot: e.pickShot('heroOrbit', { orbitSeconds: e.quick ? 1.2 : 1.8, attackerAt: from }) }],
    shatter: { magnitude: MAGNITUDE.queen, cutNormal }, trauma: TRAUMA.queen, hitStopMs: HIT_STOP_MS.queen, heavy: true,
    decal: ember ? 'scorch' : 'frost',
  };
};
