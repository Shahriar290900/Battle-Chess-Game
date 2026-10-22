import { Color, Group, Object3D, Vector3 } from 'three';
import { GRAPHICS_PRESETS, type Faction, type GraphicsSettings, type QualityTier } from '../contracts';

export const FX_COLORS = {
  emberhold: { main: new Color(0xff7a1a), hot: new Color(0xffd27a), dark: new Color(0x5e1f1a) },
  rime: { main: new Color(0x7fd3f0), hot: new Color(0x6ff3ff), dark: new Color(0x1c2e44), light: new Color(0xdceff7) },
} as const;

/** Shared mutable fx state. */
export const fxState = {
  tier: 'medium' as QualityTier,
  root: new Group(),
  /** Scene-time seconds, advanced by update(dt). */
  time: 0,
  gfx: { ...GRAPHICS_PRESETS.medium } as GraphicsSettings,
};
fxState.root.name = 'fx_root';

/** Particle budgets per GraphicsSettings.particles. */
export const PARTICLE_CAP: Record<GraphicsSettings['particles'], number> = { high: 500, medium: 250, low: 120 };
export const COUNT_MUL: Record<GraphicsSettings['particles'], number> = { high: 1, medium: 0.75, low: 0.45 };
export const isLow = () => fxState.gfx.particles === 'low' && fxState.tier === 'low';

export const rand = (a: number, b: number) => a + Math.random() * (b - a);
export const factionColor = (f: Faction) => (f === 'emberhold' ? FX_COLORS.emberhold.main : FX_COLORS.rime.hot);

const _v = new Vector3();
export function worldPos(o: Object3D, out = _v): Vector3 { return o.getWorldPosition(out); }

/** Remove & dispose geometry/material of every mesh under obj (only for fx-owned objects). */
export function disposeTree(o: Object3D): void {
  o.traverse((c: any) => {
    if (c.userData?.fxSharedGeo !== true) c.geometry?.dispose?.();
    const m = c.material;
    if (Array.isArray(m)) m.forEach((x) => x.dispose()); else m?.dispose?.();
  });
}
