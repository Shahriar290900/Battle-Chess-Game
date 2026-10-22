// STUB (lead) — replaced by the kinematics agent. Procedural animation layer is a no-op.
import type { KinematicsApi } from '../contracts';

export function createKinematics(): KinematicsApi {
  return { attach() {}, detach() {}, lookAt() {}, impulse() {}, setEnabled() {}, update() {} };
}
