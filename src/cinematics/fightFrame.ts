// Per-frame presentation of a borrowed camera: shot driver + lighting rig + occluder fading.
import { Vector3 } from 'three';
import type { Faction, PieceActor } from '../contracts';
import type { CameraDriver } from './cameraDriver';
import { LightRig } from './lightRig';
import { OccluderFader } from './occluders';
import type { Stage } from './stage';

export interface FightFrameOptions {
  driver: CameraDriver | null;
  /** Live world positions to keep unobstructed (torso height is added). */
  focus: () => Vector3[];
  keyFaction: Faction; rimFaction: Faction;
  /** Pieces allowed to be faded / dimmed. */
  bystanders: () => readonly PieceActor[];
  lights?: boolean;
}

export class FightFrame {
  readonly rig: LightRig | null;
  readonly fader: OccluderFader;
  private released = false;
  private readonly targets: Vector3[] = [];
  private readonly cam = new Vector3();

  constructor(private readonly stage: Stage, private readonly o: FightFrameOptions) {
    this.rig = o.lights === false ? null : new LightRig(stage.ctx.board.scene, o.keyFaction, o.rimFaction);
    this.fader = new OccluderFader(o.bystanders);
    stage.onSettle(() => this.dispose());
  }

  /** Fade the lights in over `dur` starting at `at`. */
  fadeIn(at: number, dur = 0.3): void { if (this.rig) this.stage.proxy(at, dur, 'power1.inOut', (p) => this.rig!.setAmount(p)); }
  fadeOut(at: number, dur = 0.3): void {
    if (this.rig) { let from = -1; this.stage.proxy(at, dur, 'power1.inOut', (p) => { if (from < 0) from = this.rig!.currentAmount || 1; this.rig!.setAmount(from * (1 - p)); }); }
  }
  /** Camera handed back: restore occluders and stop shot updates. */
  release(): void { this.released = true; }

  /** Call from the master timeline's onUpdate. */
  update(t: number): void {
    const o = this.o;
    const pose = o.driver ? o.driver.update(t) : null;
    this.cam.copy(pose ? pose.position : this.stage.ctx.camera.camera.position);
    const f = o.focus();
    this.targets.length = 0;
    for (const p of f) this.targets.push(new Vector3(p.x, p.y + 0.8, p.z));
    this.rig?.update(f[0], f[f.length - 1], this.cam);
    this.fader.update(t, this.cam, this.targets, this.released || !o.driver);
  }

  dispose(): void {
    this.fader.restoreAll();
    this.rig?.dispose();
  }
}
