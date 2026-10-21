import { BoxGeometry, Mesh, MeshStandardMaterial, Object3D, Scene, Vector3 } from 'three';
import type { BoardApi, Faction, PieceActor, Role, Square } from '../../src/contracts';
import { squareToWorld } from '../../src/contracts';
import type { SandboxActor, SandboxRegistry } from './actor';

export class SandboxBoard implements BoardApi {
  readonly scene = new Scene();
  private map = new Map<Square, SandboxActor>();
  private tiles = new Map<Square, Mesh>();
  tintLog: Array<[Square, number | null]> = [];
  constructor(private registry: SandboxRegistry) {
    const dark = new MeshStandardMaterial({ color: 0x3a3430, roughness: 0.8 });
    const light = new MeshStandardMaterial({ color: 0xb9a98c, roughness: 0.8 });
    const g = new BoxGeometry(1, 0.3, 1);
    for (let f = 0; f < 8; f++) for (let r = 0; r < 8; r++) {
      const sq = 'abcdefgh'[f] + (r + 1);
      const m = new Mesh(g, ((f + r) % 2 ? light : dark).clone());
      squareToWorld(sq, m.position); m.position.y = -0.15; m.receiveShadow = true;
      this.scene.add(m); this.tiles.set(sq, m);
    }
    const frame = new Mesh(new BoxGeometry(9.2, 0.4, 9.2), new MeshStandardMaterial({ color: 0x1a1512 }));
    frame.position.y = -0.36; this.scene.add(frame);
  }
  clear() {
    for (const a of this.map.values()) { this.scene.remove(a.root); a.dispose(); }
    this.map.clear();
    for (const t of this.tiles.values()) ((t.material as MeshStandardMaterial).emissive.set(0));
  }
  add(faction: Faction, role: Role, sq: Square) { return this.spawnActor(faction, role, sq); }
  actorAt(sq: Square) { return this.map.get(sq); }
  allActors() { return [...this.map.values()]; }
  setActorSquare(a: PieceActor, sq: Square) {
    for (const [k, v] of this.map) if (v === a) this.map.delete(k);
    a.square = sq; this.map.set(sq, a as SandboxActor);
  }
  removeActor(a: PieceActor) {
    if (this.map.get(a.square) === a) this.map.delete(a.square);
    for (const [k, v] of this.map) if (v === a) this.map.delete(k);
    this.scene.remove(a.root);
  }
  spawnActor(faction: Faction, role: Role, sq: Square) {
    const a = this.registry.createActor(faction, role, sq) as SandboxActor;
    this.map.set(sq, a); this.scene.add(a.root);
    return a;
  }
  squareCenter(sq: Square, target: Vector3) { return squareToWorld(sq, target); }
  tintSquare(sq: Square, color: number | null) {
    this.tintLog.push([sq, color]);
    const m = this.tiles.get(sq)?.material as MeshStandardMaterial | undefined;
    if (m) m.emissive.set(color ?? 0);
  }
  syncToFen() {}
  update(dt: number) { for (const a of this.map.values()) a.update(dt); }
}
export type { Object3D };
