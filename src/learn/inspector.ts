// Piece inspector: a private three.js scene (own lights, pedestal, shared environment map) drawn through a pane.
// Drag to orbit, wheel / pinch to zoom, auto-rotate while idle. Plays Idle / Attack / Taunt / Surrender on demand.
import { gsap } from 'gsap';
import {
  AdditiveBlending, CanvasTexture, CircleGeometry, Color, CylinderGeometry, DirectionalLight, HemisphereLight, Mesh, MeshBasicMaterial,
  MeshStandardMaterial, PerspectiveCamera, Scene, SRGBColorSpace, TorusGeometry, Vector3, type Material, type Texture,
} from 'three';
import type { Faction, Role } from '../contracts';
import { PALETTE, ROLE_HEIGHT } from '../contracts';
import type { PieceActorImpl } from '../assets/pieceActor';
import type { AppServices } from '../main';
import type { Pane, PaneManager } from './panes';

export type InspectorClip = 'Idle' | 'Attack' | 'Taunt' | 'Surrender';
export const INSPECTOR_CLIPS: readonly InspectorClip[] = ['Idle', 'Attack', 'Taunt', 'Surrender'];

export interface Inspector {
  readonly pane: Pane;
  readonly el: HTMLCanvasElement;
  setPiece(faction: Faction, role: Role): void;
  play(clip: InspectorClip): void;
  autoRotate: boolean;
  /** Freeze rendering (no GPU work) until resumed. */
  paused: boolean;
  resetView(): void;
  zoom(delta: number): void;
  dispose(): void;
}

const TINT: Record<Faction, number> = { emberhold: PALETTE.emberhold.ember, rime: PALETTE.rime.glow };

function glowTexture(): CanvasTexture {
  const c = document.createElement('canvas');
  c.width = c.height = 128;
  const g = c.getContext('2d')!;
  const rg = g.createRadialGradient(64, 64, 0, 64, 64, 64);
  rg.addColorStop(0, 'rgba(255,255,255,0.9)'); rg.addColorStop(0.5, 'rgba(255,255,255,0.25)'); rg.addColorStop(1, 'rgba(255,255,255,0)');
  g.fillStyle = rg; g.fillRect(0, 0, 128, 128);
  const t = new CanvasTexture(c);
  t.colorSpace = SRGBColorSpace;
  return t;
}

export function createInspector(s: AppServices, panes: PaneManager): Inspector {
  const scene = new Scene();
  scene.background = new Color(0x0a0909);
  scene.environment = s.scene.environment;
  scene.environmentIntensity = s.scene.environmentIntensity;
  const camera = new PerspectiveCamera(30, 1, 0.1, 60);

  const hemi = new HemisphereLight(0xcdd6ff, 0x1c140e, 0.6);
  const key = new DirectionalLight(0xffe4c0, 2.4); key.position.set(3, 5, 4);
  const rim = new DirectionalLight(0xffffff, 2.0); rim.position.set(-4, 3, -4);
  scene.add(hemi, key, rim);

  const geos: Array<{ dispose(): void }> = [];
  const mats: Material[] = [];
  const texes: Texture[] = [];
  const own = <T extends { dispose(): void }>(g: T): T => { geos.push(g); return g; };
  const ownM = <M extends Material>(m: M): M => { mats.push(m); return m; };

  const plate = new Mesh(own(new CylinderGeometry(0.95, 1.05, 0.12, 48)), ownM(new MeshStandardMaterial({ color: 0x171417, roughness: 0.55, metalness: 0.6 })));
  plate.position.y = -0.06;
  const ringMat = ownM(new MeshBasicMaterial({ color: 0xffffff }));
  const ring = new Mesh(own(new TorusGeometry(0.98, 0.018, 8, 64)), ringMat);
  ring.rotation.x = Math.PI / 2; ring.position.y = 0.002;
  const glowTex = glowTexture(); texes.push(glowTex);
  const glowMat = ownM(new MeshBasicMaterial({ map: glowTex, transparent: true, depthWrite: false, blending: AdditiveBlending, opacity: 0.55 }));
  const glow = new Mesh(own(new CircleGeometry(1.9, 32)), glowMat);
  glow.rotation.x = -Math.PI / 2; glow.position.y = -0.119;
  scene.add(plate, ring, glow);

  // orbit state
  const view = { az: 0.6, polar: 1.28, dist: 4.2, target: new Vector3(0, 0.7, 0) };
  const home = { az: 0.6, polar: 1.28, dist: 4.2 };
  let actor: PieceActorImpl | null = null;
  let timeline: ReturnType<typeof gsap.timeline> | null = null;
  let lastUpdate = 0;
  let interacting = false;
  let idleSince = 0;
  let disposed = false;
  const api = { autoRotate: true, paused: false } as { autoRotate: boolean; paused: boolean };

  const pane = panes.create({ scene, camera, maxSide: 640, fps: 30 });
  pane.el.classList.add('learn-inspector-canvas');
  pane.el.setAttribute('role', 'img');
  pane.el.tabIndex = 0;

  function placeCamera() {
    const sp = Math.sin(view.polar);
    camera.position.set(view.target.x + view.dist * sp * Math.sin(view.az), view.target.y + view.dist * Math.cos(view.polar), view.target.z + view.dist * sp * Math.cos(view.az));
    camera.lookAt(view.target);
  }

  pane.needsRender = () => !api.paused;
  pane.before = () => {
    const now = performance.now();
    const dt = lastUpdate ? Math.min(0.1, (now - lastUpdate) / 1000) : 0.016;
    lastUpdate = now;
    if (api.autoRotate && !interacting && now - idleSince > 2500) view.az += dt * 0.45;
    placeCamera();
    actor?.update(dt);
  };
  pane.onVisible = (v) => { if (v) lastUpdate = 0; };

  // ---- pointer input
  const pts = new Map<number, { x: number; y: number }>();
  let pinch = 0;
  const touchIdle = () => { idleSince = performance.now(); };
  const el = pane.el;
  el.style.touchAction = 'none';
  el.addEventListener('pointerdown', (e) => {
    pts.set(e.pointerId, { x: e.clientX, y: e.clientY });
    try { el.setPointerCapture(e.pointerId); } catch { /* ignore */ }
    interacting = true;
    if (pts.size === 2) { const [a, b] = [...pts.values()]; pinch = Math.hypot(a.x - b.x, a.y - b.y); }
    api.paused = false;
  });
  el.addEventListener('pointermove', (e) => {
    const p = pts.get(e.pointerId);
    if (!p) return;
    const dx = e.clientX - p.x, dy = e.clientY - p.y;
    p.x = e.clientX; p.y = e.clientY;
    if (pts.size === 1) {
      view.az -= dx * 0.008;
      view.polar = Math.min(1.5, Math.max(0.35, view.polar - dy * 0.006));
    } else if (pts.size === 2) {
      const [a, b] = [...pts.values()];
      const d = Math.hypot(a.x - b.x, a.y - b.y);
      if (pinch > 0) view.dist = Math.min(7.5, Math.max(1.8, view.dist * (pinch / d)));
      pinch = d;
    }
    touchIdle();
  });
  const up = (e: PointerEvent) => { pts.delete(e.pointerId); if (pts.size < 2) pinch = 0; if (!pts.size) { interacting = false; touchIdle(); } };
  el.addEventListener('pointerup', up); el.addEventListener('pointercancel', up);
  el.addEventListener('wheel', (e) => { e.preventDefault(); view.dist = Math.min(7.5, Math.max(1.8, view.dist * (1 + Math.sign(e.deltaY) * 0.08))); touchIdle(); api.paused = false; }, { passive: false });
  el.addEventListener('keydown', (e) => {
    const k = e.key;
    if (k === 'ArrowLeft') view.az += 0.15; else if (k === 'ArrowRight') view.az -= 0.15;
    else if (k === 'ArrowUp') view.polar = Math.max(0.35, view.polar - 0.1); else if (k === 'ArrowDown') view.polar = Math.min(1.5, view.polar + 0.1);
    else if (k === '+' || k === '=') view.dist = Math.max(1.8, view.dist * 0.9); else if (k === '-') view.dist = Math.min(7.5, view.dist / 0.9);
    else return;
    e.preventDefault(); touchIdle();
  });

  function killTimeline() { timeline?.kill(); timeline = null; }

  function settle() {
    if (!actor || disposed) return;
    actor.root.position.set(0, 0, 0);
    actor.root.rotation.y = 0;
    actor.resetPose();
  }

  function dropActor() {
    killTimeline();
    if (actor) { gsap.killTweensOf(actor.model.rotation); gsap.killTweensOf(actor.model.position); scene.remove(actor.root); actor.dispose(); actor = null; }
  }

  const inspector: Inspector = {
    pane, el,
    get autoRotate() { return api.autoRotate; }, set autoRotate(v) { api.autoRotate = v; touchIdle(); },
    get paused() { return api.paused; }, set paused(v) { api.paused = v; },

    setPiece(faction, role) {
      dropActor();
      const prev = s.registry.lod;
      s.registry.lod = 1; // reduced meshes: this view is small and the target GPUs are weak
      try { actor = s.registry.createActor(faction, role, 'e4'); } finally { s.registry.lod = prev; }
      actor.root.position.set(0, 0, 0);
      actor.root.rotation.y = 0;
      scene.add(actor.root);
      const c = new Color(TINT[faction]);
      ringMat.color.copy(c); glowMat.color.copy(c);
      rim.color.copy(c).lerp(new Color(0xffffff), 0.45);
      const hgt = ROLE_HEIGHT[role];
      view.target.set(0, hgt * 0.5 + 0.08, 0);
      home.dist = 2.6 + hgt * 1.3; view.dist = home.dist;
      actor.play('Idle');
      pane.el.setAttribute('aria-label', `${role} of the ${faction === 'emberhold' ? 'Emberhold' : 'Rime Host'}, 3D view. Drag to rotate, scroll or pinch to zoom.`);
      api.paused = false;
    },

    play(clip) {
      if (!actor) return;
      killTimeline();
      gsap.killTweensOf(actor.model.rotation); gsap.killTweensOf(actor.model.position);
      settle();
      api.paused = false;
      if (clip === 'Idle') return;
      const a = actor;
      const back = () => gsap.delayedCall(0.5, () => { if (actor === a) settle(); });
      if (clip === 'Attack') {
        timeline = a.attackTimeline();
        timeline.eventCallback('onComplete', back);
      } else if (a.hasClip(clip)) {
        timeline = a.clipTimeline(clip);
        if (clip === 'Taunt') timeline.eventCallback('onComplete', back); // Surrender holds its pose until another action
      } else if (clip === 'Taunt') {
        timeline = gsap.timeline({ onComplete: back });
        timeline.to(a.model.rotation, { x: 0.35, duration: 0.25, ease: 'power2.out' }).to(a.model.rotation, { x: -0.1, duration: 0.2 }).to(a.model.rotation, { x: 0.3, duration: 0.2 }).to(a.model.rotation, { x: 0, duration: 0.3 });
      } else {
        timeline = gsap.timeline();
        timeline.to(a.model.position, { y: -0.12, duration: 0.8, ease: 'power2.out' }, 0).to(a.model.rotation, { x: 0.45, duration: 0.8, ease: 'power2.out' }, 0);
      }
    },

    resetView() { view.az = home.az; view.polar = home.polar; view.dist = home.dist; touchIdle(); api.paused = false; },
    zoom(d) { view.dist = Math.min(7.5, Math.max(1.8, view.dist * (1 + d))); touchIdle(); api.paused = false; },

    dispose() {
      if (disposed) return;
      disposed = true;
      dropActor();
      pane.dispose();
      scene.remove(plate, ring, glow, hemi, key, rim);
      key.dispose?.(); rim.dispose?.(); hemi.dispose?.();
      geos.forEach((g) => g.dispose()); mats.forEach((m) => m.dispose()); texes.forEach((t) => t.dispose());
      scene.environment = null;
    },
  };
  placeCamera();
  return inspector;
}
