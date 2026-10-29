import { describe, expect, it } from 'vitest';
import { createCameraRig } from '../../src/camera/cameraRig';
import { FILES } from '../../src/contracts';

const stub = () => {
  const el = { style: {}, addEventListener() {}, removeEventListener() {}, setPointerCapture() {}, releasePointerCapture() {}, getRootNode: () => ({ addEventListener() {}, removeEventListener() {} }), ownerDocument: { addEventListener() {}, removeEventListener() {} }, clientWidth: 100, clientHeight: 100 };
  return el as unknown as HTMLElement;
};

const VIEWPORTS: Array<[number, number]> = [[1280, 720], [1024, 768], [390, 844], [844, 390], [768, 1024]];

describe('camera rig seat fit', () => {
  for (const [w, h] of VIEWPORTS) {
    for (const seat of ['w', 'b'] as const) {
      it(`keeps all 64 squares on screen at ${w}x${h} (${seat})`, () => {
        const rig = createCameraRig(stub(), { aspect: w / h });
        rig.resize(w, h);
        rig.toSeat(seat, { instant: true });
        let off = 0;
        for (const f of FILES) for (let r = 1; r <= 8; r++) {
          const p = rig.projectSquare(f + r);
          if (p.x < 0 || p.y < 0 || p.x > w || p.y > h) off++;
        }
        expect(off).toBe(0);
        rig.dispose();
      });
    }
  }
  it('refits immediately on a resize to portrait', () => {
    const rig = createCameraRig(stub(), { aspect: 16 / 9 });
    rig.resize(1280, 720);
    rig.resize(390, 844);
    let off = 0;
    for (const f of FILES) for (let r = 1; r <= 8; r++) {
      const p = rig.projectSquare(f + r);
      if (p.x < 0 || p.y < 0 || p.x > 390 || p.y > 844) off++;
    }
    expect(off).toBe(0);
    rig.dispose();
  });
  it('free-look offsets are clamped and recenter(0) restores the seat pose', () => {
    const rig = createCameraRig(stub(), { aspect: 16 / 9 });
    rig.resize(1280, 720);
    const home = rig.projectSquare('e4');
    rig.orbit(1, 3); rig.zoom(0.1);
    for (let i = 0; i < 60; i++) rig.update(0.05);
    expect(rig.offSeat).toBe(true);
    expect(rig.camera.position.y).toBeGreaterThan(1); // never under the board
    void rig.recenter(0);
    for (let i = 0; i < 10; i++) rig.update(0.05);
    const back = rig.projectSquare('e4');
    expect(Math.abs(back.x - home.x)).toBeLessThan(3);
    expect(Math.abs(back.y - home.y)).toBeLessThan(3);
    expect(rig.offSeat).toBe(false);
    rig.dispose();
  });
});
