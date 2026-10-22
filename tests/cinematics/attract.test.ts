import { describe, expect, it } from 'vitest';
import { DEFAULT_SETTINGS } from '../../src/contracts';
import type { AttractContext } from '../../src/contracts';
import { advance, createSequencePlayer, drain, gsap } from './harness';
import { makeRig, mkMove } from './mocks';

const { createAttract, ATTRACT_START_FEN } = await import('../../src/cinematics');

function attractRig(settings: Partial<typeof DEFAULT_SETTINGS> = {}, kinematics = true) {
  const rig = makeRig(mkMove({ from: 'e2', to: 'e4', side: 'w', role: 'pawn' }), (b) => { b.syncToFen(ATTRACT_START_FEN); }, settings, { kinematics });
  const sequences = createSequencePlayer();
  const { move: _m, ...rest } = rig.ctx;
  void _m;
  const ctx: AttractContext = { ...rest, sequences };
  return { rig, ctx, sequences };
}

const eventNames = (rig: ReturnType<typeof attractRig>['rig']) => rig.events.map((e) => e.name);

describe('attract mode', () => {
  it('start() flies over the armies and plays staged duels; stop() restores everything', async () => {
    const { rig, ctx } = attractRig();
    const attract = createAttract(ctx);
    expect(attract.running).toBe(false);
    attract.start();
    expect(attract.running).toBe(true);
    attract.start(); // idempotent
    // 1) the flyover moves the (borrowed) camera along both lines and up over the board
    await advance(16000);
    expect(rig.camera.borrows).toBe(1);
    const ys = rig.camera.poses.map((p) => p.position.y);
    expect(Math.min(...ys)).toBeLessThan(1.3);   // low dolly
    expect(Math.max(...ys)).toBeGreaterThan(8);  // crane over the board
    expect(rig.camera.poses.every((p) => Number.isFinite(p.position.x + p.position.y + p.position.z) && p.position.y >= 0.6)).toBe(true);
    // 2) duels start after the flyover
    await advance(50000);
    expect(eventNames(rig)).toContain('capture:begin');
    expect(eventNames(rig)).toContain('capture:impact');
    // never emits game/turn events
    expect(eventNames(rig).some((n) => n.startsWith('game:') || n.startsWith('turn:'))).toBe(false);
    // stop mid-flight
    const stopped = attract.stop();
    await advance(4000);
    await stopped;
    expect(attract.running).toBe(false);
    await drain();
    expect(rig.board.syncCalls[rig.board.syncCalls.length - 1]).toBe(ATTRACT_START_FEN);
    expect(rig.board.allActors().length).toBe(32);
    expect(rig.camera.state).toBe('seat');
    expect(gsap.globalTimeline.timeScale()).toBe(1);
    expect(rig.board.scene.children.some((o) => o.name === 'cinematic_light_rig')).toBe(false);
    for (const a of rig.board.allActors()) {
      expect(a.fade).toBe(1); expect(a.dim).toBe(0);
      expect(gsap.getTweensOf([a.root.position, a.root.rotation, a.model.rotation]).length).toBe(0);
    }
    expect(rig.kin!.active.length).toBe(0);
    expect(rig.fx.trailsOpen).toBe(0);
    expect(rig.registry.outstanding.size).toBe(0);
    // the camera stays quiet after stop
    const frames = rig.camera.poses.length;
    await advance(1500);
    expect(rig.camera.poses.length).toBe(frames);
  });

  it('stop() at any moment (immediately, during the flyover, mid-duel) leaves the start position', async () => {
    for (const ms of [0, 500, 3500, 9000, 24000]) {
      const { rig, ctx } = attractRig();
      const attract = createAttract(ctx);
      attract.start();
      if (ms) await advance(ms);
      const stopped = attract.stop();
      await advance(3500);
      await stopped;
      await drain();
      expect(rig.board.syncCalls[rig.board.syncCalls.length - 1]).toBe(ATTRACT_START_FEN);
      expect(rig.board.allActors().length).toBe(32);
      expect(rig.camera.state === 'seat' || rig.camera.borrows === 0).toBe(true);
      expect(gsap.globalTimeline.timeScale()).toBe(1);
      expect(rig.board.scene.children.some((o) => o.name === 'cinematic_light_rig')).toBe(false);
      expect(attract.running).toBe(false);
    }
  });

  it('stop() without start is a no-op; low graphics uses quick captures', async () => {
    const { rig, ctx } = attractRig({ graphics: { ...DEFAULT_SETTINGS.graphics, preset: 'low' } }, false);
    const attract = createAttract(ctx);
    await attract.stop();
    attract.start();
    await advance(45000);
    const stopped = attract.stop();
    await advance(3500);
    await stopped;
    await drain();
    expect(rig.board.syncCalls[rig.board.syncCalls.length - 1]).toBe(ATTRACT_START_FEN);
  });
});
