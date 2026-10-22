// Lighting rig: warm shadow-casting key from the Emberhold side (+z), cold rim from the Rime side (-z),
// IBL from a PMREM'd RoomEnvironment (lighting only; the background is the scene), plus fog and a
// gradient sky dome that is ember-warm behind White and ice-cold behind Black.
import {
  AdditiveBlending, BackSide, Color, CircleGeometry, CylinderGeometry, DirectionalLight, FogExp2, Group,
  HemisphereLight, Mesh, MeshStandardMaterial, Object3D, PMREMGenerator, PointLight, ShaderMaterial, SphereGeometry, SpotLight, Sprite, SpriteMaterial,
  Float32BufferAttribute, BufferGeometry, BufferAttribute, Points, RepeatWrapping, type Scene, type WebGLRenderer,
} from 'three';
import type { QualityTier } from '../contracts';
import { makeFloorTexture, makeGlowTexture } from './boardTextures';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';

export interface Lighting {
  key: DirectionalLight;
  rim: DirectionalLight;
  setShadowSize(px: number): void;
  setShadowsEnabled(on: boolean): void;
  /** 'off' disables the key light's shadow, 'low' = 1024 map, 'high' = 2048. */
  setShadows(level: 'off' | 'low' | 'high'): void;
  /** Ambient life: motes, braziers and fog density. */
  setAmbient(on: boolean): void;
  /** Brazier point lights are skipped on the Low tier (emissive flames remain). */
  setTier(tier: QualityTier): void;
  /** Flicker the braziers (real seconds). */
  update(time: number, camZ?: number): void;
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

export function createLighting(scene: Scene, renderer: WebGLRenderer): Lighting {
  // IBL
  const pmrem = new PMREMGenerator(renderer);
  const env = new RoomEnvironment();
  const envRT = pmrem.fromScene(env, 0.04);
  scene.environment = envRT.texture;
  scene.environmentIntensity = 0.28;
  env.dispose();
  pmrem.dispose();

  scene.background = new Color(0x05070b);
  scene.fog = new FogExp2(0x06080c, 0.022);

  const key = new DirectionalLight(0xffb878, 3.4);
  key.position.set(5.5, 7.5, 8.5);
  key.castShadow = true;
  key.shadow.mapSize.set(2048, 2048);
  key.shadow.camera.left = -9; key.shadow.camera.right = 9;
  key.shadow.camera.top = 9; key.shadow.camera.bottom = -9;
  key.shadow.camera.near = 2; key.shadow.camera.far = 34;
  key.shadow.bias = -0.0004;
  key.shadow.normalBias = 0.03;
  key.shadow.radius = 5;
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
  const warmC = new Color(0x5c4838), coldC = new Color(0x2a3a4c), c = new Color();
  for (let i = 0; i < pos.count; i++) {
    const t = Math.min(Math.max(pos.getZ(i) / 14 * 0.5 + 0.5, 0), 1);
    const rr = Math.hypot(pos.getX(i), pos.getZ(i));
    const fall = 1 - Math.min(Math.max((rr - 12) / 30, 0), 1);
    c.copy(coldC).lerp(warmC, t).multiplyScalar(0.25 + 0.75 * fall * fall);
    colors.push(c.r, c.g, c.b);
  }
  floorGeo.setAttribute('color', new Float32BufferAttribute(colors, 3));
  const floorTex = makeFloorTexture(1024);
  floorTex.wrapS = floorTex.wrapT = RepeatWrapping;
  floorTex.repeat.set(10, 10);
  const floor = new Mesh(floorGeo, new MeshStandardMaterial({ map: floorTex, vertexColors: true, roughness: 0.78, metalness: 0.08 }));
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
    col.position.set(Math.sin(a) * 25, 15.5, Math.cos(a) * 25);
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
    for (const [w, h, y, ph, op] of [[0.9, 1.7, 2.35, 0, 0.8], [1.7, 2.4, 2.45, 1.7, 0.16]] as const) {
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
  // ---- faint back-lights behind each side (cold behind the Rime ranks, warm behind Emberhold) and drifting motes
  const haze = makeGlowTexture(128);
  // Only the glows on the far side of the board (from the camera) are shown, so they never haze the near ranks.
  const hazeSide: { cold: Array<{ m: SpriteMaterial; op: number }>; warm: Array<{ m: SpriteMaterial; op: number }> } = { cold: [], warm: [] };
  for (const [x, y, z, w, h, col, op] of [
    [-5.5, 0.5, -9, 6.5, 3.4, 0x4f8fd0, 0.12], [5.5, 0.5, -9, 6.5, 3.4, 0x4f8fd0, 0.12], [0, 1.0, -11, 10, 4, 0x6aa8e8, 0.08],
    [-5.5, 0.5, 9, 6.5, 3.4, 0xe0782a, 0.14], [5.5, 0.5, 9, 6.5, 3.4, 0xe0782a, 0.14], [0, 1.0, 11, 10, 4, 0xf0903a, 0.1],
  ] as const) {
    const m = new SpriteMaterial({ map: haze, color: col, transparent: true, opacity: 0, blending: AdditiveBlending, depthWrite: false, fog: false });
    const sp = new Sprite(m);
    sp.position.set(x, y, z);
    sp.scale.set(w, h, 1);
    hall.add(sp);
    (z < 0 ? hazeSide.cold : hazeSide.warm).push({ m, op });
  }
  const MOTES = 260;
  const moteGeo = new BufferGeometry();
  {
    const p = new Float32Array(MOTES * 3), a = new Float32Array(MOTES * 4), col = new Float32Array(MOTES * 3);
    let seed = 1337;
    const rnd = () => { seed = (seed * 1664525 + 1013904223) >>> 0; return seed / 4294967296; };
    for (let i = 0; i < MOTES; i++) {
      p[i * 3] = (rnd() - 0.5) * 18; p[i * 3 + 1] = rnd() * 6; p[i * 3 + 2] = (rnd() - 0.5) * 18;
      a[i * 4] = 0.15 + rnd() * 0.3;       // rise speed
      a[i * 4 + 1] = rnd() * 6.28;         // phase
      a[i * 4 + 2] = 0.05 + rnd() * 0.07;  // size
      a[i * 4 + 3] = 0.4 + rnd() * 0.6;    // brightness
      const warm = p[i * 3 + 2] > 0;
      col[i * 3] = warm ? 1.0 : 0.55; col[i * 3 + 1] = warm ? 0.55 : 0.8; col[i * 3 + 2] = warm ? 0.22 : 1.0;
    }
    moteGeo.setAttribute('position', new BufferAttribute(p, 3));
    moteGeo.setAttribute('aData', new BufferAttribute(a, 4));
    moteGeo.setAttribute('aColor', new BufferAttribute(col, 3));
  }
  const moteMat = new ShaderMaterial({
    uniforms: { uTime: { value: 0 } },
    vertexShader: /* glsl */ `
      uniform float uTime; attribute vec4 aData; attribute vec3 aColor;
      varying vec3 vCol; varying float vA;
      void main() {
        vec3 p = position;
        p.y = mod(p.y + uTime * aData.x, 6.0) - 0.8;
        p.x += sin(uTime * 0.35 + aData.y) * 0.45;
        p.z += cos(uTime * 0.29 + aData.y * 1.3) * 0.45;
        vec4 mv = modelViewMatrix * vec4(p, 1.0);
        gl_Position = projectionMatrix * mv;
        gl_PointSize = aData.z * 900.0 / -mv.z;
        vA = aData.w * smoothstep(-0.8, 0.4, p.y) * smoothstep(5.2, 3.2, p.y) * (0.65 + 0.35 * sin(uTime * 1.7 + aData.y * 3.0));
        vCol = aColor;
      }`,
    fragmentShader: /* glsl */ `
      varying vec3 vCol; varying float vA;
      void main() {
        float d = length(gl_PointCoord - 0.5) * 2.0;
        float a = smoothstep(1.0, 0.0, d) * vA * 0.7;
        gl_FragColor = vec4(vCol, a);
        #include <colorspace_fragment>
      }`,
    transparent: true, depthWrite: false, blending: AdditiveBlending, fog: false,
  });
  const motes = new Points(moteGeo, moteMat);
  motes.frustumCulled = false;
  motes.renderOrder = 5;
  scene.add(motes);
  let lightsOn = true;
  let ambientOn = true;
  let tierMotes = true;

  const api: Lighting = {
    key, rim,
    setTier(tier) {
      tierMotes = tier !== 'low';
      moteGeo.setDrawRange(0, tier === 'high' ? MOTES : 150);
      lightsOn = tier !== 'low';
      api.setAmbient(ambientOn);
    },
    update(time, camZ = 10) {
      moteMat.uniforms.uTime.value = time;
      const far = (sign: number) => Math.min(Math.max(sign * camZ / 6, 0), 1);
      for (const h of hazeSide.cold) h.m.opacity = h.op * far(1);
      for (const h of hazeSide.warm) h.m.opacity = h.op * far(-1);
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
    setShadows(level) {
      key.castShadow = level !== 'off';
      if (level !== 'off') api.setShadowSize(level === 'high' ? 2048 : 1024);
    },
    setAmbient(on) {
      ambientOn = on;
      hall.visible = on;
      motes.visible = on && tierMotes;
      for (const l of lights) l.visible = on && lightsOn;
      (scene.fog as FogExp2).density = on ? 0.022 : 0.009;
    },
    dispose() { envRT.dispose(); },
  };
  return api;
}
