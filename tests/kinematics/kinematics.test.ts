import { describe, expect, it } from 'vitest';
import { Quaternion } from 'three';
import { createKinematics, impulseFalloff, solveLook } from '../../src/kinematics';
import { newLookAngles } from '../../src/kinematics/look';
import { DEG, HEAD_PITCH_MAX, HEAD_YAW_MAX } from '../../src/kinematics/tables';
import { Spring } from '../../src/kinematics/spring';
import { eul, maxAngle, mockActor, quatEq, V } from './helpers';

/** Accelerate to 3 u/s over 0.8 s, cruise 0.6 s, stop abruptly, then rest. Returns peak |angle| over all bones. */
function runMotion(role: Parameters<typeof mockActor>[0], dtFn: (i: number) => number, restSeconds = 4) {
  const a = mockActor(role);
  const k = createKinematics();
  k.attach(a);
  let peak = 0, peakTop = 0, t = 0, i = 0;
  const step = () => {
    const dt = dtFn(i++);
    t += dt;
    // piecewise velocity profile integrated analytically-ish
    const v = t < 0.8 ? 3 * (t / 0.8) : t < 1.4 ? 3 : 0;
    a.root.position.x += v * dt;
    k.update(dt);
    for (const b of Object.values(a.bones)) {
      const m = maxAngle(b);
      expect(Number.isFinite(m)).toBe(true);
      peak = Math.max(peak, m);
    }
    if (a.bones.top) peakTop = Math.max(peakTop, Math.abs(eul(a.bones.top).x), Math.abs(eul(a.bones.top).z));
  };
  while (t < 1.4 + 0.3) step();
  const moving = peak;
  const end = t + restSeconds;
  while (t < end) step();
  let residual = 0;
  for (const b of Object.values(a.bones)) residual = Math.max(residual, maxAngle(b));
  return { moving, peak, peakTop, residual, a };
}

describe('spring integrator', () => {
  for (const dt of [1 / 30, 1 / 60, 1 / 120, 1 / 144, 0.25]) {
    it(`stays bounded and decays at dt=${dt.toFixed(4)}`, () => {
      const s = new Spring(6, 0.1, 1);
      s.x = 0.5;
      const sim = Math.min(dt, 0.1);
      const n = Math.max(1, Math.ceil(sim / (1 / 120)));
      for (let f = 0; f < 600; f++) for (let j = 0; j < n; j++) s.step(sim / n);
      expect(Number.isFinite(s.x)).toBe(true);
      expect(Math.abs(s.x)).toBeLessThan(0.01);
    });
  }
});

describe('stability across frame rates', () => {
  const rates = [1 / 30, 1 / 60, 1 / 90, 1 / 144];
  for (const role of ['pawn', 'bishop', 'knight', 'queen', 'king', 'rook'] as const) {
    it(`${role}: bounded while moving, settles at rest, for every dt and a 0.25 s spike`, () => {
      const peaks: number[] = [];
      for (const dt of rates) {
        const r = runMotion(role, () => dt);
        expect(r.peak).toBeLessThan(0.7);
        expect(r.residual).toBeLessThan(0.08); // idle life only
        peaks.push(r.peakTop);
      }
      const spiky = runMotion(role, (i) => (i === 40 ? 0.25 : 1 / 60));
      expect(spiky.peak).toBeLessThan(0.7);
      expect(spiky.residual).toBeLessThan(0.08);
      // frame-rate independence: swing amplitude agrees within 2.5x
      const lo = Math.min(...peaks), hi = Math.max(...peaks);
      if (hi > 0.01) expect(hi / Math.max(lo, 1e-6)).toBeLessThan(2.5);
    });
  }

  it('top lags behind the acceleration (hanging cape) then overshoots forward', () => {
    const a = mockActor('queen');
    const k = createKinematics(); k.attach(a);
    // root yaw 0 => forward is +Z, +X is local "left". Accelerating toward +X: a hanging cape trails toward -X (negative rz).
    let minRz = 0, maxRz = 0;
    for (let i = 0, t = 0; t < 0.8; i++, t += 1 / 60) {
      a.root.position.x += 3 * Math.min(t / 0.3, 1) / 60; k.update(1 / 60);
      const z = eul(a.bones.top).z; minRz = Math.min(minRz, z); maxRz = Math.max(maxRz, z);
    }
    expect(minRz).toBeLessThan(-0.03);
    expect(maxRz).toBeGreaterThan(0); // swing-back overshoot
  });
});

describe('inertial lean and landing', () => {
  it('leans forward when accelerating forward and the lean overshoots/settles after stopping', () => {
    const a = mockActor('pawn');
    const k = createKinematics(); k.attach(a);
    let t = 0; let maxFwd = 0; let minAfterStop = 0;
    for (; t < 0.6; t += 1 / 60) { a.root.position.z += 3 * Math.min(t / 0.4, 1) / 60; k.update(1 / 60); maxFwd = Math.max(maxFwd, eul(a.bones.body).x); }
    for (let i = 0; i < 120; i++) { k.update(1 / 60); minAfterStop = Math.min(minAfterStop, eul(a.bones.body).x); }
    expect(maxFwd).toBeGreaterThan(0.01);
    expect(minAfterStop).toBeLessThan(-0.002); // recoil when stopping
    for (let i = 0; i < 400; i++) k.update(1 / 60);
    expect(maxAngle(a.bones.body)).toBeLessThan(0.03);
  });

  it('squashes body scale.y on a landing and recovers', () => {
    const a = mockActor('knight');
    const k = createKinematics(); k.attach(a);
    a.root.position.y = 1;
    k.update(1 / 60);
    let minSy = 1;
    for (let i = 0; i < 12; i++) { a.root.position.y -= 5 / 60; if (a.root.position.y < 0) a.root.position.y = 0; k.update(1 / 60); }
    for (let i = 0; i < 40; i++) { k.update(1 / 60); minSy = Math.min(minSy, a.bones.mount_body.scale.y); }
    expect(minSy).toBeLessThan(0.99);
    for (let i = 0; i < 300; i++) k.update(1 / 60);
    expect(Math.abs(a.bones.mount_body.scale.y - 1)).toBeLessThan(0.002);
  });
});

describe('look-at IK', () => {
  it('solver clamps head yaw to 70deg and pitch to 30deg, remainder goes to the spine', () => {
    const o = newLookAngles();
    solveLook('humanoid', true, 170 * DEG, -80 * DEG, o);
    expect(Math.abs(o.headYaw)).toBeLessThanOrEqual(HEAD_YAW_MAX + 1e-9);
    expect(Math.abs(o.headPitch)).toBeLessThanOrEqual(HEAD_PITCH_MAX + 1e-9);
    expect(o.spineYaw).toBeGreaterThan(0.2);
    solveLook('humanoid', true, 40 * DEG, 0, o);
    expect(o.headYaw + o.spineYaw).toBeCloseTo(40 * DEG, 6);
    solveLook('humanoid', false, -100 * DEG, 0, o);
    expect(o.headYaw).toBeCloseTo(-HEAD_YAW_MAX, 6);
    expect(o.spineYaw).toBe(0);
  });

  it('turns the head toward a world point and blends in about a quarter second', () => {
    const a = mockActor('queen', { yaw: Math.PI }); // faces -Z
    const k = createKinematics(); k.attach(a);
    k.lookAt(a, V(-2, 1, -2), 1); // target at -X,-Z: for a piece facing -Z, -X is its left? (yaw pi flips x)
    let y25 = 0;
    for (let i = 0; i < 15; i++) { k.update(1 / 60); if (i === 14) y25 = eul(a.bones.head).y; }
    for (let i = 0; i < 120; i++) k.update(1 / 60);
    const fin = eul(a.bones.head).y + eul(a.bones.spine).y;
    expect(Math.abs(fin)).toBeGreaterThan(30 * DEG);
    expect(Math.abs(y25)).toBeGreaterThan(0.6 * Math.abs(eul(a.bones.head).y));
    // release returns to (near) rest
    k.lookAt(a, null);
    for (let i = 0; i < 180; i++) k.update(1 / 60);
    expect(Math.abs(eul(a.bones.head).y)).toBeLessThan(0.08);
  });

  it('never exceeds the clamps even for targets behind and overhead', () => {
    const a = mockActor('king');
    const k = createKinematics(); k.attach(a);
    k.lookAt(a, V(0.2, 40, -5), 1);
    for (let i = 0; i < 240; i++) k.update(1 / 60);
    const e = eul(a.bones.head);
    expect(Math.abs(e.y)).toBeLessThanOrEqual(HEAD_YAW_MAX + 0.1); // + idle wander
    expect(Math.abs(e.x)).toBeLessThanOrEqual(HEAD_PITCH_MAX + 0.1);
  });

  it('uses mount_head for knights and top/body for rooks, and ignores unattached actors', () => {
    const kn = mockActor('knight'); const rk = mockActor('rook'); const stray = mockActor('pawn');
    const k = createKinematics(); k.attach(kn); k.attach(rk);
    k.lookAt(kn, V(3, 1, 3)); k.lookAt(rk, V(3, 1, 3)); k.lookAt(stray, V(3, 1, 3));
    for (let i = 0; i < 200; i++) k.update(1 / 60);
    expect(Math.abs(eul(kn.bones.mount_head).y)).toBeGreaterThan(0.2);
    expect(Math.abs(eul(rk.bones.top).y) + Math.abs(eul(rk.bones.body).y)).toBeGreaterThan(0.2);
    expect(maxAngle(stray.bones.head)).toBe(0);
  });
});

describe('impulse (knockback)', () => {
  it('falloff is 1 at the origin, monotone, and 0 at the radius', () => {
    expect(impulseFalloff(0, 3)).toBe(1);
    expect(impulseFalloff(3, 3)).toBe(0);
    expect(impulseFalloff(4, 3)).toBe(0);
    let prev = 2;
    for (let d = 0; d <= 3; d += 0.25) { const f = impulseFalloff(d, 3); expect(f).toBeLessThanOrEqual(prev); prev = f; }
  });

  it('nearer and lighter actors wobble more; actors outside the radius do not move', () => {
    const near = mockActor('bishop', { x: 1, z: 0 }), far = mockActor('bishop', { x: 2.5, z: 0 });
    const out = mockActor('bishop', { x: 5, z: 0 }), heavy = mockActor('rook', { x: 1, z: 0 }), pawn = mockActor('pawn', { x: 1, z: 0 });
    const k = createKinematics();
    for (const a of [near, far, out, heavy, pawn]) k.attach(a);
    k.impulse(V(0, 0, 0), 1.2, 3);
    const peak: Record<string, number> = { near: 0, far: 0, out: 0, heavy: 0, pawn: 0 };
    const set = { near, far, out, heavy, pawn };
    for (let i = 0; i < 90; i++) {
      k.update(1 / 60);
      for (const [n, a] of Object.entries(set)) peak[n] = Math.max(peak[n], Math.abs(eul(a.bones.body).z));
    }
    expect(peak.near).toBeGreaterThan(peak.far);
    expect(peak.far).toBeGreaterThan(0);
    expect(peak.out).toBeLessThan(0.005); // only idle sway
    expect(peak.pawn).toBeGreaterThan(peak.heavy * 2);
    // leans away: impulse from -X pushes a +X actor toward +X: tipping +Y toward +X is negative rz
    const a2 = mockActor('pawn', { x: 1 }); const k2 = createKinematics(); k2.attach(a2);
    k2.impulse(V(0, 0, 0), 1, 3);
    let mn = 0; for (let i = 0; i < 30; i++) { k2.update(1 / 60); mn = Math.min(mn, eul(a2.bones.body).z); }
    expect(mn).toBeLessThan(-0.02);
  });

  it('strong impulses hop light pieces (and land), never heavy ones; settles within ~1.2 s', () => {
    const p = mockActor('pawn', { x: 0.5 }), r = mockActor('rook', { x: 0.5 });
    const k = createKinematics(); k.attach(p); k.attach(r);
    k.impulse(V(0, 0, 0), 3, 3);
    let hopP = 0, hopR = 0;
    for (let i = 0; i < 40; i++) { k.update(1 / 60); hopP = Math.max(hopP, p.bones.body.position.y - 0.6); hopR = Math.max(hopR, r.bones.body.position.y - 0.22); }
    expect(hopP).toBeGreaterThan(0.01);
    expect(hopP).toBeLessThan(0.15);
    expect(hopR).toBeLessThan(0.002);
    for (let i = 0; i < 70; i++) k.update(1 / 60); // total ~1.8 s
    expect(maxAngle(p.bones.body)).toBeLessThan(0.05);
    expect(Math.abs(p.bones.body.position.y - 0.6)).toBeLessThan(0.01);
  });
});

describe('enable / disable / detach / clip interplay', () => {
  it('disable restores the clip pose exactly and update becomes a no-op', () => {
    const a = mockActor('queen');
    const rest = new Map<string, Quaternion>();
    for (const [n, b] of Object.entries(a.bones)) { b.quaternion.setFromAxisAngle(V(1, 0, 0).normalize(), 0.05 + rest.size * 0.01); rest.set(n, b.quaternion.clone()); }
    const scale0 = a.bones.body.scale.clone(), pos0 = a.bones.body.position.clone();
    const k = createKinematics(); k.attach(a);
    k.lookAt(a, V(2, 1, 2));
    for (let i = 0; i < 60; i++) { a.root.position.x += 0.05; k.update(1 / 60); }
    k.impulse(V(0, 0, 0), 2, 4);
    for (let i = 0; i < 10; i++) k.update(1 / 60);
    expect(quatEq(a.bones.head.quaternion, rest.get('head')!)).toBe(false);
    k.setEnabled(false);
    for (const [n, b] of Object.entries(a.bones)) expect(quatEq(b.quaternion, rest.get(n)!)).toBe(true);
    expect(a.bones.body.scale.equals(scale0)).toBe(true);
    expect(a.bones.body.position.equals(pos0)).toBe(true);
    a.root.position.x += 5; k.update(1 / 60);
    for (const [n, b] of Object.entries(a.bones)) expect(quatEq(b.quaternion, rest.get(n)!)).toBe(true);
    k.setEnabled(true);
    for (let i = 0; i < 5; i++) k.update(1 / 60);
    expect(quatEq(a.bones.top.quaternion, rest.get('top')!)).toBe(false);
  });

  it('detach restores the pose', () => {
    const a = mockActor('pawn');
    const k = createKinematics(); k.attach(a);
    for (let i = 0; i < 90; i++) k.update(1 / 60);
    k.detach(a);
    for (const b of Object.values(a.bones)) expect(b.quaternion.equals(new Quaternion())).toBe(true);
  });

  it('layers on top of a mixer that rewrites channels and does not accumulate on static ones', () => {
    const a = mockActor('pawn');
    const k = createKinematics(); k.attach(a);
    const clip = new Quaternion().setFromAxisAngle(V(0, 1, 0), 0.3);
    for (let i = 0; i < 600; i++) { if (i % 2 === 0) a.bones.head.quaternion.copy(clip); /* static every other frame */ k.update(1 / 60); }
    // offsets stay small around the clip pose (no drift)
    const err = a.bones.head.quaternion.angleTo(clip);
    expect(err).toBeLessThan(0.1);
  });

  it('fades the additive layer out while a scripted (scrubbed) clip owns the pose', () => {
    const a = mockActor('king');
    const k = createKinematics(); k.attach(a);
    k.impulse(V(0, 0, 0), 3, 4); a.root.position.set(0.3, 0, 0);
    for (let i = 0; i < 6; i++) k.update(1 / 60);
    a.mode = 'scrub';
    k.impulse(V(0, 0, 0), 3, 4);
    for (let i = 0; i < 40; i++) k.update(1 / 60);
    expect(maxAngle(a.bones.body)).toBeLessThan(0.003);
    expect(maxAngle(a.bones.top)).toBeLessThan(0.003);
  });

  it('never writes root or model transforms; tolerates actors without bones', () => {
    const a = mockActor('pawn'); const bare = mockActor('bishop', { bones: [] });
    const k = createKinematics(); k.attach(a); k.attach(bare);
    const p = a.root.position.clone(), r = a.root.rotation.y;
    k.lookAt(bare, V(1, 1, 1)); k.impulse(V(0, 0, 0), 2, 4);
    for (let i = 0; i < 120; i++) k.update(1 / 60);
    expect(a.root.position.equals(p)).toBe(true);
    expect(a.root.rotation.y).toBe(r);
    expect(a.model.position.lengthSq() + a.model.rotation.x ** 2 + a.model.rotation.y ** 2 + a.model.rotation.z ** 2).toBe(0);
  });

  it('skips hidden (faded) actors and survives teleports', () => {
    const a = mockActor('pawn');
    const k = createKinematics(); k.attach(a);
    a.model.visible = false;
    k.impulse(V(0, 0, 0), 3, 4);
    for (let i = 0; i < 30; i++) k.update(1 / 60);
    expect(maxAngle(a.bones.body)).toBe(0);
    a.model.visible = true;
    for (let i = 0; i < 10; i++) k.update(1 / 60);
    a.root.position.x += 40; // undo / sync-to-fen warp
    k.update(1 / 60);
    for (let i = 0; i < 300; i++) k.update(1 / 60);
    expect(maxAngle(a.bones.body)).toBeLessThan(0.05);
  });
});

describe('performance', () => {
  it('32 actors update well under 0.3 ms/frame on average (node, jit-warmed)', () => {
    const k = createKinematics();
    const actors = [] as ReturnType<typeof mockActor>[];
    const roles = ['pawn', 'rook', 'knight', 'bishop', 'queen', 'king'] as const;
    for (let i = 0; i < 32; i++) { const a = mockActor(roles[i % 6], { x: i % 8, z: Math.floor(i / 8) }); k.attach(a); actors.push(a); }
    k.lookAt(actors[3], V(2, 1, 2));
    const frame = (i: number) => { actors[i % 32].root.position.x += Math.sin(i * 0.1) * 0.02; k.update(1 / 60); };
    for (let i = 0; i < 600; i++) frame(i);
    const N = 1500;
    let ms = Infinity;
    for (let rep = 0; rep < 3; rep++) { // best of 3: the suite runs in parallel with other workers
      const t0 = performance.now();
      for (let i = 0; i < N; i++) frame(i);
      ms = Math.min(ms, (performance.now() - t0) / N);
    }
    console.log(`kinematics: ${ms.toFixed(4)} ms/frame for 32 actors`);
    expect(ms).toBeLessThan(0.3);
  });
});
