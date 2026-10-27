// Lighting rig: a warm shadow-casting key from the Emberhold side (+z), a cool rim from the Rime side (-z), a soft frontal fill, a
// hemisphere fill and a themed PMREM environment (warm firelight one side, cold moonlight the other, bright overhead strip) so
// stone and metal actually shine. No point lights: braziers glow through emissive + additive billboards (see hall.ts), so the
// light count is constant and the same look holds on Low.
//
// Shadows: one directional map. It is not re-rendered every frame (shadowMap.autoUpdate = false): `tick()` refreshes it at a few
// Hz when the board is idle and every frame (or every other frame) while something moves.
import {
  BoxGeometry, Color, DirectionalLight, FogExp2, Group, HemisphereLight, Mesh, MeshBasicMaterial, Object3D, PMREMGenerator,
  Scene as ThreeScene, ShaderMaterial, SphereGeometry, SpotLight, BackSide,
  type Scene, type WebGLRenderer,
} from 'three';
import type { QualityTier } from '../contracts';
import { createHall, type Hall } from './hall';

export interface Lighting {
  key: DirectionalLight;
  rim: DirectionalLight;
  readonly hall: Hall;
  setShadowSize(px: number): void;
  setShadowsEnabled(on: boolean): void;
  /** 'off' disables the key light's shadow, 'low' = 1024 map, 'high' = 2048. */
  setShadows(level: 'off' | 'low' | 'high'): void;
  /** Ambient life: motes and flame flicker. The hall dressing itself is always shown. */
  setAmbient(on: boolean): void;
  setTier(tier: QualityTier): void;
  /** Flicker the braziers (real seconds). */
  update(time: number, camZ?: number): void;
  /** Call every frame: refreshes the shadow map when due. `busy` = something is moving (cinematic, drag...). */
  tick(dt: number, busy: boolean): void;
  /** Force a shadow refresh on the next tick (piece teleported, settings changed...). */
  invalidateShadows(): void;
  dispose(): void;
}

/**
 * Pre-warm shader programs for the cinematic light rig. Three.js keys programs on the light counts, so the first capture
 * (which adds 3 SpotLights, no shadows) would compile every material mid-fight. Temporarily add 3 dormant spotlights with
 * the same settings as src/cinematics/lightRig.ts, render one frame through the real pipeline, then remove them.
 */
export function prewarmCinematicLights(scene: Scene, renderFrame: () => void): void {
  const group = new Group();
  const aim = new Object3D();
  group.add(aim);
  for (const [color, angle, penumbra] of [[0xffb26b, 0.5, 0.85], [0xfff2e4, 1.0, 1], [0xa5dcff, 0.7, 0.9]] as const) {
    const l = new SpotLight(color, 0, 0, angle, penumbra, 0);
    l.castShadow = false;
    l.target = aim;
    group.add(l);
  }
  scene.add(group);
  try { renderFrame(); } finally {
    scene.remove(group);
    group.children.forEach((c) => (c as SpotLight).dispose?.());
  }
}

/** A themed light-probe scene: dusk gradient + emissive panels. Baked once into a PMREM cube (a few ms). */
function buildEnvironment(): ThreeScene {
  const env = new ThreeScene();
  const sky = new Mesh(
    new SphereGeometry(40, 24, 12),
    new ShaderMaterial({
      side: BackSide,
      vertexShader: 'varying vec3 d; void main(){ d = normalize(position); gl_Position = projectionMatrix * modelViewMatrix * vec4(position,1.0); }',
      fragmentShader: `varying vec3 d; void main(){
        float h = d.y * 0.5 + 0.5;
        vec3 c = mix(vec3(0.16,0.14,0.13), vec3(0.20,0.24,0.34), smoothstep(0.35,0.95,h));
        c = mix(vec3(0.10,0.085,0.08), c, smoothstep(0.1,0.5,h));
        c += vec3(0.55,0.26,0.10) * smoothstep(0.0,1.0,d.z) * smoothstep(0.8,0.4,h);
        c += vec3(0.10,0.22,0.42) * smoothstep(0.0,1.0,-d.z) * smoothstep(0.8,0.4,h);
        gl_FragColor = vec4(c,1.0); }`,
    }),
  );
  env.add(sky);
  const panel = (w: number, h: number, d: number, color: Color, x: number, y: number, z: number) => {
    const m = new Mesh(new BoxGeometry(w, h, d), new MeshBasicMaterial({ color }));
    m.position.set(x, y, z);
    env.add(m);
  };
  panel(16, 8, 0.5, new Color(7.5, 3.8, 1.5), 0, 9, 28);        // firelight, behind White
  panel(10, 5, 0.5, new Color(6.0, 3.0, 1.2), -18, 4, 14);
  panel(10, 5, 0.5, new Color(6.0, 3.0, 1.2), 18, 4, 14);
  panel(16, 8, 0.5, new Color(1.6, 3.4, 8.0), 0, 9, -28);       // moonlight / frost, behind Black
  panel(10, 5, 0.5, new Color(1.4, 2.8, 6.5), -18, 4, -14);
  panel(10, 5, 0.5, new Color(1.4, 2.8, 6.5), 18, 4, -14);
  panel(22, 0.5, 8, new Color(3.4, 3.3, 3.2), 0, 22, 0);        // overhead strip: gives metal a bright top highlight
  return env;
}

export function createLighting(scene: Scene, renderer: WebGLRenderer, opts: { weak?: boolean } = {}): Lighting {
  // ---- IBL
  const pmrem = new PMREMGenerator(renderer);
  const envScene = buildEnvironment();
  const envRT = pmrem.fromScene(envScene, 0.035, 0.1, 100, { size: 128 });
  scene.environment = envRT.texture;
  scene.environmentIntensity = 0.8;
  envScene.traverse((o) => { const m = o as Mesh; if (m.isMesh) { m.geometry.dispose(); (m.material as MeshBasicMaterial).dispose(); } });
  pmrem.dispose();

  scene.background = new Color(0x26283a);
  scene.fog = new FogExp2(0x2a2f44, 0.0105);

  // ---- direct lights (count never changes)
  const key = new DirectionalLight(0xffc48a, 2.7);
  key.position.set(5.5, 8.5, 8.5);
  key.castShadow = true;
  key.shadow.mapSize.set(1024, 1024);
  key.shadow.camera.left = -7.8; key.shadow.camera.right = 7.8;
  key.shadow.camera.top = 7.2; key.shadow.camera.bottom = -7.2;
  key.shadow.camera.near = 3; key.shadow.camera.far = 26;
  key.shadow.bias = -0.0005;
  key.shadow.normalBias = 0.035;
  scene.add(key, key.target);

  const rim = new DirectionalLight(0x86b4ff, 2.1);
  rim.position.set(-4.5, 4.2, -10);
  scene.add(rim, rim.target);

  const fill = new DirectionalLight(0xffe7cf, 0.5);
  fill.position.set(-3, 3.2, 9);
  scene.add(fill, fill.target);

  scene.add(new HemisphereLight(0xa4b4d4, 0x5e4a38, 0.7));

  const hall = createHall(scene, { weak: !!opts.weak });

  // ---- shadow scheduling
  renderer.shadowMap.autoUpdate = false;
  let shadowsOn = true;
  renderer.shadowMap.needsUpdate = true; // the very first render must create the map (autoUpdate is off)
  let shadowAcc = 0, shadowDirty = true, shadowHz = 10, shadowBusyHz = 30;
  const refresh = () => { renderer.shadowMap.needsUpdate = true; shadowAcc = 0; shadowDirty = false; };

  const api: Lighting = {
    key, rim, hall,
    setTier(tier) {
      hall.setTier(tier);
      shadowHz = tier === 'high' ? 15 : 10;
      shadowBusyHz = tier === 'high' ? 60 : tier === 'medium' ? 30 : 20;
      shadowDirty = true;
    },
    update(time) { hall.update(time); },
    tick(dt, busy) {
      if (!shadowsOn) return;
      shadowAcc += dt;
      if (shadowDirty || shadowAcc >= 1 / (busy ? shadowBusyHz : shadowHz) - 0.002) refresh();
    },
    invalidateShadows() { shadowDirty = true; renderer.shadowMap.needsUpdate = true; },
    setShadowSize(px) {
      if (key.shadow.mapSize.x === px) return;
      key.shadow.mapSize.set(px, px);
      key.shadow.map?.dispose();
      key.shadow.map = null;
      shadowDirty = true;
      renderer.shadowMap.needsUpdate = true;
    },
    setShadowsEnabled(on) { shadowsOn = on; key.castShadow = on; shadowDirty = true; renderer.shadowMap.needsUpdate = true; },
    setShadows(level) {
      shadowsOn = level !== 'off';
      key.castShadow = shadowsOn;
      if (shadowsOn) api.setShadowSize(level === 'high' ? 2048 : 1024);
      shadowDirty = true;
      renderer.shadowMap.needsUpdate = true;
    },
    setAmbient(on) {
      hall.setAmbient(on);
      (scene.fog as FogExp2).density = on ? 0.0105 : 0.008;
    },
    dispose() { envRT.dispose(); },
  };
  return api;
}
