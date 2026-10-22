// Damped scalar spring, semi-implicit (symplectic) Euler. Stable while dt * omega < ~1, so callers substep.
export class Spring {
  x = 0;
  v = 0;
  /** omega^2 */
  k = 0;
  /** 2 * zeta * omega */
  c = 0;
  /** |x| clamp (v is zeroed against the stop). */
  lim = 1;
  constructor(freqHz = 3, zeta = 0.3, lim = 1) { this.tune(freqHz, zeta, lim); }
  tune(freqHz: number, zeta: number, lim: number): void {
    const w = 2 * Math.PI * freqHz;
    this.k = w * w;
    this.c = 2 * zeta * w;
    this.lim = lim;
  }
  /** Velocity change equivalent to a constant force `accel` held for dt (the steady-state offset is accel*gain). */
  kick(dv: number): void { this.v += dv; }
  step(h: number): void {
    if (this.x === 0 && this.v === 0) return;
    this.v += (-this.k * this.x - this.c * this.v) * h;
    this.x += this.v * h;
    if (this.x > this.lim) { this.x = this.lim; if (this.v > 0) this.v = 0; }
    else if (this.x < -this.lim) { this.x = -this.lim; if (this.v < 0) this.v = 0; }
    if (this.x < 1e-6 && this.x > -1e-6 && this.v < 1e-4 && this.v > -1e-4) { this.x = 0; this.v = 0; } // sleep
  }
  reset(): void { this.x = 0; this.v = 0; }
}

/** Max internal step; frames are split into ceil(dt / SUBSTEP) equal substeps. */
export const SUBSTEP = 1 / 120;
/** Longest simulated frame; longer real dt (tab switch, hitch) is clamped so springs never explode. */
export const MAX_SIM_DT = 0.1;
