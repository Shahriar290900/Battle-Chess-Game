// Board hints: legal-move markers (glow discs, red rings on capturable squares), selected-square frame
// and last-move highlights. The colour-blind option swaps to distinct shapes (diamond / crossed ring)
// and a blue/orange palette so meaning never depends on hue alone.
import { CanvasTexture, DoubleSide, Group, Mesh, MeshBasicMaterial, PlaneGeometry, SRGBColorSpace, type Scene } from 'three';
import type { Square } from '../contracts';
import { squareToWorld } from '../contracts';

export interface HintTarget { square: Square; capture: boolean }

export interface Markers {
  show(targets: HintTarget[]): void;
  clear(): void;
  setSelected(sq: Square | null): void;
  setLastMove(from: Square | null, to?: Square | null): void;
  setColorBlind(on: boolean): void;
  update(time: number): void;
}

function tex(draw: (g: CanvasRenderingContext2D, s: number) => void, size = 128): CanvasTexture {
  const c = document.createElement('canvas');
  c.width = c.height = size;
  draw(c.getContext('2d')!, size);
  const t = new CanvasTexture(c);
  t.colorSpace = SRGBColorSpace;
  return t;
}

function makeTextures() {
  const dot = tex((g, s) => {
    const rg = g.createRadialGradient(s / 2, s / 2, 0, s / 2, s / 2, s / 2);
    rg.addColorStop(0, 'rgba(255,255,255,1)'); rg.addColorStop(0.32, 'rgba(255,255,255,0.95)');
    rg.addColorStop(0.45, 'rgba(255,255,255,0.35)'); rg.addColorStop(1, 'rgba(255,255,255,0)');
    g.fillStyle = rg; g.fillRect(0, 0, s, s);
  });
  const ring = tex((g, s) => {
    const rg = g.createRadialGradient(s / 2, s / 2, s * 0.26, s / 2, s / 2, s / 2);
    rg.addColorStop(0, 'rgba(255,255,255,0)'); rg.addColorStop(0.3, 'rgba(255,255,255,0.25)');
    rg.addColorStop(0.62, 'rgba(255,255,255,1)'); rg.addColorStop(0.8, 'rgba(255,255,255,0.9)'); rg.addColorStop(1, 'rgba(255,255,255,0)');
    g.fillStyle = rg; g.fillRect(0, 0, s, s);
  });
  const diamond = tex((g, s) => {
    g.fillStyle = 'rgba(255,255,255,0.95)';
    g.beginPath(); g.moveTo(s / 2, s * 0.22); g.lineTo(s * 0.78, s / 2); g.lineTo(s / 2, s * 0.78); g.lineTo(s * 0.22, s / 2); g.closePath(); g.fill();
    g.strokeStyle = 'rgba(255,255,255,0.4)'; g.lineWidth = s * 0.05; g.stroke();
  });
  const crossRing = tex((g, s) => {
    g.strokeStyle = 'rgba(255,255,255,1)'; g.lineWidth = s * 0.09;
    g.beginPath(); g.arc(s / 2, s / 2, s * 0.36, 0, Math.PI * 2); g.stroke();
    g.lineWidth = s * 0.08; g.lineCap = 'round';
    g.beginPath(); g.moveTo(s * 0.33, s * 0.33); g.lineTo(s * 0.67, s * 0.67); g.moveTo(s * 0.67, s * 0.33); g.lineTo(s * 0.33, s * 0.67); g.stroke();
  });
  const frame = tex((g, s) => {
    g.strokeStyle = 'rgba(255,255,255,1)'; g.lineWidth = s * 0.07;
    g.strokeRect(s * 0.06, s * 0.06, s * 0.88, s * 0.88);
    g.strokeStyle = 'rgba(255,255,255,0.35)'; g.lineWidth = s * 0.14;
    g.strokeRect(s * 0.04, s * 0.04, s * 0.92, s * 0.92);
  });
  const soft = tex((g, s) => { g.fillStyle = 'rgba(255,255,255,0.55)'; g.fillRect(s * 0.04, s * 0.04, s * 0.92, s * 0.92); });
  return { dot, ring, diamond, crossRing, frame, soft };
}

export function createMarkers(scene: Scene): Markers {
  const t = makeTextures();
  const group = new Group();
  group.name = 'markers';
  scene.add(group);
  const geo = new PlaneGeometry(1, 1).rotateX(-Math.PI / 2);
  const mk = (map: CanvasTexture, color: number, opacity = 1) =>
    new MeshBasicMaterial({ map, color, transparent: true, depthWrite: false, opacity, side: DoubleSide });

  const palettes = {
    normal: { move: mk(t.dot, 0xffd27a, 0.95), capture: mk(t.ring, 0xff3a2e, 1) },
    blind: { move: mk(t.diamond, 0x3aa0ff, 0.95), capture: mk(t.crossRing, 0xff9a1a, 1) },
  };
  let blind = false;
  const selectedMat = mk(t.frame, 0xffe29a, 1);
  const lastFrom = mk(t.soft, 0xc79a52, 0.28);
  const lastTo = mk(t.soft, 0xe8c27a, 0.4);

  const pool: Mesh[] = [];
  const active: Array<{ mesh: Mesh; capture: boolean; phase: number }> = [];
  const getMesh = (): Mesh => {
    const m = pool.pop() ?? new Mesh(geo, palettes.normal.move);
    m.renderOrder = 4;
    group.add(m);
    return m;
  };
  const release = (m: Mesh) => { group.remove(m); pool.push(m); };

  const selected = new Mesh(geo, selectedMat); selected.renderOrder = 3; selected.visible = false; group.add(selected);
  const lf = new Mesh(geo, lastFrom); lf.renderOrder = 2; lf.visible = false; group.add(lf);
  const lt = new Mesh(geo, lastTo); lt.renderOrder = 2; lt.visible = false; group.add(lt);

  const place = (m: Mesh, sq: Square, y: number, scale: number) => {
    const p = squareToWorld(sq);
    m.position.set(p.x, y, p.z);
    m.scale.setScalar(scale);
  };

  return {
    show(targets) {
      this.clear();
      const pal = blind ? palettes.blind : palettes.normal;
      for (const tg of targets) {
        const m = getMesh();
        m.material = tg.capture ? pal.capture : pal.move;
        place(m, tg.square, 0.012, tg.capture ? 0.95 : 0.62);
        active.push({ mesh: m, capture: tg.capture, phase: Math.random() * 6 });
      }
    },
    clear() {
      while (active.length) release(active.pop()!.mesh);
    },
    setSelected(sq) {
      selected.visible = !!sq;
      if (sq) place(selected, sq, 0.01, 1);
    },
    setLastMove(from, to) {
      lf.visible = !!from; lt.visible = !!to;
      if (from) place(lf, from, 0.008, 1);
      if (to) place(lt, to, 0.009, 1);
    },
    setColorBlind(on) {
      blind = on;
      const pal = on ? palettes.blind : palettes.normal;
      for (const a of active) a.mesh.material = a.capture ? pal.capture : pal.move;
    },
    update(time) {
      for (const a of active) {
        const s = Math.sin(time * 3 + a.phase);
        const base = a.capture ? 0.95 : 0.62;
        a.mesh.scale.setScalar(base * (1 + s * 0.07));
        if (a.capture) a.mesh.rotation.y = time * 0.5;
      }
      selectedMat.opacity = 0.75 + Math.sin(time * 4) * 0.25;
    },
  };
}
