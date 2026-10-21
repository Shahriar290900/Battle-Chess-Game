// Defender -> fragments swap (choreography §1/§4). Fragments are requested at the start of the sequence so
// the lazy GLB load never stalls the impact; every await is guarded so a hung registry/fx cannot hang a capture.
import { Quaternion, Vector3 } from 'three';
import type { Object3D } from 'three';
import type { PieceActor } from '../contracts';
import { withTimeout } from './common';
import type { FinishReason, Stage } from './stage';

/** Real ms to wait for the fragment set before giving up and just removing the defender. */
const ACQUIRE_TIMEOUT_MS = 1500;
/** Real ms after which fragments are force-released if fx never calls onDone. */
const RELEASE_FAILSAFE_MS = 6000;

export interface ShatterRequest { impulseDir: Vector3; magnitude: number; cutNormal?: Vector3 }

export class ShatterJob {
  removed = false;
  shattered = false;
  private obj: Object3D | undefined;
  private acquired: Promise<Object3D | undefined> | null = null;
  private placed = false;
  private released = false;
  private abandoned = false;
  private failsafe: ReturnType<typeof setTimeout> | null = null;
  private readonly p = new Vector3();
  private readonly q = new Quaternion();

  constructor(private readonly stage: Stage, readonly defender: PieceActor, private readonly acquireTimeoutMs = ACQUIRE_TIMEOUT_MS) {}

  /** Start loading/pooling the fragment set now. */
  prefetch(): void {
    if (this.acquired) return;
    let p: Promise<Object3D>;
    try { p = Promise.resolve(this.stage.ctx.registry.acquireFragments(this.defender.id)); } catch (e) { p = Promise.reject(e); }
    this.acquired = p.then((o) => {
      this.obj = o;
      if (this.abandoned) this.release();
      return o;
    }, () => undefined);
  }

  /** Swap defender for fragments and fire the shatter effect. Tracked by the stage; never throws. */
  run(req: ShatterRequest): void {
    if (this.shattered) return;
    this.shattered = true;
    this.stage.bus('capture:shatter', { defender: this.defender.role, defenderFaction: this.defender.faction });
    this.prefetch();
    this.stage.track(this.swap(req).catch((e) => console.warn('[cinematics] shatter failed', e)));
  }

  private async swap(req: ShatterRequest): Promise<void> {
    const { ctx } = this.stage;
    const frag = await withTimeout(this.acquired as Promise<Object3D | undefined>, this.acquireTimeoutMs);
    if (this.stage.finished) return; // skip/watchdog already removed the defender and released fragments
    if (frag) {
      this.defender.root.getWorldPosition(this.p);
      this.defender.root.getWorldQuaternion(this.q);
      frag.position.copy(this.p);
      frag.quaternion.copy(this.q);
      frag.visible = true;
      ctx.board.scene.add(frag);
    }
    this.removeDefender();
    if (!frag) return;
    this.placed = true;
    this.failsafe = setTimeout(() => this.release(), RELEASE_FAILSAFE_MS);
    const done = () => this.release();
    let promise: Promise<void> | undefined;
    try {
      promise = ctx.fx.shatter({
        actor: this.defender, fragments: frag, impulseDir: req.impulseDir.clone(), magnitude: req.magnitude,
        cutNormal: req.cutNormal?.clone(), onDone: done,
      });
    } catch (e) {
      console.warn('[cinematics] fx.shatter threw', e);
      done();
      return;
    }
    // never wait on the fx promise itself (it may never settle); just release when it does
    promise?.then(done, done);
  }

  removeDefender(): void {
    if (this.removed) return;
    this.removed = true;
    try { this.stage.ctx.board.removeActor(this.defender); } catch (e) { console.warn('[cinematics] removeActor failed', e); }
  }

  private release(): void {
    if (this.released || !this.obj) return;
    this.released = true;
    if (this.failsafe) { clearTimeout(this.failsafe); this.failsafe = null; }
    try { this.obj.parent?.remove(this.obj); this.stage.ctx.registry.releaseFragments(this.defender.id, this.obj); } catch (e) { console.warn('[cinematics] releaseFragments failed', e); }
  }

  /** Guarantee: defender removed; fragments released on skip (on a natural finish fx owns them until onDone). */
  settle(reason: FinishReason): void {
    this.removeDefender();
    if (reason !== 'complete' || !this.placed) {
      this.abandoned = true;
      this.release();
    }
  }
}
