// Captured pieces kneel on two stone ledges beside the board (or at its ends in portrait), as in a classic chess set.
// Each piece is a static actor (LOD1, GRAVEYARD_PIECE_SCALE) frozen at the end of its Surrender clip: no mixer, no collider,
// no kinematics. The list is derived from the FEN (piece counts, promotions handled), so undo/new game need nothing special.
import { gsap } from 'gsap';
import {
  BoxGeometry, Color, Float32BufferAttribute, Group, InstancedMesh, Mesh, MeshBasicMaterial, MeshStandardMaterial, PlaneGeometry,
  type BufferGeometry,
} from 'three';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';
import type { EventBus, Faction, Role, Side } from '../contracts';
import { SIDE_FACTION } from '../contracts';
import { parsePlacement } from '../core/rules';
import type { AssetRegistryImpl } from '../assets/registry';
import type { PieceActorImpl } from '../assets/pieceActor';
import { makeContactShadowTexture } from './boardTextures';

export interface CapturedPiece { faction: Faction; role: Role }

export interface Graveyard {
  readonly group: Group;
  sync(captured: CapturedPiece[]): void;
  setLayout(layout: 'sides' | 'ends'): void;
  setVisible(on: boolean): void;
  /** Every piece currently displayed (tests / debugging). */
  readonly count: number;
}

const INITIAL: Record<Role, number> = { pawn: 8, knight: 2, bishop: 2, rook: 2, queen: 1, king: 1 };
const VALUE: Record<Role, number> = { queen: 9, rook: 5, bishop: 3.2, knight: 3, pawn: 1, king: 0 };

/** Captured pieces implied by a position: missing non-pawns, and missing pawns that were not promoted. */
export function capturedFromFen(fen: string): CapturedPiece[] {
  const present: Record<Side, Record<Role, number>> = {
    w: { pawn: 0, knight: 0, bishop: 0, rook: 0, queen: 0, king: 0 },
    b: { pawn: 0, knight: 0, bishop: 0, rook: 0, queen: 0, king: 0 },
  };
  for (const v of parsePlacement(fen).values()) present[v.side][v.role]++;
  const out: CapturedPiece[] = [];
  for (const side of ['w', 'b'] as Side[]) {
    const p = present[side];
    let promoted = 0;
    for (const r of ['knight', 'bishop', 'rook', 'queen'] as Role[]) {
      const missing = INITIAL[r] - p[r];
      if (missing > 0) for (let i = 0; i < missing; i++) out.push({ faction: SIDE_FACTION[side], role: r });
      else promoted += -missing;
    }
    const pawns = Math.max(0, INITIAL.pawn - p.pawn - promoted);
    for (let i = 0; i < pawns; i++) out.push({ faction: SIDE_FACTION[side], role: 'pawn' });
  }
  return out;
}

const LEDGE_LEN = 7.2;
const LEDGE_W = 1.05;
const ROWS = 8;
const PITCH = LEDGE_LEN / ROWS;
const SLOTS = ROWS * 2;
const TOP_Y = 0; // ledge top surface (same height as the board top)

interface Ledge {
  faction: Faction; // faction of the pieces displayed here
  group: Group;
  items: Array<{ piece: CapturedPiece; actor: PieceActorImpl }>;
}

/** Carved dark stone ledge with an inset darker panel and a metal trim: bronze for Emberhold, frost-silver for the Rime Host. */
function ledgeGeometry(trim: number): BufferGeometry {
  const slab = new BoxGeometry(LEDGE_W, 0.42, LEDGE_LEN).translate(0, TOP_Y - 0.21, 0);
  const panel = new BoxGeometry(LEDGE_W - 0.34, 0.03, LEDGE_LEN - 0.5).translate(0, TOP_Y + 0.004, 0);
  const trimIn = new BoxGeometry(0.06, 0.07, LEDGE_LEN - 0.08).translate(-LEDGE_W / 2 + 0.06, TOP_Y + 0.02, 0);
  const trimOut = new BoxGeometry(0.06, 0.07, LEDGE_LEN - 0.08).translate(LEDGE_W / 2 - 0.06, TOP_Y + 0.02, 0);
  const cap = new BoxGeometry(LEDGE_W + 0.12, 0.1, 0.16);
  const capA = cap.clone().translate(0, TOP_Y + 0.0, LEDGE_LEN / 2 - 0.04);
  const capB = cap.translate(0, TOP_Y + 0.0, -LEDGE_LEN / 2 + 0.04);
  const foot = new BoxGeometry(LEDGE_W + 0.2, 0.1, LEDGE_LEN + 0.2).translate(0, TOP_Y - 0.4, 0);
  const parts = [slab, panel, trimIn, trimOut, capA, capB, foot];
  const colors = [new Color(0x3a322b), new Color(0x1f1a16), new Color(trim), new Color(trim), new Color(0x2a241f), new Color(0x2a241f), new Color(0x241f1a)];
  parts.forEach((g, i) => {
    const n = g.getAttribute('position').count;
    const arr = new Float32Array(n * 3);
    for (let k = 0; k < n; k++) { arr[k * 3] = colors[i].r; arr[k * 3 + 1] = colors[i].g; arr[k * 3 + 2] = colors[i].b; }
    g.setAttribute('color', new Float32BufferAttribute(arr, 3));
  });
  return mergeGeometries(parts, false)!;
}

export function createGraveyard(d: { root: Group; registry: AssetRegistryImpl; bus?: EventBus }): Graveyard {
  const group = new Group();
  group.name = 'graveyard';
  d.root.add(group);
  const mat = new MeshStandardMaterial({ vertexColors: true, roughness: 0.7, metalness: 0.2 });
  const blobTex = makeContactShadowTexture(64);
  const blobs = new InstancedMesh(
    new PlaneGeometry(1, 1).rotateX(-Math.PI / 2),
    new MeshBasicMaterial({ map: blobTex, transparent: true, depthWrite: false, fog: false, polygonOffset: true, polygonOffsetFactor: -3, polygonOffsetUnits: -3 }),
    SLOTS * 2,
  );
  blobs.frustumCulled = false; blobs.renderOrder = 3; blobs.count = 0;
  blobs.raycast = () => undefined;
  group.add(blobs);

  // Rime pieces (captured by White) on the left ledge, Emberhold pieces (captured by Black) on the right.
  const ledges: Ledge[] = (['rime', 'emberhold'] as Faction[]).map((faction) => {
    const g = new Group();
    const m = new Mesh(ledgeGeometry(faction === 'rime' ? 0xb08a4a : 0x9cc8e0), mat); // left ledge belongs to White (bronze), right to Black (frost)
    m.receiveShadow = true; m.castShadow = true;
    m.raycast = () => undefined;
    g.add(m);
    group.add(g);
    return { faction, group: g, items: [] };
  });
  let layout: 'sides' | 'ends' = 'sides';

  const place = () => {
    // Local +X of each ledge group points at the board, so a piece with yaw +PI/2 kneels facing it.
    const cfg = layout === 'sides'
      ? [{ x: -6.2, z: 0, rot: 0 }, { x: 6.2, z: 0, rot: Math.PI }]
      : [{ x: 0, z: 6.25, rot: Math.PI / 2 }, { x: 0, z: -6.25, rot: -Math.PI / 2 }];
    ledges.forEach((l, i) => {
      l.group.position.set(cfg[i].x, 0, cfg[i].z);
      l.group.rotation.y = cfg[i].rot;
    });
  };

  const slotPos = (i: number, out: { x: number; z: number }) => {
    const row = Math.floor(i / 2), col = i % 2;
    out.x = col ? 0.25 : -0.25;
    out.z = (row - (ROWS - 1) / 2) * PITCH;
  };
  const tmp = { x: 0, z: 0 };
  const blobArr = blobs.instanceMatrix.array as Float32Array;

  const layoutItems = (l: Ledge) => {
    l.items.forEach((it, i) => {
      slotPos(i, tmp);
      it.actor.root.position.set(tmp.x, TOP_Y, tmp.z);
      it.actor.root.rotation.y = Math.PI / 2 + (i % 2 ? -0.12 : 0.12);
    });
  };
  const refreshBlobs = () => {
    let n = 0;
    for (const l of ledges) {
      l.group.updateMatrixWorld(true);
      for (let i = 0; i < l.items.length && n < SLOTS * 2; i++) {
        const p = l.items[i].actor.root;
        // world position of the slot (ledges only rotate about Y)
        const wx = l.group.position.x + (p.position.x * Math.cos(l.group.rotation.y) + p.position.z * Math.sin(l.group.rotation.y));
        const wz = l.group.position.z + (-p.position.x * Math.sin(l.group.rotation.y) + p.position.z * Math.cos(l.group.rotation.y));
        const s = 0.95, o = n * 16;
        blobArr.fill(0, o, o + 16);
        blobArr[o] = s; blobArr[o + 5] = s; blobArr[o + 10] = s; blobArr[o + 12] = wx; blobArr[o + 13] = TOP_Y + 0.008; blobArr[o + 14] = wz; blobArr[o + 15] = 1;
        n++;
      }
    }
    blobs.count = n;
    blobs.instanceMatrix.needsUpdate = true;
  };

  const sortItems = (l: Ledge) => l.items.sort((a, b) => VALUE[b.piece.role] - VALUE[a.piece.role]);
  const disposeItem = (it: Ledge['items'][number]) => { gsap.killTweensOf(it.actor.root.position); it.actor.dispose(); };
  const total = () => ledges.reduce((n, l) => n + l.items.length, 0);

  const api: Graveyard = {
    group,
    get count() { return total(); },
    setVisible(on) { group.visible = on; },
    setLayout(next) {
      if (next === layout) return;
      layout = next;
      place();
      refreshBlobs();
    },
    sync(captured) {
      const want = ledges.map((l) => captured.filter((c) => c.faction === l.faction).slice(0, SLOTS));
      const before = total();
      let added: Ledge['items'][number] | null = null;
      let addedCount = 0;
      ledges.forEach((l, li) => {
        // keep matching actors, drop the rest, create the missing ones
        const pool = l.items.slice();
        const next: Ledge['items'] = [];
        for (const c of want[li]) {
          const k = pool.findIndex((it) => it.piece.role === c.role);
          if (k >= 0) next.push(pool.splice(k, 1)[0]);
          else {
            const actor = d.registry.createGraveyardActor(c.faction, c.role);
            l.group.add(actor.root);
            const it = { piece: c, actor };
            next.push(it); added = it; addedCount++;
          }
        }
        pool.forEach((it) => { disposeItem(it); });
        l.items = next;
        sortItems(l);
        layoutItems(l);
      });
      refreshBlobs();
      // A single new piece after a capture fades in (the shatter has just finished); anything else appears instantly.
      const it = added as Ledge['items'][number] | null;
      if (it && addedCount === 1 && total() === before + 1) {
        const a = it.actor;
        const y = a.root.position.y;
        a.setFade(0);
        a.root.position.y = y + 0.5;
        const k = { v: 0 };
        gsap.to(k, { v: 1, duration: 0.7, ease: 'power2.out', onUpdate: () => a.setFade(k.v) });
        gsap.to(a.root.position, { y, duration: 0.7, ease: 'bounce.out' });
      }
    },
  };
  place();
  return api;
}
