// LearnStage: takes over the real 3D board for guided play. A transparent input layer sits over the canvas (so the
// game's own board input never sees the pointer), picks pieces with the real raycast, shows legal markers, lifts and
// drags pieces, and hands every attempted move to the active lesson/tutorial step. Plays the REAL cinematic sequences.
import { gsap } from 'gsap';
import { Plane, Raycaster, Vector2, Vector3, type Mesh, type Material } from 'three';
import type { MoveResult, PromotionRole, Side, Square } from '../contracts';
import { SIDE_FACTION, squareToWorld, worldToSquare } from '../contracts';
import type { PieceActorImpl } from '../assets/pieceActor';
import type { CameraRigImpl } from '../camera/cameraRig';
import { Rules, type LegalMove } from '../core/rules';
import type { BoardImpl } from '../render/board';
import { createMarkers, type Markers } from '../render/markers';
import type { AppServices } from '../main';
import { clear, h } from './dom';

const LIFT = 0.12;
const DRAG_PX = 9;
/** A private Markers instance (its scene node is removed and its textures / materials freed on dispose). */
export function createOwnMarkers(scene: import('three').Scene): { markers: Markers; dispose(): void } {
  const before = new Set(scene.children);
  const markers = createMarkers(scene);
  const node = scene.children.find((c) => !before.has(c))!;
  return {
    markers,
    dispose() {
      scene.remove(node);
      const mats = new Set<Material>();
      let geo: { dispose(): void } | null = null;
      node.traverse((o) => {
        const m = o as Mesh;
        if (m.isMesh) { geo = m.geometry; (Array.isArray(m.material) ? m.material : [m.material]).forEach((x) => mats.add(x)); }
      });
      mats.forEach((m) => { (m as Material & { map?: { dispose(): void } | null }).map?.dispose(); m.dispose(); });
      (geo as { dispose(): void } | null)?.dispose();
    },
  };
}

export const TINT = { focus: 0xd9a441, goal: 0x4fcf7a, hint: 0x5ab4ff, wrong: 0xff4a3a } as const;

export type TryResult = 'ok' | 'illegal' | 'wrong';
export type MoveAttempt = (from: Square, to: Square, promotion?: PromotionRole) => Promise<TryResult>;

export class LearnStage {
  readonly rules = new Rules();
  readonly layer: HTMLElement;
  readonly board: BoardImpl;
  readonly rig: CameraRigImpl;
  /** The lesson/tutorial handler for a human move attempt. */
  onAttempt: MoveAttempt | null = null;
  /** Called when the learner taps the layer while a sequence plays (default: skip it). */
  inputEnabled = true;
  busy = false;
  /** Restrict which squares may be selected (defaults to the side to move). */
  selectable: ((sq: Square) => boolean) | null = null;

  private readonly markers: Markers;
  private readonly ownMarkers: ReturnType<typeof createOwnMarkers>;
  /** Fired when the learner selects one of their pieces. */
  onSelect: ((sq: Square) => void) | null = null;
  private readonly ray = new Raycaster();
  private readonly ndc = new Vector2();
  private readonly plane = new Plane(new Vector3(0, 1, 0), -LIFT);
  private readonly hit = new Vector3();
  private readonly tinted = new Set<Square>();
  private selected: PieceActorImpl | null = null;
  private legal: LegalMove[] = [];
  private down: { id: number; x: number; y: number; actor: PieceActorImpl | null; toggleOff: boolean; drag: boolean } | null = null;
  private readonly tick = (time: number) => this.markers.update(time);
  private pickerEl: HTMLElement | null = null;
  private pickerResolve: ((r: PromotionRole | null) => void) | null = null;
  private disposed = false;

  constructor(private readonly s: AppServices, parent: HTMLElement) {
    this.board = s.board as BoardImpl;
    this.rig = s.camera as CameraRigImpl;
    this.ownMarkers = createOwnMarkers(s.scene);
    this.markers = this.ownMarkers.markers;
    gsap.ticker.add(this.tick);
    this.layer = h('div', { class: 'learn-layer', 'aria-hidden': 'true' });
    parent.append(this.layer);
    this.layer.addEventListener('pointerdown', this.onDown);
    this.layer.addEventListener('pointermove', this.onMove);
    this.layer.addEventListener('pointerup', this.onUp);
    this.layer.addEventListener('pointercancel', this.onCancel);
  }

  // ------------------------------------------------------------ position
  /** Replace the position on the real board (and the private rules) without animation. */
  setPosition(fen: string, seat?: Side, instantSeat = false): void {
    this.s.sequences.skip();
    this.deselect(false);
    this.clearTints();
    this.rules.reset(fen);
    this.board.syncToFen(fen);
    this.s.fx.setStaticActors?.(this.board.allActors());
    if (seat) void this.rig.toSeat(seat, { instant: instantSeat });
  }

  tint(squares: readonly Square[], color: number): void {
    for (const sq of squares) { this.board.tintSquare(sq, color); this.tinted.add(sq); }
  }

  clearTints(): void {
    for (const sq of this.tinted) this.board.tintSquare(sq, null);
    this.tinted.clear();
  }

  /** Briefly flash squares (wrong move feedback) then restore previous tints via the caller. */
  flash(squares: readonly Square[], color: number, ms = 450): void {
    const prev = new Set(this.tinted);
    for (const sq of squares) this.board.tintSquare(sq, color);
    window.setTimeout(() => { if (this.disposed) return; for (const sq of squares) if (!prev.has(sq)) this.board.tintSquare(sq, null); }, ms);
  }

  /** Show the pulsing hint frame on a piece and a glow on the target. */
  showHintMove(from: Square, to: Square): void {
    this.markers.setSelected(from);
    this.markers.show([{ square: to, capture: !!this.rules.pieceAt(to) }]);
  }
  clearHintMove(): void { if (!this.selected) { this.markers.clear(); this.markers.setSelected(null); } }

  // ------------------------------------------------------------ sequences
  /** Play a move the rules have accepted, then its check / mate / stalemate follow-up, exactly like a real game. */
  async play(res: MoveResult, override: Partial<import('../contracts').Settings> = {}): Promise<void> {
    const { board, camera, fx, registry, bus, sequences, kinematics } = this.s;
    const ctx = { move: res, board, camera, fx, registry, bus, settings: { ...this.s.settings.get(), ...override }, kinematics };
    this.busy = true;
    this.deselect(false);
    try {
      if (res.captured) await sequences.capture(ctx);
      else if (res.isCastle) await sequences.castle(ctx);
      else await sequences.move(ctx);
      if (res.promotion) await sequences.promote(ctx, res.promotion);
      board.syncToFen(res.fenAfter);
      fx.setStaticActors?.(board.allActors());
      const turn = res.side === 'w' ? 'b' : 'w';
      const king = new Rules(res.fenAfter).kingSquare(turn);
      if (res.check && king) {
        bus.emit('check', { side: turn, kingSquare: king });
        board.tintSquare(king, 0xff3a2a); this.tinted.add(king);
        if (res.mate) await sequences.checkmate(ctx, king); else await sequences.check(ctx, king);
      } else if (res.stalemate || res.draw) await sequences.stalemate(ctx);
    } catch (e) {
      console.error('[learn] sequence failed', e);
      board.syncToFen(res.fenAfter);
    } finally {
      this.busy = false;
    }
  }

  // ------------------------------------------------------------ promotion picker
  pickPromotion(side: Side): Promise<PromotionRole | null> {
    this.closePicker();
    const roles: PromotionRole[] = ['queen', 'rook', 'bishop', 'knight'];
    const el = h('div', { class: 'learn-picker', role: 'dialog', 'aria-label': 'Choose a promotion' },
      h('p', { class: 'learn-picker-title', text: `Promote to… (${SIDE_FACTION[side] === 'emberhold' ? 'Emberhold' : 'Rime Host'})` }),
      h('div', { class: 'learn-picker-row' }, ...roles.map((r) => h('button', { class: 'learn-btn', type: 'button', 'data-tip': `${r[0].toUpperCase() + r.slice(1)}|Promote the pawn to a ${r}.`, onClick: () => this.resolvePicker(r) }, r[0].toUpperCase() + r.slice(1)))));
    this.pickerEl = el;
    this.layer.parentElement?.append(el);
    return new Promise((res) => { this.pickerResolve = res; });
  }
  private resolvePicker(r: PromotionRole | null) { const f = this.pickerResolve; this.closePicker(); f?.(r); }
  private closePicker() { this.pickerEl?.remove(); this.pickerEl = null; this.pickerResolve = null; }

  // ------------------------------------------------------------ input
  private canSelect(sq: Square): boolean {
    if (this.selectable) return this.selectable(sq);
    const p = this.rules.pieceAt(sq);
    return !!p && p.side === this.rules.turn();
  }

  private aim(e: PointerEvent): void {
    this.ndc.set((e.clientX / window.innerWidth) * 2 - 1, -(e.clientY / window.innerHeight) * 2 + 1);
    this.ray.setFromCamera(this.ndc, this.rig.camera);
  }

  private squareAt(e: PointerEvent): { sq: Square | null; actor: PieceActorImpl | null } {
    this.aim(e);
    const actor = this.board.pickActor(this.ray);
    if (actor) return { sq: actor.square, actor };
    return { sq: this.board.pickSquare(this.ray), actor: null };
  }

  private lower(actor: PieceActorImpl, animate: boolean): void {
    gsap.killTweensOf(actor.root.position);
    const p = squareToWorld(actor.square);
    if (animate) gsap.to(actor.root.position, { x: p.x, z: p.z, y: 0, duration: 0.15, ease: 'power2.out' });
    else actor.root.position.set(p.x, 0, p.z);
  }

  deselect(animate = true): void {
    if (this.selected) { this.selected.setHighlight(false); this.lower(this.selected, animate); }
    this.selected = null;
    this.legal = [];
    this.markers.clear();
    this.markers.setSelected(null);
  }

  private select(actor: PieceActorImpl): void {
    if (this.selected && this.selected !== actor) this.deselect();
    this.selected = actor;
    this.legal = this.rules.legalMovesFrom(actor.square);
    actor.setHighlight(true);
    gsap.killTweensOf(actor.root.position);
    gsap.to(actor.root.position, { y: LIFT, duration: 0.15, ease: 'power2.out' });
    this.markers.show(this.legal.map((m) => ({ square: m.to, capture: !!m.captured })));
    this.markers.setSelected(actor.square);
    this.s.bus.emit('ui:select', { square: actor.square });
    this.onSelect?.(actor.square);
  }

  private wobble(actor: PieceActorImpl): void {
    gsap.fromTo(actor.model.rotation, { z: -0.12 }, { z: 0, duration: 0.45, ease: 'elastic.out(1,0.35)', overwrite: 'auto' });
  }

  private async commit(to: Square): Promise<void> {
    const actor = this.selected;
    if (!actor || !this.onAttempt) return;
    const from = actor.square;
    const lm = this.legal.find((m) => m.to === to);
    this.markers.clear();
    this.markers.setSelected(null);
    actor.setHighlight(false);
    this.lower(actor, false);
    this.selected = null;
    this.legal = [];
    let promo: PromotionRole | undefined;
    if (lm?.isPromotion) {
      this.busy = true;
      const r = await this.pickPromotion(this.rules.turn());
      this.busy = false;
      if (!r) return;
      promo = r;
    }
    this.busy = true;
    let r: TryResult = 'illegal';
    try { r = await this.onAttempt(from, to, promo); } finally { this.busy = false; }
    if (r !== 'ok' && !this.disposed) { this.wobble(actor); }
  }

  private readonly onDown = (e: PointerEvent): void => {
    if (e.button !== undefined && e.button > 0) return;
    if (this.pickerEl) return;
    if (this.busy) {
      if (this.s.sequences.running) this.s.sequences.skip();
      e.preventDefault();
      return;
    }
    if (!this.inputEnabled) return;
    const { sq, actor } = this.squareAt(e);
    if (!sq) { this.deselect(); return; }
    if (this.selected && sq !== this.selected.square && !(actor && this.canSelect(sq))) {
      void this.commit(sq);
      e.preventDefault();
      return;
    }
    if (this.selected && actor && this.canSelect(sq) && !this.legal.some((m) => m.to === sq) && actor !== this.selected) {
      this.select(actor);
      this.startPress(e, actor, false);
      e.preventDefault();
      return;
    }
    if (this.selected && this.legal.some((m) => m.to === sq)) { void this.commit(sq); e.preventDefault(); return; }
    if (actor && this.canSelect(sq)) {
      const toggleOff = this.selected === actor;
      if (!toggleOff) this.select(actor);
      this.startPress(e, actor, toggleOff);
      e.preventDefault();
      return;
    }
    this.deselect();
  };

  private startPress(e: PointerEvent, actor: PieceActorImpl, toggleOff: boolean): void {
    this.down = { id: e.pointerId, x: e.clientX, y: e.clientY, actor, toggleOff, drag: false };
    try { this.layer.setPointerCapture(e.pointerId); } catch { /* synthetic events */ }
  }

  private readonly onMove = (e: PointerEvent): void => {
    const d = this.down;
    if (!d || e.pointerId !== d.id || !d.actor) return;
    if (!d.drag && Math.hypot(e.clientX - d.x, e.clientY - d.y) > DRAG_PX) { d.drag = true; if (this.selected !== d.actor) this.select(d.actor); }
    if (d.drag) {
      this.aim(e);
      if (this.ray.ray.intersectPlane(this.plane, this.hit)) {
        gsap.killTweensOf(d.actor.root.position);
        d.actor.root.position.set(Math.min(Math.max(this.hit.x, -4.2), 4.2), LIFT + 0.05, Math.min(Math.max(this.hit.z, -4.2), 4.2));
      }
      e.preventDefault();
    }
  };

  private readonly onUp = (e: PointerEvent): void => {
    const d = this.down;
    if (!d || e.pointerId !== d.id) return;
    this.down = null;
    try { this.layer.releasePointerCapture(e.pointerId); } catch { /* ignore */ }
    if (d.drag && d.actor) {
      this.aim(e);
      let target: Square | null = null;
      if (this.ray.ray.intersectPlane(this.plane, this.hit)) target = worldToSquare(this.hit);
      if (target && target !== d.actor.square) { void this.commit(target); return; }
      gsap.to(d.actor.root.position, { x: squareToWorld(d.actor.square).x, z: squareToWorld(d.actor.square).z, y: LIFT, duration: 0.18, ease: 'power2.out' });
    } else if (d.toggleOff) this.deselect();
  };

  private readonly onCancel = (): void => {
    if (this.down?.actor && this.selected) this.deselect();
    this.down = null;
  };

  // ------------------------------------------------------------ teardown
  dispose(): void {
    if (this.disposed) return;
    this.disposed = true;
    gsap.ticker.remove(this.tick);
    this.closePicker();
    this.deselect(false);
    this.clearTints();
    this.layer.removeEventListener('pointerdown', this.onDown);
    this.layer.removeEventListener('pointermove', this.onMove);
    this.layer.removeEventListener('pointerup', this.onUp);
    this.layer.removeEventListener('pointercancel', this.onCancel);
    this.layer.remove();
    this.ownMarkers.dispose();
    clear(this.layer);
  }
}
