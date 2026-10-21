// Test harness: fake timers are installed BEFORE gsap and the cinematics modules load, so gsap's ticker
// (setTimeout based in node) runs on the fake clock and tests can advance it deterministically.
import { vi } from 'vitest';

vi.useFakeTimers();

export const { gsap } = await import('gsap');
export const { createSequencePlayer } = await import('../../src/cinematics');

gsap.ticker.lagSmoothing(0);

/** Advance the fake clock in ~frame steps until `p` settles or `maxMs` of fake time passes. */
export async function runUntil(p: Promise<unknown>, maxMs = 40000, step = 33): Promise<{ settled: boolean; elapsed: number }> {
  let settled = false;
  void p.then(() => { settled = true; }, () => { settled = true; });
  let elapsed = 0;
  await vi.advanceTimersByTimeAsync(0);
  while (!settled && elapsed < maxMs) {
    await vi.advanceTimersByTimeAsync(step);
    elapsed += step;
  }
  return { settled, elapsed };
}

/** Let leftover timers (fragment fail-safes, restore tweens, dissolves) run out. */
export async function drain(ms = 8000): Promise<void> {
  for (let i = 0; i < ms / 100; i++) await vi.advanceTimersByTimeAsync(100);
}

export async function advance(ms: number, step = 33): Promise<void> {
  for (let t = 0; t < ms; t += step) await vi.advanceTimersByTimeAsync(step);
}
