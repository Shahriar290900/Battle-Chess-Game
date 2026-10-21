import type { Vector3 } from 'three';
import type { Faction, PieceActor, SequenceContext } from '../../contracts';
import type { Stage } from '../stage';
import type { ShotCue, ShotInputs } from '../shots';
import type { WarpPlan } from '../timeWarp';

export type DecalKind = 'crack' | 'scorch' | 'frost';

export interface AttackPlacement {
  /** Master time the attacker's Attack timeline starts. */
  attackAt: number;
  /** Master time of the "impact" label (attackAt + clip impact time). */
  impactAt: number;
  /** Master time the Attack timeline ends. */
  end: number;
}

export interface ResolvePlacement {
  resolveAt: number;
  /** Time the attacker is standing on `to` (cleanup starts here). */
  walkEnd: number;
  /** Time Victory finishes. */
  end: number;
}

/** Everything a per-role choreography needs; built by the capture director. */
export interface CaptureEnv {
  stage: Stage;
  ctx: SequenceContext;
  attacker: PieceActor;
  defender: PieceActor;
  faction: Faction;
  defFaction: Faction;
  /** captureMode === 'quick': skip the approach walk. */
  quick: boolean;
  /** Attacker square centre / defender position / destination square centre (y = 0). */
  A: Vector3; D: Vector3; To: Vector3;
  /** Unit horizontal vector attacker -> defender and its perpendicular toward the camera seat. */
  dir: Vector3; perp: Vector3;
  /** Horizontal distance attacker -> defender. */
  dist: number;
  /** extras.strikeRange. */
  strikeRange: number;
  /** Where the attacker stands to strike: D - dir * strikeRange (or A when already close enough). */
  S: Vector3;
  /** Master time at which the choreography may begin (after setup + face). */
  t0: number;
  isEnPassant: boolean;
  seatZ: 1 | -1;
  inputs: ShotInputs;
  /** Nest attacker.attackTimeline() so its impact lands at max(earliest + impact, desiredImpact). Emits attack:whoosh. */
  placeAttack(earliest: number, desiredImpact?: number): AttackPlacement;
  /** Slide the attacker from `from` onto `to` at `at`, face rest yaw, then play Victory once the Attack is done (capped). */
  resolve(at: number, from: Vector3, o?: { victoryMax?: number; /** Victory waits until this time (Attack end). */ after?: number }): ResolvePlacement;
}

export interface ShatterPlan {
  magnitude: number;
  /** Overrides the attacker->defender / weapon-motion derived direction. */
  impulseDir?: Vector3;
  cutNormal?: Vector3;
}

/** The result of a choreography: timing landmarks plus the feel parameters the director applies. */
export interface ChoreoPlan {
  approachAt: number;
  attackAt: number;
  impactAt: number;
  resolveAt: number;
  /** Attacker stands on `to`; cleanup (camera restore, undim) starts here. */
  walkEnd: number;
  /** Everything the attacker does is finished. */
  end: number;
  cues: ShotCue[];
  shatter: ShatterPlan;
  /** camera.shake trauma 0.35 .. 0.8. */
  trauma: number;
  hitStopMs: number;
  heavy: boolean;
  /** Replaces the default hit-stop / slow-mo script (king cleave). */
  warp?: WarpPlan;
  /** Extra seconds between the 0.12 s HitReact and the shatter (bishop freeze / crack). */
  shatterDelay?: number;
  /** Hold HitReact mid-pose until the shatter (frozen / cracking). */
  holdHitReact?: boolean;
  decal?: DecalKind;
}

export type Choreography = (env: CaptureEnv) => ChoreoPlan;

export const HIT_STOP_MS = { pawn: 70, knight: 85, bishop: 85, rook: 100, queen: 110, king: 110 } as const;
export const TRAUMA = { pawn: 0.35, knight: 0.55, bishop: 0.5, rook: 0.8, queen: 0.8, king: 0.8 } as const;
export const MAGNITUDE = { pawn: 0.5, knight: 0.9, bishop: 0.8, rook: 1.4, queen: 1.5, king: 1.5 } as const;
