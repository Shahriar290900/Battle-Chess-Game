// Lighting rig: warm shadow-casting key from the Emberhold side (+z), cold rim from the Rime side (-z),
// IBL from a PMREM'd RoomEnvironment (lighting only; the background is the scene), plus fog and a
// gradient sky dome that is ember-warm behind White and ice-cold behind Black.
import {
  AdditiveBlending, BackSide, Color, CircleGeometry, CylinderGeometry, DirectionalLight, FogExp2, Group,
  HemisphereLight, Mesh, MeshStandardMaterial, PMREMGenerator, PointLight, ShaderMaterial, SphereGeometry, Sprite, SpriteMaterial,
  Float32BufferAttribute, type Scene, type WebGLRenderer,
} from 'three';
import type { QualityTier } from '../contracts';
import { makeGlowTexture } from './boardTextures';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';

export interface Lighting {
  key: DirectionalLight;
  rim: DirectionalLight;
  setShadowSize(px: number): void;
  setShadowsEnabled(on: boolean): void;
  /** Brazier point lights are skipped on the Low tier (emissive flames remain). */
  setTier(tier: QualityTier): void;
  /** Flicker the braziers (real seconds). */
  update(time: number): void;
  dispose(): void;
}

const SKY_VERT = /* glsl */ `
  varying vec3 vDir;
  void main() {
    vDir = normalize(position);
    vec4 p = modelViewMatrix * vec4(position, 1.0);
    gl_Position = projectionMatrix * p;
  }`;
const SKY_FRAG = /* glsl */ `
  varying vec3 vDir;
  void main() {
    float h = clamp(vDir.y * 0.5 + 0.5, 0.0, 1.0);
    vec3 zenith = vec3(0.012, 0.016, 0.026);
    vec3 horizon = vec3(0.045, 0.055, 0.08);
    vec3 col = mix(horizon, zenith, smoothstep(0.45, 0.95, h));
    // Emberhold glow behind White (+z), frost glow behind Black (-z).
    float warm = smoothstep(0.1, 1.0, vDir.z) * smoothstep(0.62, 0.38, h);
    float cold = smoothstep(0.1, 1.0, -vDir.z) * smoothstep(0.65, 0.4, h);
    col += vec3(0.20, 0.075, 0.02) * warm;
    col += vec3(0.04, 0.09, 0.15) * cold;
    gl_FragColor = vec4(col, 1.0);
    #include <tonemapping_fragment>
    #include <colorspace_fragment>
  }`;

export function createLighting(scene: Scene, renderer: WebGLRenderer): Lighting {
  // IBL
  const pmrem = new PMREMGenerator(renderer);
  const env = new RoomEnvironment();
  const envRT = pmrem.fromScene(env, 0.04);
  scene.environment = envRT.texture;
  scene.environmentIntensity = 0.16;
  env.dispose();
  pmrem.dispose();

  scene.background = new Color(0x05070b);
  scene.fog = new FogExp2(0x06080c, 0.022);

  const key = new DirectionalLight(0xffb878, 3.4);
  key.position.set(3.5, 11, 9);
  key.castShadow = true;
  key.shadow.mapSize.set(2048, 2048);
  key.shadow.camera.left = -7; key.shadow.camera.right = 7;
  key.shadow.camera.top = 7; key.shadow.camera.bottom = -7;
  key.shadow.camera.near = 2; key.shadow.camera.far = 30;
  key.shadow.bias = -0.0004;
  key.shadow.normalBias = 0.03;
  key.shadow.radius = 3;
  scene.add(key, key.target);

  const rim = new DirectionalLight(0x6aa8ff, 1.9);
  rim.position.set(-4, 3.2, -10);
  scene.add(rim, rim.target);

  scene.add(new HemisphereLight(0x2c3a56, 0x140d09, 0.22));

  // Sky dome
  const sky = new Mesh(
    new SphereGeometry(90, 32, 16),
    new ShaderMaterial({ vertexShader: SKY_VERT, fragmentShader: SKY_FRAG, side: BackSide, depthWrite: false, fog: false }),
  );
  sky.renderOrder = -10;
  sky.frustumCulled = false;
  scene.add(sky);

  // Floor: dark stone fading into fog, warm toward White, cold toward Black.
  const floorGeo = new CircleGeometry(70, 72, 0, Math.PI * 2);
  floorGeo.rotateX(-Math.PI / 2);
  const pos = floorGeo.getAttribute('position');
  const colors: number[] = [];
  const warmC = new Color(0x120b07), coldC = new Color(0x080d14), c = new Color();
  for (let i = 0; i < pos.count; i++) {
    const t = Math.min(Math.max(pos.getZ(i) / 14 * 0.5 + 0.5, 0), 1);
    c.copy(coldC).lerp(warmC, t);
    colors.push(c.r, c.g, c.b);
  }
  floorGeo.setAttribute('color', new Float32BufferAttribute(colors, 3));
  const floor = new Mesh(floorGeo, new MeshStandardMaterial({ vertexColors: true, roughness: 0.92, metalness: 0.05 }));
  floor.position.y = -1.25;
  floor.receiveShadow = true;
  floor.name = 'floor';
  scene.add(floor);

  // ---- hall dressing: a ring of dark columns lost in the fog, and four braziers around the dais
  const hall = new Group();
  hall.name = 'hall';
  const stone = new MeshStandardMaterial({ color: 0x14110f, roughness: 0.85, metalness: 0.1 });
  const colGeo = new CylinderGeometry(1.1, 1.3, 34, 14);
  for (let i = 0; i < 12; i++) {
    const a = (i / 12) * Math.PI * 2 + 0.26;
    const col = new Mesh(colGeo, stone);
    col.position.set(Math.sin(a) * 21, 15.5, Math.cos(a) * 21);
    hall.add(col);
  }
  const flames: Array<{ m: Sprite; base: number; phase: number; w: number }> = [];
  const glow = makeGlowTexture(128);
  const lights: PointLight[] = [];
  const bronze = new MeshStandardMaterial({ color: 0x3a2a1c, roughness: 0.5, metalness: 0.8 });
  const silver = new MeshStandardMaterial({ color: 0x2a3948, roughness: 0.35, metalness: 0.8 });
  const brazier = (x: number, z: number, warm: boolean) => {
    const g = new Group();
    g.position.set(x, -0.95, z);
    const post = new Mesh(new CylinderGeometry(0.16, 0.3, 1.5, 10), warm ? bronze : silver);
    post.position.y = 0.75;
    const bowl = new Mesh(new CylinderGeometry(0.55, 0.28, 0.35, 12), warm ? bronze : silver);
    bowl.position.y = 1.6;
    post.castShadow = true; bowl.castShadow = true;
    g.add(post, bowl);
    const col = warm ? new Color(1.0, 0.42, 0.1) : new Color(0.25, 0.7, 1.0);
    for (const [w, h, y, ph, op] of [[1.1, 2.0, 2.35, 0, 0.85], [2.6, 3.4, 2.5, 1.7, 0.28]] as const) {
      const mat = new SpriteMaterial({ map: glow, color: col, transparent: true, opacity: op, blending: AdditiveBlending, depthWrite: false, fog: false });
      const f = new Sprite(mat);
      f.scale.set(w, h, 1);
      f.position.y = y;
      flames.push({ m: f, base: h, phase: ph + x, w });
      g.add(f);
    }
    const pl = new PointLight(warm ? 0xff8a30 : 0x6fd0ff, warm ? 16 : 12, 15, 2);
    pl.position.y = 2.3;
    g.add(pl);
    lights.push(pl);
    hall.add(g);
  };
  brazier(-9.2, 3.4, true); brazier(9.2, 3.4, true);
  brazier(-9.2, -3.6, false); brazier(9.2, -3.6, false);
  scene.add(hall);
  let lightsOn = true;

  return {
    key, rim,
    setTier(tier) {
      lightsOn = tier !== 'low';
      for (const l of lights) l.visible = lightsOn;
    },
    update(time) {
      for (const f of flames) {
        const k = 1 + Math.sin(time * 9 + f.phase) * 0.12 + Math.sin(time * 17.3 + f.phase * 2) * 0.07;
        f.m.scale.set(f.w * (1 + (k - 1) * 0.4), f.base * k, 1);
      }
      if (lightsOn) lights.forEach((l, i) => { l.intensity = (i < 2 ? 16 : 12) * (0.9 + Math.sin(time * 8 + i * 2.1) * 0.08 + Math.sin(time * 19 + i) * 0.04); });
    },
    setShadowSize(px) {
      if (key.shadow.mapSize.x === px) return;
      key.shadow.mapSize.set(px, px);
      key.shadow.map?.dispose();
      key.shadow.map = null;
    },
    setShadowsEnabled(on) { key.castShadow = on; },
    dispose() { envRT.dispose(); },
  };
}
