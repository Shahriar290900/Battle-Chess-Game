import { Euler, Object3D, Quaternion, Vector3 } from 'three';
import type { PieceActor, Role } from '../../src/contracts';

export interface MockActor extends PieceActor { bones: Record<string, Object3D>; mode: 'free' | 'scrub' }

const HUMANOID = ['spine', 'head', 'arm_L', 'arm_R'];

/** Minimal PieceActor: root > model > body hierarchy mirroring the GLB rig (only the fields kinematics reads). */
export function mockActor(role: Role, opts: { bones?: string[]; x?: number; z?: number; yaw?: number } = {}): MockActor {
  const root = new Object3D();
  root.position.set(opts.x ?? 0, 0, opts.z ?? 0);
  root.rotation.y = opts.yaw ?? 0;
  const model = new Object3D();
  root.add(model);
  const bones: Record<string, Object3D> = {};
  const mk = (name: string, parent: Object3D, y: number) => {
    const b = new Object3D(); b.name = name; b.position.set(0, y, 0); parent.add(b); bones[name] = b; return b;
  };
  const want = opts.bones ?? (role === 'rook' ? ['body', 'top'] : role === 'knight' ? ['mount_body', 'mount_head', 'body', ...HUMANOID, 'top'] : ['body', ...HUMANOID, 'top']);
  const has = (n: string) => want.includes(n);
  const mount = has('mount_body') ? mk('mount_body', model, 0.5) : null;
  const body = has('body') ? mk('body', mount ?? model, role === 'rook' ? 0.22 : 0.6) : null;
  if (mount && has('mount_head')) mk('mount_head', mount, 0.5);
  const parent = body ?? mount ?? model;
  const spine = has('spine') ? mk('spine', parent, 0.1) : null;
  if (has('head')) mk('head', spine ?? parent, 0.3);
  if (has('top')) mk('top', spine ?? parent, role === 'rook' ? 0.8 : 0.3);
  root.updateWorldMatrix(true, true);
  return {
    id: `emberhold_${role}`, faction: 'emberhold', role, side: 'w', root, model, bones, mode: 'free',
  } as unknown as MockActor;
}

const _e = new Euler();
/** Rotation of a bone as YXZ euler (rx, ry, rz). */
export function eul(o: Object3D): { x: number; y: number; z: number } {
  _e.setFromQuaternion(o.quaternion, 'YXZ');
  return { x: _e.x, y: _e.y, z: _e.z };
}
export const maxAngle = (o: Object3D) => { const e = eul(o); return Math.max(Math.abs(e.x), Math.abs(e.y), Math.abs(e.z)); };
export const quatEq = (a: Quaternion, b: Quaternion) => a.x === b.x && a.y === b.y && a.z === b.z && a.w === b.w;
export const V = (x: number, y: number, z: number) => new Vector3(x, y, z);
