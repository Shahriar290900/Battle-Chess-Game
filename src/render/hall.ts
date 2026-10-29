// The great hall around the dais, built to be nearly free: a painted arcade backdrop (one unlit cylinder), a flagstone floor,
// one merged mesh for every column / brazier, and ONE additive billboard batch for every flame and halo. No real point lights
// (the glow is emissive + baked), so the look is identical on every tier and the light count never changes.
import {
  AdditiveBlending, BackSide, BoxGeometry, BufferAttribute, BufferGeometry, CanvasTexture, CircleGeometry, Color, CylinderGeometry, DoubleSide, Float32BufferAttribute,
  Group, Mesh, MeshBasicMaterial, MeshStandardMaterial, Points, RepeatWrapping, ShaderMaterial, SphereGeometry, SRGBColorSpace, TorusGeometry,
  type Scene,
} from 'three';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';
import { makeFloorTexture, makeGlowTexture } from './boardTextures';

export interface Hall {
  readonly group: Group;
  /** Flicker / drift (seconds of real time). */
  update(time: number): void;
  /** Motes and flame flicker on/off. The static dressing stays visible on every tier. */
  setAmbient(on: boolean): void;
  /** High draws more motes. */
  setTier(tier: 'low' | 'medium' | 'high'): void;
}

const SKY_VERT = /* glsl */ `
  varying vec3 vDir;
  void main() {
    vDir = normalize(position);
    gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
  }`;
const SKY_FRAG = /* glsl */ `
  varying vec3 vDir;
  void main() {
    float h = clamp(vDir.y * 0.5 + 0.5, 0.0, 1.0);
    vec3 zenith = vec3(0.045, 0.06, 0.12);
    vec3 horizon = vec3(0.20, 0.19, 0.24);
    vec3 col = mix(horizon, zenith, smoothstep(0.5, 0.95, h));
    float warm = smoothstep(0.0, 1.0, vDir.z) * smoothstep(0.7, 0.45, h);
    float cold = smoothstep(0.0, 1.0, -vDir.z) * smoothstep(0.72, 0.45, h);
    col += vec3(0.42, 0.17, 0.05) * warm;
    col += vec3(0.07, 0.15, 0.27) * cold;
    gl_FragColor = vec4(col, 1.0);
    #include <tonemapping_fragment>
    #include <colorspace_fragment>
  }`;

/** Painted arcade wall: gothic windows glowing warm toward White (+z, u = 0) and cold toward Black (u = 0.5). */
function makeWallTexture(w: number, h: number): CanvasTexture {
  const c = document.createElement('canvas');
  c.width = w; c.height = h;
  const g = c.getContext('2d')!;
  const sky = g.createLinearGradient(0, h, 0, 0);
  sky.addColorStop(0, '#2b2a30'); sky.addColorStop(0.5, '#3a3a46'); sky.addColorStop(1, '#16182a');
  g.fillStyle = sky; g.fillRect(0, 0, w, h);
  // faint masonry
  g.strokeStyle = 'rgba(0,0,0,0.22)'; g.lineWidth = 2;
  for (let y = 0; y < h; y += h / 14) { g.beginPath(); g.moveTo(0, y); g.lineTo(w, y); g.stroke(); }
  const N = 16, cw = w / N;
  for (let i = 0; i < N; i++) {
    const cx = (i + 0.5) * cw;
    const u = (i + 0.5) / N; // 0 / 1 = warm side, 0.5 = cold side
    const warmth = Math.max(0, Math.cos(u * Math.PI * 2));
    const col = (a: number) => {
      const wr = 255 * warmth + 120 * (1 - warmth), wg = 150 * warmth + 175 * (1 - warmth), wb = 70 * warmth + 255 * (1 - warmth);
      return `rgba(${Math.round(wr)},${Math.round(wg)},${Math.round(wb)},${a})`;
    };
    const top = h * 0.14, bot = h * 0.88, half = cw * 0.27;
    // pier shadow
    g.fillStyle = 'rgba(8,8,14,0.55)'; g.fillRect(cx - cw * 0.5, 0, cw * 0.12, h);
    // arch window
    g.beginPath();
    g.moveTo(cx - half, bot);
    g.lineTo(cx - half, top + half);
    g.quadraticCurveTo(cx - half, top, cx, top - half * 0.5);
    g.quadraticCurveTo(cx + half, top, cx + half, top + half);
    g.lineTo(cx + half, bot);
    g.closePath();
    const wg = g.createLinearGradient(0, top, 0, bot);
    wg.addColorStop(0, col(0.95)); wg.addColorStop(0.55, col(0.62)); wg.addColorStop(1, col(0.25));
    g.fillStyle = wg; g.fill();
    g.strokeStyle = 'rgba(10,8,12,0.9)'; g.lineWidth = 6; g.stroke();
    // tracery
    g.lineWidth = 3; g.beginPath(); g.moveTo(cx, top - half * 0.4); g.lineTo(cx, bot); g.moveTo(cx - half, top + half * 1.6); g.lineTo(cx + half, top + half * 1.6); g.stroke();
    // glow spill
    const sp = g.createRadialGradient(cx, (top + bot) / 2, 0, cx, (top + bot) / 2, cw * 0.8);
    sp.addColorStop(0, col(0.26)); sp.addColorStop(1, col(0));
    g.fillStyle = sp; g.fillRect(cx - cw, 0, cw * 2, h);
  }
  // floor-level warm/cold wash so the wall meets the floor softly
  const wash = g.createLinearGradient(0, h, 0, h * 0.7);
  wash.addColorStop(0, 'rgba(10,10,16,0.85)'); wash.addColorStop(1, 'rgba(10,10,16,0)');
  g.fillStyle = wash; g.fillRect(0, h * 0.7, w, h * 0.3);
  const t = new CanvasTexture(c);
  t.colorSpace = SRGBColorSpace;
  t.wrapS = RepeatWrapping;
  t.anisotropy = 4;
  return t;
}

export function createHall(scene: Scene, opts: { weak: boolean }): Hall {
  const group = new Group();
  group.name = 'hall';
  scene.add(group);

  // ---- sky + arcade backdrop
  const sky = new Mesh(
    new SphereGeometry(110, 24, 12),
    new ShaderMaterial({ vertexShader: SKY_VERT, fragmentShader: SKY_FRAG, side: BackSide, depthWrite: false, fog: false }),
  );
  sky.renderOrder = -10; sky.frustumCulled = false;
  group.add(sky);
  const wallTex = makeWallTexture(opts.weak ? 1024 : 2048, opts.weak ? 256 : 512);
  const wall = new Mesh(
    new CylinderGeometry(52, 52, 46, 48, 1, true).translate(0, 20, 0),
    new MeshBasicMaterial({ map: wallTex, side: BackSide, fog: false, depthWrite: false, toneMapped: true }),
  );
  wall.renderOrder = -9; wall.frustumCulled = false;
  group.add(wall);

  // ---- floor: flagstone, warm pool toward Emberhold, cold toward Rime, fading into the haze
  const floorGeo = new CircleGeometry(60, 64);
  floorGeo.rotateX(-Math.PI / 2);
  {
    const pos = floorGeo.getAttribute('position');
    const colors = new Float32Array(pos.count * 3);
    const warm = new Color(1.0, 0.78, 0.58), cold = new Color(0.62, 0.78, 1.0), c = new Color();
    for (let i = 0; i < pos.count; i++) {
      const t = Math.min(Math.max(pos.getZ(i) / 16 * 0.5 + 0.5, 0), 1);
      const rr = Math.hypot(pos.getX(i), pos.getZ(i));
      const fall = 1 - Math.min(Math.max((rr - 7) / 30, 0), 1);
      c.copy(cold).lerp(warm, t).multiplyScalar(0.1 + 0.9 * fall * fall * fall);
      colors[i * 3] = c.r; colors[i * 3 + 1] = c.g; colors[i * 3 + 2] = c.b;
    }
    floorGeo.setAttribute('color', new Float32BufferAttribute(colors, 3));
  }
  const floorTex = makeFloorTexture(opts.weak ? 512 : 1024);
  floorTex.repeat.set(16, 16);
  const floor = new Mesh(floorGeo, new MeshStandardMaterial({ map: floorTex, vertexColors: true, roughness: 0.62, metalness: 0.12, envMapIntensity: 0.8 }));
  floor.position.y = -1.25;
  floor.receiveShadow = true;
  floor.name = 'floor';
  group.add(floor);

  // ---- static dressing merged into ONE mesh (vertex colours carry the stone / bronze / silver / banner tints)
  const parts: BufferGeometry[] = [];
  const tint = (g: BufferGeometry, c: Color, yFade?: { y0: number; y1: number; to: number }) => {
    const n = g.getAttribute('position').count, pos = g.getAttribute('position');
    const arr = new Float32Array(n * 3);
    for (let i = 0; i < n; i++) {
      const k = yFade ? 1 - (1 - yFade.to) * Math.min(Math.max((pos.getY(i) - yFade.y0) / (yFade.y1 - yFade.y0), 0), 1) : 1;
      arr[i * 3] = c.r * k; arr[i * 3 + 1] = c.g * k; arr[i * 3 + 2] = c.b * k;
    }
    g.setAttribute('color', new Float32BufferAttribute(arr, 3));
    return g;
  };
  const stone = new Color(0x8a8378);
  const bronze = new Color(0xc08a48), silver = new Color(0xa9bccb);
  const banner = (warm: boolean) => new Color(warm ? 0xb4381c : 0x2e6fb0);
  for (let i = 0; i < 12; i++) {
    const a = (i / 12) * Math.PI * 2 + 0.26;
    const x = Math.sin(a) * 25, z = Math.cos(a) * 25;
    parts.push(tint(new CylinderGeometry(1.1, 1.3, 34, 12).translate(x, 15.5, z), stone, { y0: 6, y1: 30, to: 0.35 }));
    parts.push(tint(new BoxGeometry(3.0, 1.0, 3.0).translate(x, -0.7, z), stone));
    // a banner hanging toward the dais
    const warm = Math.cos(a) > 0;
    const bx = x * 0.9, bz = z * 0.9;
    const bg = new BoxGeometry(1.5, 9, 0.08).translate(0, 0, 0);
    bg.rotateY(a + Math.PI);
    bg.translate(bx, 12, bz);
    parts.push(tint(bg, banner(warm), { y0: 8, y1: 17, to: 0.5 }));
  }
  const brazier = (x: number, z: number, y: number, s: number, warm: boolean) => {
    const c = warm ? bronze : silver;
    parts.push(tint(new CylinderGeometry(0.16 * s, 0.3 * s, 1.5 * s, 10).translate(x, y + 0.75 * s, z), c));
    parts.push(tint(new CylinderGeometry(0.58 * s, 0.28 * s, 0.38 * s, 14).translate(x, y + 1.62 * s, z), c));
    parts.push(tint(new TorusGeometry(0.58 * s, 0.05 * s, 6, 18).rotateX(Math.PI / 2).translate(x, y + 1.82 * s, z), c));
    parts.push(tint(new CylinderGeometry(0.46 * s, 0.46 * s, 0.04 * s, 14).translate(x, y + 1.78 * s, z), new Color(warm ? 0xff7a1a : 0x66d2ff)));
  };
  const HALL_BRAZIERS: Array<[number, number, boolean]> = [[-10.9, 3.6, true], [10.9, 3.6, true], [-10.9, -3.8, false], [10.9, -3.8, false]];
  for (const [x, z, warm] of HALL_BRAZIERS) brazier(x, z, -1.25, 1, warm);
  // board corner braziers (sit on the frame)
  const CORNERS: Array<[number, number, boolean]> = [];
  for (const mx of [-1, 1]) for (const mz of [-1, 1]) CORNERS.push([mx * 4.72, mz * 4.72, mz > 0]);
  for (const [x, z, warm] of CORNERS) {
    const c = warm ? bronze : silver, y = 0.09;
    parts.push(tint(new CylinderGeometry(0.14, 0.08, 0.15, 12).translate(x, y + 0.075, z), c));
    parts.push(tint(new TorusGeometry(0.14, 0.02, 6, 16).rotateX(Math.PI / 2).translate(x, y + 0.15, z), c));
    parts.push(tint(new CylinderGeometry(0.11, 0.11, 0.02, 12).translate(x, y + 0.14, z), new Color(warm ? 0xff8a2a : 0x7fdcff)));
  }
  const dressing = new Mesh(
    mergeGeometries(parts, false)!,
    new MeshStandardMaterial({ vertexColors: true, roughness: 0.55, metalness: 0.45, envMapIntensity: 1.0, side: DoubleSide }),
  );
  dressing.name = 'hallDressing';
  group.add(dressing);
  parts.forEach((p) => p.dispose());

  // ---- warm and cool islands of light on the floor under each brazier (one flat additive mesh)
  {
    const pos: number[] = [], uv: number[] = [], col: number[] = [], idx: number[] = [];
    HALL_BRAZIERS.forEach(([x, z, warm], i) => {
      const r = 6.5, y = -1.235;
      const c = warm ? [1.0, 0.52, 0.16] : [0.3, 0.62, 1.0];
      pos.push(x - r, y, z - r, x + r, y, z - r, x + r, y, z + r, x - r, y, z + r);
      uv.push(0, 0, 1, 0, 1, 1, 0, 1);
      for (let k = 0; k < 4; k++) col.push(c[0] * 0.55, c[1] * 0.55, c[2] * 0.55);
      idx.push(i * 4, i * 4 + 2, i * 4 + 1, i * 4, i * 4 + 3, i * 4 + 2);
    });
    const pg = new BufferGeometry();
    pg.setAttribute('position', new Float32BufferAttribute(pos, 3));
    pg.setAttribute('uv', new Float32BufferAttribute(uv, 2));
    pg.setAttribute('color', new Float32BufferAttribute(col, 3));
    pg.setIndex(idx);
    const pools = new Mesh(pg, new MeshBasicMaterial({ map: makeGlowTexture(128), vertexColors: true, transparent: true, depthWrite: false, blending: AdditiveBlending, fog: false }));
    pools.renderOrder = 1; pools.frustumCulled = false;
    group.add(pools);
  }

  // ---- one additive billboard batch: flames, halos, wall-light glows
  type Glow = { x: number; y: number; z: number; w: number; h: number; r: number; g: number; b: number; phase: number; kind: number };
  const glows: Glow[] = [];
  const addFlame = (x: number, y: number, z: number, warm: boolean, s: number) => {
    const c = warm ? [3.2, 1.35, 0.35] : [0.8, 2.2, 3.4];
    glows.push({ x, y: y + 2.4 * s, z, w: 0.95 * s, h: 1.8 * s, r: c[0], g: c[1], b: c[2], phase: x * 0.7 + z, kind: 1 });   // flame core (flickers)
    glows.push({ x, y: y + 2.5 * s, z, w: 2.6 * s, h: 3.0 * s, r: c[0] * 0.12, g: c[1] * 0.12, b: c[2] * 0.12, phase: x + z * 0.3, kind: 2 }); // halo (breathes)
    glows.push({ x, y: y + 2.3 * s, z, w: 6.5 * s, h: 6.5 * s, r: c[0] * 0.03, g: c[1] * 0.03, b: c[2] * 0.03, phase: 0, kind: 0 });       // wide ambient bloom
  };
  for (const [x, z, warm] of HALL_BRAZIERS) addFlame(x, -1.25, z, warm, 1);
  for (const [x, z, warm] of CORNERS) addFlame(x, -0.09, z, warm, 0.2); // 0.2 scale: flame sits just above the frame cup
  // soft backlights behind each army (replaces the old per-frame fading haze sprites)
  for (const [x, y, z, w, h, c] of [
    [-6, 1.6, 10.5, 8, 4, [1.0, 0.45, 0.12]], [6, 1.6, 10.5, 8, 4, [1.0, 0.45, 0.12]], [0, 2.2, 12.5, 12, 5, [1.0, 0.55, 0.2]],
    [-6, 1.6, -10.5, 8, 4, [0.3, 0.55, 1.0]], [6, 1.6, -10.5, 8, 4, [0.3, 0.55, 1.0]], [0, 2.2, -12.5, 12, 5, [0.4, 0.65, 1.0]],
  ] as Array<[number, number, number, number, number, number[]]>) {
    glows.push({ x, y, z, w, h, r: c[0] * 0.16, g: c[1] * 0.16, b: c[2] * 0.16, phase: x, kind: 0 });
  }

  const nq = glows.length;
  const gPos = new Float32Array(nq * 4 * 3), gCorner = new Float32Array(nq * 4 * 2), gSize = new Float32Array(nq * 4 * 2);
  const gCol = new Float32Array(nq * 4 * 3), gData = new Float32Array(nq * 4 * 2), gIdx = new Uint16Array(nq * 6);
  const corners = [[-1, -1], [1, -1], [1, 1], [-1, 1]];
  glows.forEach((q, i) => {
    for (let k = 0; k < 4; k++) {
      const v = i * 4 + k;
      gPos.set([q.x, q.y, q.z], v * 3); gCorner.set(corners[k], v * 2); gSize.set([q.w, q.h], v * 2);
      gCol.set([q.r, q.g, q.b], v * 3); gData.set([q.phase, q.kind], v * 2);
    }
    gIdx.set([i * 4, i * 4 + 1, i * 4 + 2, i * 4, i * 4 + 2, i * 4 + 3], i * 6);
  });
  const gGeo = new BufferGeometry();
  gGeo.setAttribute('position', new BufferAttribute(gPos, 3));
  gGeo.setAttribute('aCorner', new BufferAttribute(gCorner, 2));
  gGeo.setAttribute('aSize', new BufferAttribute(gSize, 2));
  gGeo.setAttribute('aColor', new BufferAttribute(gCol, 3));
  gGeo.setAttribute('aData', new BufferAttribute(gData, 2));
  gGeo.setIndex(new BufferAttribute(gIdx, 1));
  const glowTex = makeGlowTexture(128);
  const glowMat = new ShaderMaterial({
    uniforms: { uTime: { value: 0 }, uMap: { value: glowTex }, uFlicker: { value: 1 } },
    vertexShader: /* glsl */ `
      uniform float uTime; uniform float uFlicker;
      attribute vec2 aCorner; attribute vec2 aSize; attribute vec3 aColor; attribute vec2 aData;
      varying vec2 vUv; varying vec3 vCol;
      void main() {
        float k = 1.0;
        if (aData.y > 0.5 && aData.y < 1.5) k = 1.0 + uFlicker * (sin(uTime * 9.0 + aData.x) * 0.12 + sin(uTime * 17.3 + aData.x * 2.0) * 0.07);
        else if (aData.y > 1.5) k = 1.0 + uFlicker * sin(uTime * 2.3 + aData.x) * 0.06;
        vec3 right = vec3(viewMatrix[0][0], viewMatrix[1][0], viewMatrix[2][0]);
        vec3 up = vec3(viewMatrix[0][1], viewMatrix[1][1], viewMatrix[2][1]);
        vec3 p = position + (right * aCorner.x * aSize.x * (1.0 + (k - 1.0) * 0.4) + up * aCorner.y * aSize.y * k) * 0.5;
        vUv = aCorner * 0.5 + 0.5;
        vCol = aColor * (aData.y > 0.5 ? k : 1.0);
        gl_Position = projectionMatrix * viewMatrix * vec4(p, 1.0);
      }`,
    fragmentShader: /* glsl */ `
      uniform sampler2D uMap; varying vec2 vUv; varying vec3 vCol;
      void main() {
        float a = texture2D(uMap, vUv).a;
        gl_FragColor = vec4(vCol * a, 1.0);
        #include <tonemapping_fragment>
        #include <colorspace_fragment>
      }`,
    transparent: true, depthWrite: false, blending: AdditiveBlending, fog: false,
  });
  const glowMesh = new Mesh(gGeo, glowMat);
  glowMesh.frustumCulled = false;
  glowMesh.renderOrder = 6;
  group.add(glowMesh);
  void glowTex;

  // ---- drifting motes (one Points draw)
  const MOTES = 220;
  const moteGeo = new BufferGeometry();
  {
    const p = new Float32Array(MOTES * 3), a = new Float32Array(MOTES * 4), col = new Float32Array(MOTES * 3);
    let seed = 1337;
    const rnd = () => { seed = (seed * 1664525 + 1013904223) >>> 0; return seed / 4294967296; };
    for (let i = 0; i < MOTES; i++) {
      p[i * 3] = (rnd() - 0.5) * 20; p[i * 3 + 1] = rnd() * 6; p[i * 3 + 2] = (rnd() - 0.5) * 20;
      a[i * 4] = 0.15 + rnd() * 0.3; a[i * 4 + 1] = rnd() * 6.28; a[i * 4 + 2] = 0.05 + rnd() * 0.07; a[i * 4 + 3] = 0.5 + rnd() * 0.6;
      const warm = p[i * 3 + 2] > 0;
      col[i * 3] = warm ? 1.0 : 0.55; col[i * 3 + 1] = warm ? 0.6 : 0.82; col[i * 3 + 2] = warm ? 0.25 : 1.0;
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
        gl_FragColor = vec4(vCol * 1.6, smoothstep(1.0, 0.0, d) * vA * 0.7);
        #include <colorspace_fragment>
      }`,
    transparent: true, depthWrite: false, blending: AdditiveBlending, fog: false,
  });
  const motes = new Points(moteGeo, moteMat);
  motes.frustumCulled = false; motes.renderOrder = 5;
  group.add(motes);

  let ambientOn = true, tierMotes = true;
  const api: Hall = {
    group,
    update(time) {
      glowMat.uniforms.uTime.value = time;
      moteMat.uniforms.uTime.value = time;
    },
    setAmbient(on) {
      ambientOn = on;
      motes.visible = on && tierMotes;
      glowMat.uniforms.uFlicker.value = on ? 1 : 0;
    },
    setTier(tier) {
      tierMotes = tier !== 'low';
      moteGeo.setDrawRange(0, tier === 'high' ? MOTES : 120);
      api.setAmbient(ambientOn);
    },
  };
  return api;
}
