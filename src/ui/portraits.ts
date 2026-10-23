// King portraits for the allegiance cards: each faction's king is rendered ONCE at load into a small offscreen
// render target (LOD1 mesh, three lights, transparent background) and kept as a PNG data URL. No second WebGL
// context, no per-frame cost, and the render also uploads the king's textures early.
import {
  AmbientLight, Box3, Color, DirectionalLight, HemisphereLight, PerspectiveCamera, SRGBColorSpace, Scene, Vector3, WebGLRenderTarget,
  type WebGLRenderer,
} from 'three';
import type { Faction } from '../contracts';
import type { AssetRegistryImpl } from '../assets/registry';

export type Portraits = Partial<Record<Faction, string>>;

const W = 360, H = 540;
const RIM: Record<Faction, number> = { emberhold: 0xff8a3c, rime: 0x7cc3ff };

export function renderKingPortraits(renderer: WebGLRenderer, registry: AssetRegistryImpl): Portraits {
  const out: Portraits = {};
  const rt = new WebGLRenderTarget(W, H, { samples: 4 });
  rt.texture.colorSpace = SRGBColorSpace;
  const prevLod = registry.lod;
  const prevTarget = renderer.getRenderTarget();
  const prevClear = renderer.getClearAlpha();
  const prevColor = renderer.getClearColor(new Color());
  try {
    registry.lod = 1;
    for (const faction of ['emberhold', 'rime'] as Faction[]) {
      const actor = registry.createActor(faction, 'king', faction === 'emberhold' ? 'e1' : 'e8');
      try {
        const scene = new Scene();
        scene.add(new HemisphereLight(0xdfe6f2, 0x3a3026, 1.5), new AmbientLight(0xffffff, 0.6));
        const key = new DirectionalLight(0xfff0dc, 3.4);
        key.position.set(-2.2, 3.2, 3.4);
        const rim = new DirectionalLight(RIM[faction], 2.6);
        rim.position.set(2.8, 1.8, -2.4);
        scene.add(key, rim);
        actor.root.position.set(0, 0, 0);
        actor.root.rotation.set(0, 0.28, 0); // faces the camera (+Z), a quarter turn for depth
        scene.add(actor.root);
        scene.updateMatrixWorld(true);
        const box = new Box3().setFromObject(actor.root);
        const size = box.getSize(new Vector3()), c = box.getCenter(new Vector3());
        const cam = new PerspectiveCamera(24, W / H, 0.1, 50);
        const fitH = Math.max(size.y * 0.88, (size.x * 1.25) / (W / H));
        const dist = fitH / 2 / Math.tan((cam.fov * Math.PI) / 360);
        const ty = c.y - size.y * 0.2; // king sits in the upper part of the card; the text covers the rest
        cam.position.set(c.x, ty + size.y * 0.04, c.z + dist + size.z / 2);
        cam.lookAt(c.x, ty, c.z);
        renderer.setRenderTarget(rt);
        renderer.setClearColor(0x000000, 0);
        renderer.clear();
        renderer.render(scene, cam);
        const px = new Uint8Array(W * H * 4);
        renderer.readRenderTargetPixels(rt, 0, 0, W, H, px);
        const cv = document.createElement('canvas');
        cv.width = W; cv.height = H;
        const g = cv.getContext('2d')!;
        const img = g.createImageData(W, H);
        for (let y = 0; y < H; y++) img.data.set(px.subarray((H - 1 - y) * W * 4, (H - y) * W * 4), y * W * 4); // flip rows
        g.putImageData(img, 0, 0);
        out[faction] = cv.toDataURL('image/png');
      } finally {
        actor.root.removeFromParent();
        actor.dispose();
      }
    }
  } catch (e) {
    console.warn('[ui] king portraits failed; cards fall back to silhouettes', e);
  } finally {
    registry.lod = prevLod;
    renderer.setRenderTarget(prevTarget);
    renderer.setClearColor(prevColor, prevClear);
    rt.dispose();
  }
  return out;
}
