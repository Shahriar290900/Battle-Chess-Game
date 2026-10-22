import { gsap } from 'gsap';
import { Box3, Color, Material, Mesh, Object3D, Vector3 } from 'three';
import { GRAPHICS_PRESETS, bus, type EmitOptions, type Faction, type FxApi, type GraphicsSettings, type ParticlePreset, type PieceActor, type QualityTier } from '../contracts';
import { Debris } from './debris';
import { Effects } from './effects';
import { ParticleSystem } from './particles';
import { fxState } from './common';
import { makeDissolveMaterial } from './shaders/dissolve';
import { makeEmberMaterial, type SweepHandle } from './shaders/ember';
import { makeFrostMaterial } from './shaders/frost';
import { triggerBloomPulse } from './bloomBus';

export { registerBloomPulse, triggerBloomPulse } from './bloomBus';

interface SweepRec { meshes: [Mesh, Mesh['material']][]; handles: SweepHandle[]; tween?: gsap.core.Tween }

let lastParticles: ParticleSystem | null = null;

/**
 * Emit with an explicit faction tint. Currently only `summonSpiral` uses the tint (ember orange or ice cyan);
 * other presets keep their built-in colours.
 */
export function emitFaction(fx: FxApi, preset: ParticlePreset, position: Vector3, faction: Faction, opts?: EmitOptions): void {
  if (lastParticles) lastParticles.nextTint = faction === 'emberhold' ? new Color(2.2, 0.95, 0.25) : new Color(0.9, 2.2, 2.6);
  fx.emit(preset, position, opts);
  if (lastParticles) lastParticles.nextTint = null;
}

export function createFx(): FxApi {
  const particles = new ParticleSystem();
  lastParticles = particles;
  const effects = new Effects(particles);
  const debris = new Debris(particles);
  const sweeps = new WeakMap<PieceActor, SweepRec>();

  const restoreSweep = (actor: PieceActor) => {
    const r = sweeps.get(actor);
    if (!r) return;
    r.tween?.kill();
    for (const [m, orig] of r.meshes) m.material = orig;
    for (const h of r.handles) h.material.dispose();
    sweeps.delete(actor);
  };
  debris.onBeforeShatter = restoreSweep;
  const applyGraphics = (g: GraphicsSettings) => { fxState.gfx = { ...g }; particles.setGraphics(g); debris.setMode(g.physics); };
  particles.onClink = (strength) => bus.emit('debris:impact', { faction: 'emberhold', strength: strength * 0.6 });

  const meshesOf = (o: Object3D): Mesh[] => { const out: Mesh[] = []; o.traverse((c) => { if ((c as Mesh).isMesh && c.visible) out.push(c as Mesh); }); return out; };
  const swapMaterials = <H extends { material: Material }>(meshes: Mesh[], make: (m: Material) => H, rec: [Mesh, Mesh['material']][], handles: H[]) => {
    const cache = new Map<Material, H>();
    const one = (m: Material) => { let h = cache.get(m); if (!h) { h = make(m); cache.set(m, h); handles.push(h); } return h.material; };
    for (const mesh of meshes) {
      rec.push([mesh, mesh.material]);
      mesh.material = Array.isArray(mesh.material) ? mesh.material.map(one) : one(mesh.material);
    }
  };

  return {
    async init(scene, _renderer, camera) {
      fxState.root.add(particles.group);
      scene.add(fxState.root);
      effects.init(fxState.root, camera);
      await debris.init(scene);
    },
    setQuality(tier: QualityTier) { fxState.tier = tier; applyGraphics({ ...GRAPHICS_PRESETS[tier] }); },
    setGraphics(g: GraphicsSettings) { applyGraphics(g); },
    setStaticActors(actors: PieceActor[]) { debris.setStaticActors(actors); },
    emit: (preset, position, opts) => particles.emit(preset, position, opts),
    shatter: (o) => debris.shatter(o),
    shockwave: (p, f, r) => effects.shockwave(p, f, r),
    iceSpikes: (p, c) => effects.iceSpikes(p, c),
    trail: (follow, faction) => effects.trail(follow, faction),
    decal: (p, k) => effects.decal(p, k),
    column: (p, f, d) => effects.column(p, f, d),
    aura: (p, f) => effects.aura(p, f),
    flash: (a) => effects.flash(a),
    mist: () => effects.mist(),

    sweep(actor, kind, duration) {
      restoreSweep(actor);
      actor.root.updateWorldMatrix(true, true);
      const box = new Box3().setFromObject(actor.model);
      const centre = new Vector3();
      const sock = actor.sockets.socket_impact;
      if (sock) sock.getWorldPosition(centre); else box.getCenter(centre);
      let radius = 0.5;
      for (let i = 0; i < 8; i++) {
        const c = new Vector3(i & 1 ? box.max.x : box.min.x, i & 2 ? box.max.y : box.min.y, i & 4 ? box.max.z : box.min.z);
        radius = Math.max(radius, c.distanceTo(centre));
      }
      const rec: SweepRec = { meshes: [], handles: [] };
      swapMaterials(actor.meshes.length ? actor.meshes : meshesOf(actor.model),
        (m) => (kind === 'frost' ? makeFrostMaterial(m, centre, radius) : makeEmberMaterial(m, centre, radius)), rec.meshes, rec.handles);
      sweeps.set(actor, rec);
      if (kind === 'ember') triggerBloomPulse(0.4, duration);
      return new Promise<void>((resolve) => {
        const progress = { value: 0 };
        rec.tween = gsap.to(progress, {
          value: 1, duration: Math.max(0.01, duration), ease: 'power1.out',
          onUpdate: () => { for (const h of rec.handles) h.uniforms.uFxP.value = progress.value; },
          onComplete: () => resolve(),
        });
      });
    },

    dissolve(obj, faction, duration) {
      const rec: [Mesh, Mesh['material']][] = [];
      const handles: ReturnType<typeof makeDissolveMaterial>[] = [];
      swapMaterials(meshesOf(obj), (m) => makeDissolveMaterial(m, faction), rec, handles);
      return new Promise<void>((resolve) => {
        const progress = { value: 0 };
        gsap.to(progress, {
          value: 1, duration: Math.max(0.01, duration), ease: 'power1.in',
          onUpdate: () => { for (const h of handles) h.uniforms.uFxP.value = progress.value; },
          onComplete: () => {
            obj.visible = false;
            for (const [m, orig] of rec) m.material = orig;
            for (const h of handles) h.material.dispose();
            resolve();
          },
        });
      });
    },

    update(dt) {
      fxState.time += dt;
      particles.update(dt);
      effects.update(dt);
      debris.update(dt);
    },
  };
}
