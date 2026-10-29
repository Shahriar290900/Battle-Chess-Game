// Board input (architecture §8): pointer events for mouse and touch; click-click and drag-drop; free-look camera gestures.
// Selecting lifts the piece 0.12 and shows legal markers. Input is ignored while a modal is open;
// a tap during a sequence skips it; the controller itself refuses moves on the AI's turn.
//
// Picking (render-readability): a pointer resolves to a piece by testing the pointer against each piece's *visible body* projected to
// the screen (a tapered capsule from its base to its top; nearest to the camera wins), then falls back to the tile under the pointer.
// This replaces the old tall cylinder colliders, which let a tall piece steal clicks meant for the piece standing behind it, and let a
// re-click on the upper body of the selected piece resolve to the legal square behind it (that played a move on a double-click).
// Rules: a click on the selected piece (anywhere on its body) toggles it off and never moves; among bodies under the pointer the
// piece whose own square is the tile under the pointer wins (tile first), the nearest body otherwise; a legal destination wins over
// an occluding piece that cannot be selected or captured.
//
// Free-look: mouse drag on empty space (or right/middle button anywhere), wheel, two-finger drag and pinch orbit/zoom the camera
// (CameraRig.orbit / zoom). A plain tap still selects. The camera eases back after a move, on R (or the HUD button), and
// G / the HUD button flies to the captured-pieces ledges ("View fallen"). The HUD talks to this module through window events
// 'bc:camera' ({detail: 'recenter' | 'fallen'}) and listens to 'bc:camera-state' ({detail: {fallen, off}}).
import { gsap } from 'gsap';
import { Plane, Raycaster, Vector2, Vector3 } from 'three';
import type { EventBus, Faction, Role, SettingsStore, Side, Square } from '../contracts';
import { BOARD_PIECE_SCALE, ROLE_HEIGHT, SIDE_FACTION, squareToWorld, worldToSquare } from '../contracts';
import type { CameraRigImpl } from '../camera/cameraRig';
import type { GameController } from '../core/game';
import type { LegalMove } from '../core/rules';
import type { PieceActorImpl } from '../assets/pieceActor';
import type { BoardImpl } from '../render/board';
import type { Markers } from '../render/markers';

export interface BoardInput {
  dispose(): void;
  /** Test hook (window.__bc.input): what a pointer at these client coordinates would resolve to, plus the selection state. */
  debugPick(x: number, y: number, touch?: boolean): { sq: Square | null; actor: string | null; selected: Square | null; legal: Square[] };
}

const LIFT = 0.12;
const DRAG_PX = 9;
const DRAG_PX_TOUCH = 12; // fingers wobble, but a long slow drag must still start (the old 16 px lost slow headless drags)
const TOUCH_DRAG_LIFT = 0.5; // the dragged piece floats above the fingertip so the finger does not hide it
const MAGNET = 0.6; // squares: a drop this close to a legal square snaps to it
const ORBIT_SENS = 0.0062; // radians per px
const DEG = Math.PI / 180;

/** Visible-body radii (world units at BOARD_PIECE_SCALE): the pedestal at the base, tapering to the head. */
const BASE_R = 0.34;
const TOP_R: Record<Role, number> = { pawn: 0.2, rook: 0.3, knight: 0.27, bishop: 0.21, queen: 0.27, king: 0.25 };

interface BodyHit { actor: PieceActorImpl; nd: number; depth: number }

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
  const va = new Vector3(), vb = new Vector3();

  let selected: PieceActorImpl | null = null;
  let legal: LegalMove[] = [];
  let legalSet = new Set<Square>();
  let down: { id: number; x: number; y: number; actor: PieceActorImpl | null; toggleOff: boolean; drag: boolean; fresh: boolean; touch: boolean; ghost: boolean } | null = null;
  /** Mouse drag on empty space (or right/middle button): orbits the camera; a motionless release is a tap. */
  let orbit: { id: number; x: number; y: number; started: boolean; tap: boolean } | null = null;
  /** Active touch pointers (for the two-finger gesture) and the gesture itself. */
  const touches = new Map<number, { x: number; y: number }>();
  let gesture: { a: number; b: number; mx: number; my: number; dist: number } | null = null;
  const ignored = new Set<number>(); // pointers that belonged to a gesture: their release is not a tap
  let lastPly = -1;
  /** When / where the current selection was made: a second press on the same spot right after it is a double-click, never a move. */
  let lastSelect = { t: 0, x: -999, y: -999 };
  let hoverSq: Square | null = null;

  // ------------------------------------------------------------------ picking
  function aim(e: { clientX: number; clientY: number }): void {
    const r = canvas.getBoundingClientRect();
    ndc.set(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1);
    ray.setFromCamera(ndc, rig.camera);
  }

  /** Piece bodies under the pointer, in screen space. `slack` widens the bodies (touch). */
  function bodyHits(cx: number, cy: number, slack: number, padPx: number, ignore?: PieceActorImpl | null): BodyHit[] {
    const r = canvas.getBoundingClientRect();
    const cam = rig.camera;
    cam.updateMatrixWorld();
    const f = (r.height / 2) / Math.tan((cam.fov * DEG) / 2);
    const mx = r.left + r.width / 2, my = r.top + r.height / 2;
    const out: BodyHit[] = [];
    for (const a of board.allActors()) {
      if (a === ignore || !a.root.visible || a.fade < 0.05) continue;
      const p = a.root.position;
      const sc = a.root.scale.x;
      const sf = sc / BOARD_PIECE_SCALE;
      va.set(p.x, p.y + 0.03, p.z).applyMatrix4(cam.matrixWorldInverse);
      vb.set(p.x, p.y + ROLE_HEIGHT[a.role] * sc * 0.96, p.z).applyMatrix4(cam.matrixWorldInverse);
      const dB = -va.z, dT = -vb.z;
      if (dB < 0.3 || dT < 0.3) continue;
      const ax = mx + (va.x * f) / dB, ay = my - (va.y * f) / dB;
      const bx = mx + (vb.x * f) / dT, by = my - (vb.y * f) / dT;
      const sx = bx - ax, sy = by - ay;
      const len2 = sx * sx + sy * sy;
      const t = len2 > 1e-6 ? Math.min(1, Math.max(0, ((cx - ax) * sx + (cy - ay) * sy) / len2)) : 0;
      const dist = Math.hypot(cx - (ax + sx * t), cy - (ay + sy * t));
      const depth = dB + (dT - dB) * t;
      const rPx = ((BASE_R + (TOP_R[a.role] - BASE_R) * t) * sf * f) / depth;
      const nd = Math.max(0, dist - padPx) / rPx;
      if (nd <= slack) out.push({ actor: a, nd, depth });
    }
    return out;
  }

  /** Which square (and piece) did the pointer mean? */
  function squareAt(e: PointerEvent | MouseEvent, ignore?: PieceActorImpl | null): { sq: Square | null; actor: PieceActorImpl | null } {
    aim(e);
    const tileSq = board.pickSquare(ray);
    const coarse = (e as PointerEvent).pointerType === 'touch' || (e as PointerEvent).pointerType === 'pen';
    // Tight pass first (the visible bodies, a few px of play): fat-finger slack must never let a tall piece win a tap that is
    // squarely on the tile of the piece behind it. Only when nothing is hit and the tile offers nothing does the wide pass run.
    let hits = bodyHits(e.clientX, e.clientY, 1, coarse ? 4 : 2, ignore);
    if (!hits.length && coarse && !(tileSq && (board.actorAt(tileSq) || legalSet.has(tileSq)))) {
      hits = bodyHits(e.clientX, e.clientY, 1.9, 16, ignore).sort((a, b) => a.nd - b.nd).slice(0, 1);
    }
    let best: BodyHit | undefined;
    if (hits.length) {
      hits.sort((a, b) => a.depth - b.depth);
      best = hits[0];
      // Tile first: the piece whose BASE square is under the pointer wins over a nearer body that merely overlaps it on screen (a pawn
      // head in front of the knight behind it); only the selected piece keeps its body (a re-press on it toggles, never moves).
      const atTile = tileSq ? hits.find((h) => h.actor.square === tileSq) : undefined;
      if (atTile && atTile !== best && best.actor !== selected) best = atTile;
    }
    // A legal destination under the pointer beats a body of ANOTHER piece the pointer only grazes (a tall piece in front of the
    // marker): only a pointer well inside that body (nd <= 0.45) or on the selected piece itself overrides it.
    if (best && selected && tileSq && legalSet.has(tileSq) && best.actor !== selected && best.actor.square !== tileSq && best.nd > 0.45) {
      return { sq: tileSq, actor: board.actorAt(tileSq) ?? null };
    }
    if (best) {
      const a = best.actor;
      if (a === selected) {
        // The head of the selected piece can overlap the destination tile behind it. A press on the body toggles the piece, except for a
        // deliberate (not double-click) press on a legal tile: that is the move. A quick re-press never moves.
        const quick = performance.now() - lastSelect.t < 600 && Math.hypot(e.clientX - lastSelect.x, e.clientY - lastSelect.y) < 28;
        if (!quick && tileSq && legalSet.has(tileSq) && tileSq !== a.square) return { sq: tileSq, actor: board.actorAt(tileSq) ?? null };
        return { sq: a.square, actor: a };
      }
      if (selected && legalSet.has(a.square)) return { sq: a.square, actor: a }; // capture
      if (controller.canSelect(a.square)) return { sq: a.square, actor: a };
      if (selected && tileSq && legalSet.has(tileSq)) return { sq: tileSq, actor: board.actorAt(tileSq) ?? null };
      return { sq: a.square, actor: a };
    }
    if (tileSq) return { sq: tileSq, actor: board.actorAt(tileSq) ?? null };
    return { sq: null, actor: null };
  }

  /** The legal square a drop at `point` (plane y = LIFT) means: the tile under it if legal, else the nearest legal one within MAGNET. */
  function dropTarget(point: Vector3): Square | null {
    const exact = worldToSquare(point);
    if (exact && legalSet.has(exact)) return exact;
    let best: Square | null = null, bd = MAGNET;
    for (const m of legal) {
      const c = squareToWorld(m.to, va);
      const dd = Math.hypot(c.x - point.x, c.z - point.z);
      if (dd < bd) { bd = dd; best = m.to; }
    }
    return best;
  }

  // ------------------------------------------------------------------ selection
  function lower(actor: PieceActorImpl, animate: boolean): void {
    gsap.killTweensOf(actor.root.position);
    const p = squareToWorld(actor.square);
    if (animate) gsap.to(actor.root.position, { x: p.x, z: p.z, y: 0, duration: 0.15, ease: 'power2.out' });
    else actor.root.position.set(p.x, 0, p.z);
  }

  function unghost(actor: PieceActorImpl): void {
    if (actor.fade < 1) actor.setFade(1);
  }

  function deselect(animate = true): void {
    if (selected) { unghost(selected); selected.setHighlight(false); lower(selected, animate); }
    selected = null;
    legal = [];
    legalSet = new Set();
    markers.clear();
    markers.setSelected(null);
    markers.setHover(null);
  }

  function select(actor: PieceActorImpl): void {
    if (selected && selected !== actor) deselect();
    selected = actor;
    legal = controller.legalMovesFrom(actor.square);
    legalSet = new Set(legal.map((m) => m.to));
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
    unghost(actor);
    actor.setHighlight(false);
    lower(actor, false);
    markers.clear();
    markers.setSelected(null);
    markers.setHover(null);
    selected = null;
    legal = [];
    legalSet = new Set();
    void rig.recenter(0.55); // free-look eases back once the player moves
    const ok = await controller.attemptMove(from, to);
    if (!ok && controller.canSelect(from)) {
      const a = board.actorAt(from);
      if (a) select(a);
    }
  }

  // ------------------------------------------------------------------ free-look helpers
  const freeLookOk = () => !d.isBlocked() && rig.canFreeLook && controller.state !== 'resolving' && controller.state !== 'sequence' && controller.state !== 'postMove';

  function startGesture(): void {
    const ids = [...touches.keys()];
    if (ids.length < 2) return;
    const [a, b] = ids;
    const pa = touches.get(a)!, pb = touches.get(b)!;
    gesture = { a, b, mx: (pa.x + pb.x) / 2, my: (pa.y + pb.y) / 2, dist: Math.hypot(pa.x - pb.x, pa.y - pb.y) };
    // Two fingers are a camera gesture, never a move: drop any drag / half-made selection from the first finger.
    if (down) {
      const st = down;
      down = null;
      if (st.actor) {
        if (st.fresh && selected === st.actor) { unghost(st.actor); deselect(); } else endGlide(st); // still selected: back to its lifted home
      }
      rig.setInputLocked(false);
    }
    orbit = null;
    ignored.add(a); ignored.add(b);
    markers.setHover(null);
  }

  // ------------------------------------------------------------------ pointer handlers
  function onDown(e: PointerEvent): void {
    if (d.isBlocked()) return;
    const isTouch = e.pointerType === 'touch';
    if (isTouch) {
      touches.set(e.pointerId, { x: e.clientX, y: e.clientY });
      if (touches.size >= 2 && !gesture) {
        if (freeLookOk() || controller.state === 'aiThinking') { startGesture(); e.preventDefault(); return; }
      }
      if (gesture) { ignored.add(e.pointerId); e.preventDefault(); return; }
    }
    const secondary = e.button !== undefined && e.button > 0;
    if (secondary) {
      // right / middle button: orbit from anywhere
      if (e.button === 2 || e.button === 1) {
        if (freeLookOk()) {
          orbit = { id: e.pointerId, x: e.clientX, y: e.clientY, started: false, tap: false };
          try { canvas.setPointerCapture(e.pointerId); } catch { /* synthetic events */ }
          e.preventDefault();
        }
      }
      return;
    }
    if (controller.state === 'resolving' || controller.state === 'sequence' || controller.state === 'postMove') {
      controller.skip();
      e.preventDefault();
      return;
    }
    const idle = controller.state === 'aiThinking' || controller.state === 'gameOver';
    if (controller.state !== 'awaitInput' && !idle) return;
    const beginOrbitOrTap = (): void => {
      if (!isTouch && freeLookOk()) {
        orbit = { id: e.pointerId, x: e.clientX, y: e.clientY, started: false, tap: true };
        try { canvas.setPointerCapture(e.pointerId); } catch { /* synthetic events */ }
        e.preventDefault();
      } else if (controller.state === 'awaitInput') deselect();
    };
    if (idle) { if (!isTouch && freeLookOk()) beginOrbitOrTap(); return; }
    const { sq, actor } = squareAt(e);
    if (!sq) { beginOrbitOrTap(); return; }
    if (selected && legalSet.has(sq) && !(actor && actor === selected)) {
      rig.setInputLocked(true);
      void commit(sq).finally(() => rig.setInputLocked(false));
      e.preventDefault();
      return;
    }
    if (actor && controller.canSelect(sq)) {
      const toggleOff = selected === actor;
      const fresh = !toggleOff;
      if (!toggleOff) { select(actor); lastSelect = { t: performance.now(), x: e.clientX, y: e.clientY }; }
      rig.setInputLocked(true);
      down = { id: e.pointerId, x: e.clientX, y: e.clientY, actor, toggleOff, drag: false, fresh, touch: isTouch, ghost: false };
      try { canvas.setPointerCapture(e.pointerId); } catch { /* synthetic events */ }
      e.preventDefault();
      markers.setHover(null);
      return;
    }
    // an empty / non-selectable square: a tap deselects, a mouse drag orbits
    if (!isTouch && freeLookOk()) beginOrbitOrTap();
    else deselect();
  }

  function updateHover(e: PointerEvent): void {
    if (e.pointerType !== 'mouse' || d.isBlocked() || controller.state !== 'awaitInput') {
      if (hoverSq) { hoverSq = null; markers.setHover(null); }
      return;
    }
    const { sq, actor } = squareAt(e);
    const actionable = !!sq && ((!!actor && controller.canSelect(sq)) || legalSet.has(sq));
    canvas.style.cursor = actionable ? 'pointer' : '';
    const next = actionable ? sq : null;
    if (next !== hoverSq) { hoverSq = next; markers.setHover(next); }
  }

  function onMove(e: PointerEvent): void {
    if (e.pointerType === 'touch' && touches.has(e.pointerId)) {
      const t = touches.get(e.pointerId)!;
      t.x = e.clientX; t.y = e.clientY;
      if (gesture && (e.pointerId === gesture.a || e.pointerId === gesture.b)) {
        const pa = touches.get(gesture.a), pb = touches.get(gesture.b);
        if (pa && pb) {
          const mx = (pa.x + pb.x) / 2, my = (pa.y + pb.y) / 2;
          const dist = Math.hypot(pa.x - pb.x, pa.y - pb.y);
          rig.orbit(-(mx - gesture.mx) * ORBIT_SENS * 1.15, -(my - gesture.my) * ORBIT_SENS);
          if (dist > 8 && gesture.dist > 8) rig.zoom(gesture.dist / dist);
          gesture.mx = mx; gesture.my = my; gesture.dist = dist;
        }
        e.preventDefault();
        return;
      }
    }
    if (orbit && e.pointerId === orbit.id) {
      const dx = e.clientX - orbit.x, dy = e.clientY - orbit.y;
      if (!orbit.started && Math.hypot(dx, dy) > DRAG_PX) { orbit.started = true; canvas.style.cursor = 'grabbing'; markers.setHover(null); hoverSq = null; }
      if (orbit.started) {
        rig.orbit(-dx * ORBIT_SENS, -dy * ORBIT_SENS);
        orbit.x = e.clientX; orbit.y = e.clientY;
        e.preventDefault();
      }
      return;
    }
    if (!down || e.pointerId !== down.id || !down.actor) {
      if (!down) updateHover(e);
      return;
    }
    if (!down.drag && Math.hypot(e.clientX - down.x, e.clientY - down.y) > (e.pointerType === 'mouse' ? DRAG_PX : DRAG_PX_TOUCH)) {
      down.drag = true;
      if (selected !== down.actor) select(down.actor);
      // A dimmed ghost of the piece follows the pointer; the origin square stays marked as selected.
      down.actor.setFade(0.6);
      down.ghost = true;
    }
    if (down.drag) {
      aim(e);
      if (ray.ray.intersectPlane(plane, hit)) {
        gsap.killTweensOf(down.actor.root.position);
        const x = Math.min(Math.max(hit.x, -4.2), 4.2), z = Math.min(Math.max(hit.z, -4.2), 4.2);
        down.actor.root.position.set(x, LIFT + 0.05 + (down.touch ? TOUCH_DRAG_LIFT : 0), z);
        const snap = dropTarget(hit);
        markers.setHover(snap, true);
      }
      e.preventDefault();
    }
  }

  function endGlide(st: NonNullable<typeof down>): void {
    if (!st.actor) return;
    const p = squareToWorld(st.actor.square);
    unghost(st.actor);
    gsap.to(st.actor.root.position, { x: p.x, z: p.z, y: LIFT, duration: 0.18, ease: 'power2.out' });
  }

  function onUp(e: PointerEvent): void {
    const wasTouch = touches.delete(e.pointerId);
    if (wasTouch && gesture && (e.pointerId === gesture.a || e.pointerId === gesture.b)) { gesture = null; ignored.add(e.pointerId); }
    if (ignored.delete(e.pointerId)) return; // a finger of a camera gesture: not a tap
    if (orbit && e.pointerId === orbit.id) {
      const st = orbit;
      orbit = null;
      try { canvas.releasePointerCapture(e.pointerId); } catch { /* ignore */ }
      canvas.style.cursor = '';
      if (!st.started && st.tap && controller.state === 'awaitInput') deselect();
      return;
    }
    if (!down || e.pointerId !== down.id) return;
    const st = down;
    down = null;
    try { canvas.releasePointerCapture(e.pointerId); } catch { /* ignore */ }
    markers.setHover(null);
    hoverSq = null;
    if (st.drag && st.actor) {
      aim(e);
      let target: Square | null = null;
      if (ray.ray.intersectPlane(plane, hit)) target = dropTarget(hit);
      if (target) {
        void commit(target).finally(() => rig.setInputLocked(false));
        return;
      }
      // dropped on an illegal square: glide home, stay selected
      endGlide(st);
    } else if (st.toggleOff) {
      deselect();
    }
    rig.setInputLocked(false);
  }

  function onCancel(e: PointerEvent): void {
    touches.delete(e.pointerId);
    if (gesture && (e.pointerId === gesture.a || e.pointerId === gesture.b)) gesture = null;
    ignored.delete(e.pointerId);
    if (orbit && e.pointerId === orbit.id) { orbit = null; canvas.style.cursor = ''; }
    if (down && e.pointerId === down.id) {
      // The system took the pointer (a system gesture): put the piece back but keep the selection.
      const st = down;
      down = null;
      if (st.drag) endGlide(st); else if (st.actor) unghost(st.actor);
      markers.setHover(null);
      rig.setInputLocked(false);
    }
  }

  function onLeave(): void {
    if (hoverSq) { hoverSq = null; markers.setHover(null); }
  }

  function onWheel(e: WheelEvent): void {
    if (d.isBlocked() || !rig.canFreeLook) return;
    e.preventDefault();
    const unit = e.deltaMode === 1 ? 33 : e.deltaMode === 2 ? 400 : 1;
    const k = e.ctrlKey ? 0.01 : 0.0016; // trackpad pinch arrives as ctrl+wheel with small deltas
    rig.zoom(Math.exp(e.deltaY * unit * k));
  }

  const onContext = (e: Event) => e.preventDefault();

  canvas.addEventListener('pointerdown', onDown, { capture: true });
  canvas.addEventListener('pointermove', onMove);
  canvas.addEventListener('pointerup', onUp);
  canvas.addEventListener('pointercancel', onCancel);
  canvas.addEventListener('pointerleave', onLeave);
  canvas.addEventListener('wheel', onWheel, { passive: false });
  canvas.addEventListener('contextmenu', onContext);

  // ------------------------------------------------------------------ camera commands (keys + HUD buttons)
  /** Ledge order for "View fallen": the seat's trophies (the opponent's pieces it captured) first. */
  const ledgeOrder = (seat: Side): Faction[] => (seat === 'w' ? [SIDE_FACTION.b, SIDE_FACTION.w] : [SIDE_FACTION.w, SIDE_FACTION.b]);
  let fallenFaction: Faction | null = null;

  function viewFallenNext(): void {
    if (!rig.canFreeLook || d.isBlocked()) return;
    const order = ledgeOrder(rig.seat);
    const have = order.filter((f) => board.graveyard.countOf(f) > 0);
    const list = have.length ? have : [order[0]];
    if (rig.view === 'seat' || fallenFaction === null) fallenFaction = null;
    const i = fallenFaction === null ? -1 : list.indexOf(fallenFaction);
    const next = i + 1;
    if (next >= list.length) { fallenFaction = null; void rig.viewFallen(null); return; }
    fallenFaction = list[next];
    void rig.viewFallen(board.graveyard.viewOf(fallenFaction));
  }

  function recenter(): void {
    fallenFaction = null;
    void rig.recenter(0.7);
  }

  const inGame = () => {
    const s = controller.state;
    return s !== 'boot' && s !== 'loading' && s !== 'menu';
  };
  function onKey(e: KeyboardEvent): void {
    if (e.ctrlKey || e.metaKey || e.altKey || e.repeat || d.isBlocked() || !inGame()) return;
    const a = document.activeElement as HTMLElement | null;
    if (a && a !== document.body && a.closest?.('input,select,textarea')) return;
    const k = e.key.toLowerCase();
    if (k === 'r') { recenter(); e.preventDefault(); }
    else if (k === 'g') { viewFallenNext(); e.preventDefault(); }
  }
  window.addEventListener('keydown', onKey);
  const onCamCmd = (e: Event) => {
    if (d.isBlocked() || !inGame()) return;
    const cmd = (e as CustomEvent<string>).detail;
    if (cmd === 'recenter') recenter(); else if (cmd === 'fallen') viewFallenNext();
  };
  window.addEventListener('bc:camera', onCamCmd);
  const offView = rig.onViewChange(() => {
    if (rig.view === 'seat') fallenFaction = null;
    window.dispatchEvent(new CustomEvent('bc:camera-state', { detail: { fallen: rig.view === 'fallen', off: rig.offSeat } }));
  });

  const offs = [
    d.bus.on('move:resolved', () => deselect(false)),
    d.bus.on('game:start', () => { deselect(false); markers.setLastMove(null, null); lastPly = -1; fallenFaction = null; void rig.recenter(0); }),
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
    debugPick(x, y, touch = false) {
      const r = squareAt({ clientX: x, clientY: y, pointerType: touch ? 'touch' : 'mouse' } as unknown as PointerEvent);
      return { sq: r.sq, actor: r.actor ? `${r.actor.id}@${r.actor.square}` : null, selected: selected?.square ?? null, legal: [...legalSet] };
    },
    dispose() {
      canvas.removeEventListener('pointerdown', onDown, { capture: true });
      canvas.removeEventListener('pointermove', onMove);
      canvas.removeEventListener('pointerup', onUp);
      canvas.removeEventListener('pointercancel', onCancel);
      canvas.removeEventListener('pointerleave', onLeave);
      canvas.removeEventListener('wheel', onWheel);
      canvas.removeEventListener('contextmenu', onContext);
      window.removeEventListener('keydown', onKey);
      window.removeEventListener('bc:camera', onCamCmd);
      offView();
      offs.forEach((f) => f());
      offSnap(); offSet();
    },
  };
}
