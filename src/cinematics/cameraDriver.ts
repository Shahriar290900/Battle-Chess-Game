// Drives a borrowed camera handle from a list of shot cues each time the master timeline updates.
import { Vector3 } from 'three';
import type { CinematicCameraHandle, PieceActor } from '../contracts';
import { smoothstep } from './common';
import { constrainPose, newPose, type ShotCue, type ShotPose } from './shots';

export class CameraDriver {
  private cues: ShotCue[] = [];
  private readonly seat: ShotPose = newPose();
  private readonly cur: ShotPose = newPose();
  private readonly prev: ShotPose = newPose();
  private readonly tmp: ShotPose = newPose();
  private readonly fwd = new Vector3();
  private blendIn = 0.6;
  /** Master time at which control was released (restore started); stops further updates. */
  released = false;
  /** Punch-in toward the impact: FOV tightens and the camera pushes in during the lead-up, then eases back. */
  private punch: { at: number; lead: number; fov: number; push: number } | null = null;
  /** Total number of poses pushed (used by tests/sandbox). */
  frames = 0;

  constructor(private readonly handle: CinematicCameraHandle, private readonly actors: () => readonly PieceActor[]) {
    const cam = handle.camera;
    this.seat.position.copy(cam.position);
    // look-at = where the camera's forward ray meets the board plane (fallback: 8 units ahead)
    cam.getWorldDirection(this.fwd);
    if (this.fwd.y < -0.05) this.seat.lookAt.copy(cam.position).addScaledVector(this.fwd, -cam.position.y / this.fwd.y);
    else this.seat.lookAt.copy(cam.position).addScaledVector(this.fwd, 8);
    this.seat.fov = cam.fov;
    this.cur.position.copy(this.seat.position); this.cur.lookAt.copy(this.seat.lookAt); this.cur.fov = this.seat.fov;
  }

  setCues(cues: ShotCue[], blendIn = 0.6): void {
    this.cues = [...cues].sort((a, b) => a.at - b.at);
    this.blendIn = blendIn;
  }

  setPunch(at: number, lead = 0.5, fov = 7, push = 0.45): void { this.punch = { at, lead, fov, push }; }

  /** Pose for master-time `t`; also pushes it to the handle unless released. */
  update(t: number): ShotPose {
    if (this.released || this.cues.length === 0) return this.cur;
    let idx = 0;
    for (let k = 0; k < this.cues.length; k++) if (this.cues[k].at <= t) idx = k;
    const cue = this.cues[idx];
    const pose = cue.shot.pose(Math.max(0, t - cue.at), this.tmp);
    const blend = idx === 0 ? this.blendIn : (cue.blend ?? 0);
    const since = t - cue.at;
    if (blend > 0 && since < blend) {
      const u = smoothstep(since / blend);
      if (idx === 0) this.mix(this.seat, pose, u);
      else {
        const before = this.cues[idx - 1];
        before.shot.pose(Math.max(0, t - before.at), this.prev);
        this.mix(this.prev, pose, u);
      }
    } else {
      this.cur.position.copy(pose.position); this.cur.lookAt.copy(pose.lookAt); this.cur.fov = pose.fov;
    }
    if (this.punch) {
      const { at, lead, fov, push } = this.punch;
      const k = t < at ? smoothstep((t - (at - lead)) / lead) : Math.max(0, 1 - (t - at) / 0.6) ** 2;
      if (k > 0) {
        this.fwd.copy(this.cur.lookAt).sub(this.cur.position);
        if (this.fwd.lengthSq() > 1e-6) this.cur.position.addScaledVector(this.fwd.normalize(), push * k);
        this.cur.fov = Math.max(20, this.cur.fov - fov * k);
      }
    }
    constrainPose(this.cur, this.actors());
    this.handle.set(this.cur.position, this.cur.lookAt, this.cur.fov);
    this.frames++;
    return this.cur;
  }

  private mix(a: ShotPose, b: ShotPose, u: number): void {
    this.cur.position.copy(a.position).lerp(b.position, u);
    this.cur.lookAt.copy(a.lookAt).lerp(b.lookAt, u);
    this.cur.fov = a.fov + (b.fov - a.fov) * u;
  }
}
