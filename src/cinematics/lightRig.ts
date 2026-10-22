// Cinematic lighting rig for captures: faction-tinted key spotlight on the fight midpoint, a soft fill from the
// camera side and a rim light from behind the fighters. Added to the board scene, faded in/out, removed on settle.
import { Color, Group, Object3D, SpotLight, Vector3 } from 'three';
import type { Scene } from 'three';
import type { Faction } from '../contracts';

const KEY_TINT: Record<Faction, number> = { emberhold: 0xffb26b, rime: 0xa5dcff };
const KEY_I = 5.0; const FILL_I = 1.6; const RIM_I = 3.4;

export class LightRig {
  readonly group = new Group();
  readonly key: SpotLight; readonly fill: SpotLight; readonly rim: SpotLight;
  private readonly aim = new Object3D();
  private amount = 0;
  private readonly mid = new Vector3(); private readonly v = new Vector3(); private readonly toCam = new Vector3();

  constructor(private readonly scene: Scene, attacker: Faction, defender: Faction) {
    this.group.name = 'cinematic_light_rig';
    const mk = (color: number, angle: number, penumbra: number) => {
      const l = new SpotLight(color, 0, 0, angle, penumbra, 0); // decay 0: no distance falloff
      l.castShadow = false; l.target = this.aim; this.group.add(l);
      return l;
    };
    this.key = mk(KEY_TINT[attacker], 0.5, 0.85);
    this.fill = mk(0xfff2e4, 1.0, 1);
    this.rim = mk(KEY_TINT[defender], 0.7, 0.9);
    this.rim.color = new Color(KEY_TINT[defender]);
    this.group.add(this.aim);
    scene.add(this.group);
  }

  /** 0..1 master intensity. */
  setAmount(a: number): void {
    this.amount = Math.max(0, Math.min(1, a));
    this.key.intensity = KEY_I * this.amount; this.fill.intensity = FILL_I * this.amount; this.rim.intensity = RIM_I * this.amount;
  }
  get currentAmount(): number { return this.amount; }

  /** Re-aim at the live fight midpoint; `cam` is the current camera position. */
  update(a: Vector3, d: Vector3, cam: Vector3): void {
    this.mid.copy(a).lerp(d, 0.5); this.mid.y = 0.6;
    this.aim.position.copy(this.mid);
    this.toCam.set(cam.x - this.mid.x, 0, cam.z - this.mid.z);
    if (this.toCam.lengthSq() < 1e-6) this.toCam.set(0, 0, 1);
    this.toCam.normalize();
    // key: high, slightly to the camera side and off-axis so faces/fronts catch it
    this.key.position.copy(this.mid).addScaledVector(this.toCam, 2.5).add(this.v.set(-this.toCam.z * 2, 6.5, this.toCam.x * 2));
    // fill: from the camera side, a little above the lens
    this.fill.position.set(cam.x, cam.y + 1.5, cam.z);
    // rim: behind the fighters, low enough to edge the silhouettes
    this.rim.position.copy(this.mid).addScaledVector(this.toCam, -4).add(this.v.set(this.toCam.z * 1.5, 3.2, -this.toCam.x * 1.5));
  }

  dispose(): void {
    this.scene.remove(this.group);
    this.key.dispose?.(); this.fill.dispose?.(); this.rim.dispose?.();
  }
}
