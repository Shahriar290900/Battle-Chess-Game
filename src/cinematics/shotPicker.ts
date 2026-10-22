// Shot selection: build 3 candidate angles per shot type and keep the one with the fewest occluders.
import { Vector3 } from 'three';
import type { PieceActor } from '../contracts';
import { countOccluders } from './occluders';
import {
  constrainPose, heroOrbit, lowHero, lowSide, newPose, overShoulder, topDownSlam, trackingLeap,
  type Shot, type ShotInputs, type ShotName,
} from './shots';

export interface PickOptions { orbitSeconds?: number; /** Where the attacker stands during the strike (default: its live position). */ attackerAt?: Vector3 }

function build(name: ShotName, inputs: ShotInputs, o: PickOptions): Shot {
  switch (name) {
    case 'lowSide': return lowSide(inputs);
    case 'overShoulder': return overShoulder(inputs);
    case 'topDownSlam': return topDownSlam(inputs);
    case 'trackingLeap': return trackingLeap(inputs);
    case 'heroOrbit': return heroOrbit(inputs, { duration: o.orbitSeconds });
    case 'lowHero': return lowHero(inputs);
    default: throw new Error(`cannot pick shot ${name}`);
  }
}

/** Score a candidate: lower is better. Occluders block the fighters, `near` pieces would fill the frame. */
export function scoreShot(shot: Shot, samples: readonly number[], attacker: Vector3, defender: Vector3, bystanders: readonly PieceActor[], all: readonly PieceActor[]): number {
  const pose = newPose();
  const targets = [new Vector3(attacker.x, 0.8, attacker.z), new Vector3(defender.x, 0.8, defender.z)];
  let score = 0;
  for (const t of samples) {
    shot.pose(t, pose);
    constrainPose(pose, all);
    const { occluders, near } = countOccluders(pose.position, targets, bystanders);
    score += occluders * 10 + near * 6;
  }
  return score;
}

/**
 * Pick the clearest of three angles (seat side / opposite side / farther+higher). The returned shot follows the
 * live inputs; only the choice is made from static positions. Ties prefer the default angle.
 */
export function pickShot(name: ShotName, live: ShotInputs, bystanders: readonly PieceActor[], all: readonly PieceActor[], o: PickOptions = {}): Shot {
  const A = o.attackerAt ?? live.attacker();
  const D = live.defender();
  const stat: ShotInputs = { ...live, attacker: () => A, defender: () => D };
  const samples = name === 'heroOrbit' ? [0, (o.orbitSeconds ?? 1.8)] : [0, 1.5];
  let best = 0; let bestScore = Infinity;
  for (const v of [0, 1, 2] as const) {
    const sc = scoreShot(build(name, { ...stat, variant: v }, o), samples, A, D, bystanders, all) + v * 0.5;
    if (sc < bestScore) { bestScore = sc; best = v; }
  }
  return build(name, { ...live, variant: best as 0 | 1 | 2 }, o);
}
