// Board input (architecture §8): pointer events for mouse and touch; click-click and drag-drop.
// Selecting lifts the piece 0.12 and shows legal markers. Input is ignored while a modal is open;
// a tap during a sequence skips it; the controller itself refuses moves on the AI's turn.
import { gsap } from 'gsap';
import { Plane, Raycaster, Vector2, Vector3 } from 'three';
import type { EventBus, SettingsStore, Square } from '../contracts';
import { squareToWorld, worldToSquare } from '../contracts';
import type { CameraRigImpl } from '../camera/cameraRig';
import type { GameController } from '../core/game';
import type { LegalMove } from '../core/rules';
import type { PieceActorImpl } from '../assets/pieceActor';
import type { BoardImpl } from '../render/board';
import type { Markers } from '../render/markers';

export interface BoardInput {
  dispose(): void;
}

const LIFT = 0.12;
const DRAG_PX = 9;

export function createBoardInput(d: {
  canvas: HTMLElement;
  rig: CameraRigImpl;
  board: BoardImpl;
  controller: GameController;
  markers: Markers;
  settings: SettingsStore;
  bus: EventBus;
  isBlocked: () => boolean;
}): BoardInput {
  const { canvas, rig, board, controller, markers } = d;
  const ray = new Raycaster();
  const ndc = new Vector2();
  const plane = new Plane(new Vector3(0, 1, 0), -LIFT);
  const hit = new Vector3();

  let selected: PieceActorImpl | null = null;
  let legal: LegalMove[] = [];
  let down: { id: number; x: number; y: number; actor: PieceActorImpl | null; toggleOff: boolean; drag: boolean } | null = null;
  let lastPly = -1;

  function aim(e: PointerEvent): void {
    const r = canvas.getBoundingClientRect();
    ndc.set(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1);
    ray.setFromCamera(ndc, rig.camera);
  }

  function squareAt(e: PointerEvent, ignore?: PieceActorImpl): { sq: Square | null; actor: PieceActorImpl | null } {
    aim(e);
    const actor = board.pickActor(ray, ignore);
    if (actor) return { sq: actor.square, actor };
    return { sq: board.pickSquare(ray), actor: null };
  }

  function lower(actor: PieceActorImpl, animate: boolean): void {
    gsap.killTweensOf(actor.root.position);
    const p = squareToWorld(actor.square);
    if (animate) gsap.to(actor.root.position, { x: p.x, z: p.z, y: 0, duration: 0.15, ease: 'power2.out' });
    else actor.root.position.set(p.x, 0, p.z);
  }

  function deselect(animate = true): void {
    if (selected) { selected.setHighlight(false); lower(selected, animate); }
    selected = null;
    legal = [];
    markers.clear();
    markers.setSelected(null);
  }

  function select(actor: PieceActorImpl): void {
    if (selected && selected !== actor) deselect();
    selected = actor;
    legal = controller.legalMovesFrom(actor.square);
    actor.setHighlight(true);
    gsap.killTweensOf(actor.root.position);
    gsap.to(actor.root.position, { y: LIFT, duration: 0.15, ease: 'power2.out' });
    markers.show(legal.map((m) => ({ square: m.to, capture: !!m.captured })));
    markers.setSelected(actor.square);
    d.bus.emit('ui:select', { square: actor.square });
  }

  async function commit(to: Square): Promise<void> {
    const actor = selected;
    if (!actor) return;
    const from = actor.square;
    actor.setHighlight(false);
    lower(actor, false);
    markers.clear();
    markers.setSelected(null);
    selected = null;
    legal = [];
    const ok = await controller.attemptMove(from, to);
    if (!ok && controller.canSelect(from)) {
      const a = board.actorAt(from);
      if (a) select(a);
    }
  }

  function onDown(e: PointerEvent): void {
    if (e.button !== undefined && e.button > 0) return;
    if (d.isBlocked()) return;
    if (controller.state === 'resolving' || controller.state === 'sequence' || controller.state === 'postMove') {
      controller.skip();
      e.preventDefault();
      return;
    }
    if (controller.state !== 'awaitInput') return;
    const { sq, actor } = squareAt(e);
    if (!sq) { deselect(); return; }
    if (selected && legal.some((m) => m.to === sq)) {
      rig.setInputLocked(true);
      void commit(sq).finally(() => rig.setInputLocked(false));
      e.preventDefault();
      return;
    }
    if (actor && controller.canSelect(sq)) {
      const toggleOff = selected === actor;
      if (!toggleOff) select(actor);
      rig.setInputLocked(true);
      down = { id: e.pointerId, x: e.clientX, y: e.clientY, actor, toggleOff, drag: false };
      try { canvas.setPointerCapture(e.pointerId); } catch { /* synthetic events */ }
      e.preventDefault();
      return;
    }
    deselect();
  }

  function onMove(e: PointerEvent): void {
    if (!down || e.pointerId !== down.id || !down.actor) {
      if (!down && e.pointerType === 'mouse' && !d.isBlocked()) {
        const { sq } = squareAt(e);
        canvas.style.cursor = sq && controller.canSelect(sq) ? 'pointer' : '';
      }
      return;
    }
    if (!down.drag && Math.hypot(e.clientX - down.x, e.clientY - down.y) > DRAG_PX) {
      down.drag = true;
      if (selected !== down.actor) select(down.actor);
    }
    if (down.drag) {
      aim(e);
      if (ray.ray.intersectPlane(plane, hit)) {
        gsap.killTweensOf(down.actor.root.position);
        down.actor.root.position.set(Math.min(Math.max(hit.x, -4.2), 4.2), LIFT + 0.05, Math.min(Math.max(hit.z, -4.2), 4.2));
      }
      e.preventDefault();
    }
  }

  function onUp(e: PointerEvent): void {
    if (!down || e.pointerId !== down.id) return;
    const st = down;
    down = null;
    try { canvas.releasePointerCapture(e.pointerId); } catch { /* ignore */ }
    if (st.drag && st.actor) {
      aim(e);
      let target: Square | null = null;
      if (ray.ray.intersectPlane(plane, hit)) target = worldToSquare(hit);
      if (target && legal.some((m) => m.to === target)) {
        void commit(target).finally(() => rig.setInputLocked(false));
        return;
      }
      // dropped on an illegal square: glide home, stay selected
      gsap.to(st.actor.root.position, { x: squareToWorld(st.actor.square).x, z: squareToWorld(st.actor.square).z, y: LIFT, duration: 0.18, ease: 'power2.out' });
    } else if (st.toggleOff) {
      deselect();
    }
    rig.setInputLocked(false);
  }

  function onCancel(): void {
    if (down?.actor && selected) deselect();
    down = null;
    rig.setInputLocked(false);
  }

  canvas.addEventListener('pointerdown', onDown, { capture: true });
  canvas.addEventListener('pointermove', onMove);
  canvas.addEventListener('pointerup', onUp);
  canvas.addEventListener('pointercancel', onCancel);

  const offs = [
    d.bus.on('move:resolved', () => deselect(false)),
    d.bus.on('game:start', () => { deselect(false); markers.setLastMove(null, null); lastPly = -1; }),
    d.bus.on('turn:start', () => { if (selected && !controller.canSelect(selected.square)) deselect(false); }),
  ];
  const offSnap = controller.subscribe((s) => {
    if (s.moves.length === lastPly) return;
    lastPly = s.moves.length;
    const last = s.moves[s.moves.length - 1];
    markers.setLastMove(last?.from ?? null, last?.to ?? null);
  });
  markers.setColorBlind(d.settings.get().colorBlind);
  const offSet = d.settings.subscribe((s, k) => { if (k === 'colorBlind') markers.setColorBlind(s.colorBlind); });

  return {
    dispose() {
      canvas.removeEventListener('pointerdown', onDown, { capture: true });
      canvas.removeEventListener('pointermove', onMove);
      canvas.removeEventListener('pointerup', onUp);
      canvas.removeEventListener('pointercancel', onCancel);
      offs.forEach((f) => f());
      offSnap(); offSet();
    },
  };
}
