import { gsap } from 'gsap';
import { PerspectiveCamera, Vector3 } from 'three';
import type { CameraRig, CinematicCameraHandle, Side } from '../../src/contracts';

export class SandboxCamera implements CameraRig {
  readonly camera = new PerspectiveCamera(40, 16 / 9, 0.1, 100);
  mode: 'follow' = 'follow';
  seat: Side = 'w';
  private pos = new Vector3(); private look = new Vector3(); private fov = 40;
  private trauma = 0; private time = 0;
  /** Last pose pushed by the director (for debugging/tests). */
  lastPose = { position: new Vector3(), lookAt: new Vector3(), fov: 40 };

  constructor() { this.toSeatInstant('w'); }
  private seatPose(side: Side) { return { pos: new Vector3(0, 9.6, side === 'w' ? 8.6 : -8.6), look: new Vector3(0, 0, 0), fov: 40 }; }
  private toSeatInstant(side: Side) { this.seat = side; const s = this.seatPose(side); this.pos.copy(s.pos); this.look.copy(s.look); this.fov = s.fov; this.apply(0); }
  setMode() {}
  async toSeat(side: Side, opts?: { instant?: boolean }) { if (opts?.instant) this.toSeatInstant(side); else { this.seat = side; await this.restore(1.0); } }
  borrow(): CinematicCameraHandle {
    gsap.killTweensOf(this.pos); gsap.killTweensOf(this.look);
    return {
      camera: this.camera,
      set: (p, l, f) => { this.pos.copy(p); this.look.copy(l); if (f) this.fov = f; this.lastPose.position.copy(p); this.lastPose.lookAt.copy(l); this.lastPose.fov = this.fov; },
    };
  }
  restore(duration = 1): Promise<void> {
    const s = this.seatPose(this.seat);
    gsap.killTweensOf(this.pos); gsap.killTweensOf(this.look);
    if (duration <= 0) { this.pos.copy(s.pos); this.look.copy(s.look); this.fov = s.fov; return Promise.resolve(); }
    return new Promise((resolve) => {
      const f = { fov: this.fov };
      gsap.to(this.pos, { x: s.pos.x, y: s.pos.y, z: s.pos.z, duration, ease: 'power2.inOut' });
      gsap.to(this.look, { x: s.look.x, y: s.look.y, z: s.look.z, duration, ease: 'power2.inOut' });
      gsap.to(f, { fov: s.fov, duration, ease: 'power2.inOut', onUpdate: () => { this.fov = f.fov; }, onComplete: () => { resolve(); } });
    });
  }
  shake(t: number) { this.trauma = Math.min(1, Math.max(this.trauma, t)); }
  resize(w: number, h: number) { this.camera.aspect = w / h; this.camera.updateProjectionMatrix(); }
  private apply(dt: number) {
    this.time += dt;
    this.trauma = Math.max(0, this.trauma - dt * 2);
    const s = this.trauma * this.trauma;
    this.camera.position.copy(this.pos);
    if (s > 0) this.camera.position.add(new Vector3(Math.sin(this.time * 61) * s * 0.35, Math.sin(this.time * 47 + 1) * s * 0.25, Math.sin(this.time * 53 + 2) * s * 0.35));
    this.camera.fov = this.fov; this.camera.updateProjectionMatrix();
    this.camera.lookAt(this.look);
  }
  update(dt: number) { this.apply(dt); }
}
