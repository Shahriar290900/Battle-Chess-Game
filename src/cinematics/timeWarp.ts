// Real-time driven slow-motion. The classic bug: tweening gsap.globalTimeline.timeScale() with a
// tween that itself lives in the global timeline slows the tween too. Here the global time scale is
// driven from a gsap.ticker listener using REAL elapsed milliseconds, so ramps always take the real
// time asked for, no matter how slow the timeline gets.
import { gsap } from 'gsap';

/** A stretch of real (wall-clock) seconds played at a constant time scale. */
export interface WarpSegment { scale: number; seconds: number }

export interface WarpPlan { segments: WarpSegment[]; /** Real seconds to ramp from the last scale back to 1. */ ramp: number }

const smooth = (u: number) => u * u * (3 - 2 * u);

export class TimeWarp {
  private plan: WarpPlan | null = null;
  private elapsed = 0;
  private total = 0;
  private attached = false;
  private readonly listener = (_time: number, deltaMs: number) => this.tick(deltaMs / 1000);

  get active(): boolean { return this.plan !== null; }

  /** Start (or replace) a warp script. The first segment's scale is applied immediately. */
  play(plan: WarpPlan): void {
    this.plan = plan;
    this.elapsed = 0;
    this.total = plan.segments.reduce((s, g) => s + g.seconds, 0) + plan.ramp;
    if (!this.attached) { gsap.ticker.add(this.listener); this.attached = true; }
    gsap.globalTimeline.timeScale(Math.max(0.01, this.scaleAt(0)));
  }

  /** Time scale at `e` real seconds into the current script. */
  scaleAt(e: number): number {
    const plan = this.plan;
    if (!plan) return 1;
    let t = e;
    let last = 1;
    for (const seg of plan.segments) {
      if (t < seg.seconds) return seg.scale;
      t -= seg.seconds;
      last = seg.scale;
    }
    if (plan.ramp <= 0) return 1;
    const u = Math.min(1, t / plan.ramp);
    return last + (1 - last) * smooth(u);
  }

  private tick(dt: number): void {
    if (!this.plan) return;
    this.elapsed += Math.min(dt, 0.1); // a hitch must not swallow the hit-stop
    if (this.elapsed >= this.total) { this.stop(); return; }
    gsap.globalTimeline.timeScale(Math.max(0.01, this.scaleAt(this.elapsed)));
  }

  /** End the script and put the global time scale back to exactly 1. */
  stop(): void {
    if (this.attached) { gsap.ticker.remove(this.listener); this.attached = false; }
    this.plan = null;
    gsap.globalTimeline.timeScale(1);
  }
}

/** Default hit-stop script: 0.03 for `hitStopMs`, 0.35 slow-mo for `tail`, ramp to 1 over 0.6 s. */
export function hitStopPlan(hitStopMs: number, slowSeconds = 0.25, ramp = 0.6): WarpPlan {
  return {
    segments: [
      { scale: 0.03, seconds: hitStopMs / 1000 },
      { scale: 0.35, seconds: slowSeconds },
    ],
    ramp,
  };
}
