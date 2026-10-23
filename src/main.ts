// Composition root: renderer + scene → post → fx → assets → board → camera → cinematics → audio → platform → controller → UI.
//
// `services` (built below) is the documented hand-off to optional feature modules such as src/learn:
//   createLearn(services) from src/learn/index.ts, when that file exists, is called once after loading and its
//   open(kind) is wired to the "How to Play" / "Piece Library" books and the first-launch prompt.
//   AppServices = { scene, renderer, camera (CameraRig), registry, board, sequences, fx, audio, kinematics,
//                   settings, bus, post, controller, attract }.
// Loading is driven by real work and reported on the bus as `loading:progress` ({loaded, total=100, stage}).
import { gsap } from 'gsap';
import { Raycaster, Vector2, type PerspectiveCamera, type Scene, type WebGLRenderer } from 'three';
import {
  bus, SIDE_FACTION, type AttractContext, type AttractMode, type AudioBus, type BoardApi, type CameraRig, type EventBus, type FxApi,
  type GameModeConfig, type KinematicsApi, type QualityTier, type SequencePlayer, type SettingsStore,
} from './contracts';
import { createAssetRegistry, type AssetRegistryImpl } from './assets/registry';
import { createCameraRig } from './camera/cameraRig';
import * as cinematics from './cinematics';
import { createAudioBus } from './audio';
import { createAiPlayer } from './core/ai';
import { createGameController, type GameController } from './core/game';
import { createLivePresenter } from './core/livePresenter';
import { START_FEN } from './core/rules';
import { createSettingsStore } from './core/settings';
import { createFx } from './fx';
import { createKinematics } from './kinematics';
import { createPlatform } from './platform';
import { createBoard } from './render/board';
import { applyGraphics, createFpsOverlay } from './render/graphics';
import { createLighting, prewarmCinematicLights } from './render/lighting';
import { createMarkers } from './render/markers';
import { createPost, createVignette } from './render/post';
import { createQuality, createToaster } from './render/quality';
import { detectDevice } from './render/device';
import { createPerf } from './render/perf';
import { PIXEL_RATIO_CAP, createRenderKit, watchViewport } from './render/scene';
import { createBoardInput } from './ui/boardInput';
import { createUi } from './ui';
import { createPromotionPicker } from './ui/endgame';
import { createLoadingScreen } from './ui/loading';
import { renderKingPortraits, type Portraits } from './ui/portraits';
import { installTheme } from './ui/theme';
import './ui/theme.css';

/** Everything a feature module (src/learn, ...) may need. */
export interface AppServices {
  scene: Scene;
  renderer: WebGLRenderer;
  camera: CameraRig & { readonly camera: PerspectiveCamera };
  registry: AssetRegistryImpl;
  board: BoardApi;
  sequences: SequencePlayer;
  fx: FxApi;
  audio: AudioBus;
  kinematics: KinematicsApi;
  settings: SettingsStore;
  bus: EventBus;
  controller: GameController;
  attract: AttractMode | null;
}

type LearnKind = 'tutorial' | 'howto' | 'library';
const learnModules = import.meta.glob('./learn/index.ts', { eager: true }) as Record<string, { createLearn?: (s: AppServices) => { open?(k: LearnKind): void | Promise<unknown>; start?(k: LearnKind): void | Promise<unknown> } | undefined }>;

/** Weighted loading stages; progress is reported on the bus so any UI can show it. */
function createLoadTracker(b: EventBus, stages: Array<[name: string, weight: number]>) {
  const total = stages.reduce((n, s) => n + s[1], 0);
  let done = 0;
  return {
    /** Run one stage; `work` reports its own 0..1 progress. */
    async run<T>(index: number, work: (report: (f: number) => void) => Promise<T> | T): Promise<T> {
      const [name, weight] = stages[index];
      const emit = (f: number) => b.emit('loading:progress', { loaded: Math.round(((done + weight * Math.min(Math.max(f, 0), 1)) / total) * 100), total: 100, stage: name });
      emit(0);
      const out = await work(emit);
      done += weight;
      emit(1);
      return out;
    },
    reset() { done = 0; },
  };
}

async function boot(): Promise<void> {
  installTheme();
  const canvas = document.getElementById('scene') as HTMLCanvasElement;
  const uiRoot = document.getElementById('ui-root') as HTMLElement;
  const loading = createLoadingScreen();
  uiRoot.append(loading.el);
  bus.on('loading:progress', (e) => loading.setProgress(e.loaded / e.total, e.stage));

  try {
    gsap.ticker.lagSmoothing(500, 33);
    const platform = createPlatform();
    const settings = createSettingsStore({ bus });
    const params = new URLSearchParams(location.search);
    const forced = params.get('quality') as QualityTier | null; // ?quality=low|medium|high (tests, software GL)
    const step = (name: string) => console.debug(`[boot] ${name}`);
    const device = detectDevice(platform.isMobile);
    console.debug(`[boot] gpu: ${device.gpu} | mobile=${device.mobile} cores=${device.cores} weak=${device.weak}`);
    const prefTier = settings.get().quality;
    const startTier: QualityTier = forced === 'low' || forced === 'medium' || forced === 'high' ? forced : prefTier !== 'auto' ? prefTier : device.guess;

    // ---- renderer, camera, lighting, post
    step('renderer');
    // MSAA only where the scene renders straight to the canvas (Low); composer tiers use their own passes.
    const kit = createRenderKit(canvas, { antialias: startTier === 'low' });
    kit.setPixelRatioCap(PIXEL_RATIO_CAP[startTier]);
    const rig = createCameraRig(canvas, { aspect: window.innerWidth / window.innerHeight });
    const lighting = createLighting(kit.scene, kit.renderer, { weak: device.weak });
    const post = createPost(kit.renderer, kit.scene, rig.camera, startTier);
    kit.onResize = (w, h) => post.setSize(w, h);
    const vignette = createVignette(canvas.parentElement ?? document.body, canvas.nextElementSibling);
    void vignette;
    const toast = createToaster(document.body);
    const fx = createFx();
    const kinematics = createKinematics();
    // Optional extension (not in KinematicsApi): enables distance/behind-camera culling.
    (kinematics as { setCamera?: (c: typeof rig.camera) => void }).setCamera?.(rig.camera);
    rig.setMode(settings.get().cameraMode);

    let boardRef: { setGraveyardLayout(l: 'sides' | 'ends'): void } | null = null;
    // Follows the visual viewport (mobile URL bar), orientation changes and window resizes without a reload.
    watchViewport((w, h) => {
      kit.setSize(w, h);
      canvas.style.width = `${w}px`;
      canvas.style.height = `${h}px`;
      rig.resize(w, h);
      boardRef?.setGraveyardLayout(w / h < 0.95 ? 'ends' : 'sides');
    });

    // ---- platform + audio (unlock on the first gesture, music follows settings)
    const audio = createAudioBus();
    audio.attach(bus);
    const syncAudio = () => {
      const s = settings.get();
      audio.setMusicEnabled(s.musicEnabled);
      audio.setVolumes(s.musicVolume, s.sfxVolume);
    };
    syncAudio();
    let unlocked = false;
    const unlock = () => {
      if (unlocked) return;
      unlocked = true;
      void audio.unlock().then(syncAudio).catch(() => { unlocked = false; });
    };
    window.addEventListener('pointerdown', unlock, { once: true, capture: true });
    window.addEventListener('keydown', unlock, { once: true, capture: true });
    void platform.init().catch((e) => console.warn('[platform] init failed', e));

    // ---- game objects (created up front; loading fills them)
    const registry = createAssetRegistry({ atlasCell: device.mobile || device.veryWeak ? 128 : 256, anisotropy: device.weak ? 2 : 4 });
    const ai = createAiPlayer();
    const sequences = cinematics.createSequencePlayer();
    const promotion = createPromotionPicker();
    const tracker = createLoadTracker(bus, [['Forging pieces…', 33], ['Raising the hall…', 24], ['Painting portraits…', 4], ['Tempering shaders…', 21], ['Waking the oracle…', 8], ['Tuning the lute…', 10]]);

    // ================= real loading work =================
    step('assets');
    await tracker.run(0, async (report) => {
      await registry.preload((n, total) => report(n / total));
    });
    registry.lod = startTier === 'high' ? 0 : 1;

    step('board');
    const board = createBoard({ scene: kit.scene, registry, textureSize: platform.isMobile ? 1024 : 2048, kinematics, bus, halfRateIdle: device.weak });
    boardRef = board;
    board.setGraveyardLayout(window.innerWidth / window.innerHeight < 0.95 ? 'ends' : 'sides');
    const markers = createMarkers(kit.scene, { settings, getFaction: (sq) => board.actorAt(sq)?.faction });
    board.tintListener = (sq, color) => markers.setTint(sq, color);
    await tracker.run(1, async (report) => {
      await fx.init(kit.scene, kit.renderer, rig.camera); // includes physics (rapier) init
      fx.setQuality(startTier);
      report(0.2);
      board.syncToFen(START_FEN);
      fx.setStaticActors?.(board.allActors());
      report(0.4);
      await registry.warmFragments((n, total) => report(0.4 + 0.6 * (n / total)));
    });

    const presenter = createLivePresenter({
      board, camera: rig, fx, registry, sequences, kinematics, bus, settings,
      choosePromotion: (side) => promotion.choose(side), cancelPromotion: () => promotion.cancel(),
    });
    const controller = createGameController({ presenter, ai, bus, settings });
    controller.setPhase('loading');

    const gfxDeps = { settings, kit, lighting, post, fx, board, kinematics, tier: () => quality.tier, dynScale: () => quality.dynScale };
    const quality = createQuality({
      kit, lighting, board, fx, post, platform, settings, device,
      renderFrame: (dt) => { board.update(dt); rig.update(dt); lighting.tick(dt, false); post.render(dt); },
      applyGraphics: () => applyGraphics(gfxDeps),
      notify: toast,
    });
    let benchmarking = false;
    let portraits: Portraits = {};
    await tracker.run(2, async () => { portraits = renderKingPortraits(kit.renderer, registry); });
    await tracker.run(3, async (report) => {
      // Programs first (so the probe measures steady-state frames), then the real FPS probe, then a recompile only if the tier moved.
      const compileAll = async () => {
        try { await kit.renderer.compileAsync(kit.scene, rig.camera); } catch { /* older drivers: first frame compiles */ }
        // Warm what compileAsync cannot see: LOD0 geometry uploads, hidden queen weapons, fade (transparent) variants, cinematic spotlights.
        board.prewarm(() => post.render(0));
        prewarmCinematicLights(kit.scene, () => post.render(0));
      };
      quality.apply(forced ? startTier : device.guess);
      report(0.15);
      await compileAll();
      report(0.45);
      if (!forced) {
        benchmarking = true;
        const before = quality.tier;
        try { await quality.resolve(); } finally { benchmarking = false; }
        if (quality.tier !== before) await compileAll();
      }
      lighting.invalidateShadows();
      report(1);
    });
    await tracker.run(4, async () => { await ai.init().catch((e) => console.warn('[ai] init failed (fallback engine will be used)', e)); });
    await tracker.run(5, async () => { syncAudio(); }); // audio decode starts on the first gesture (autoplay policy)

    // ---- attract mode (launch flyover behind the menu) and the Learn area: optional modules, feature-checked
    const createAttract = (cinematics as unknown as { createAttract?: (c: AttractContext) => AttractMode }).createAttract;
    const attract: AttractMode | null = createAttract
      ? createAttract({ board, camera: rig, fx, registry, bus, settings: settings.get(), kinematics, sequences })
      : null;

    const services: AppServices = { scene: kit.scene, renderer: kit.renderer, camera: rig, registry, board, sequences, fx, audio, kinematics, settings, bus, controller, attract };
    const learnMod = Object.values(learnModules)[0];
    const learn = learnMod?.createLearn?.(services);
    const learnApi = learn ? { open: (k: LearnKind) => (learn.open ?? learn.start)?.call(learn, k) as void | Promise<unknown> } : undefined;

    // ---- entering a game: stop the flyover, show the loading screen, do the real per-game work, then start
    const enterGame = async (config: GameModeConfig) => {
      loading.show('Preparing the field…');
      const t = createLoadTracker(bus, [['Clearing the field…', 20], ['Raising the hall…', 30], ['Tempering shaders…', 30], ['Waking the oracle…', 20]]);
      await t.run(0, async () => { await attract?.stop(); });
      await t.run(1, async (report) => { await registry.warmFragments((n, total) => report(n / total)); });
      await t.run(2, async () => { try { await kit.renderer.compileAsync(kit.scene, rig.camera); } catch { /* ignore */ } });
      await t.run(3, async () => { if (config.kind === 'vs-ai') await ai.init().catch(() => undefined); });
      await controller.newGame(config);
      loading.hide();
    };

    const ui = createUi({ root: uiRoot, controller, settings, bus, audio, loading, promotion, portraits: () => portraits, onStart: (c) => { void enterGame(c); }, learn: learnApi });
    // Learn screens consume Android back first (its handleBack is an optional extension of the module).
    platform.onBack(() => (learn as { handleBack?: () => boolean } | undefined)?.handleBack?.() || ui.handleBack());
    createBoardInput({ canvas, rig, board, controller, markers, settings, bus, isBlocked: () => ui.modalOpen });
    ui.hud.onLayout((px) => rig.setReserve(px));

    // ---- settings fan-out
    // Cinematics owns gsap.globalTimeline.timeScale (hit-stop/slow-mo); animSpeed only drives our own tweens.
    rig.setSpeed(settings.get().animSpeed);
    const perf = createPerf(kit.renderer, uiRoot);
    const fps = createFpsOverlay(uiRoot);
    fps.setVisible(settings.get().graphics.showFps);
    settings.subscribe((s, key) => {
      if (key === 'cameraMode') rig.setMode(s.cameraMode);
      else if (key === 'animSpeed') rig.setSpeed(s.animSpeed);
      else if (key === 'musicEnabled' || key === 'musicVolume' || key === 'sfxVolume') syncAudio();
      else if (key === 'graphics') { applyGraphics(gfxDeps); fps.setVisible(s.graphics.showFps); }
    });

    // ---- render loop (GSAP ticker: tweens update first, then we render the same frame). The FPS cap skips frames.
    let acc = 0, lastReal = performance.now();
    const frame = (time: number, deltaMs: number) => {
      if (benchmarking) return;
      acc += deltaMs / 1000;
      const cap = settings.get().graphics.fpsCap;
      if (cap > 0 && acc < 1 / cap - 0.004) return;
      const dt = Math.min(acc, 0.1);
      acc = 0;
      const nowReal = performance.now();
      const realDt = (nowReal - lastReal) / 1000;
      lastReal = nowReal;
      const ts = gsap.globalTimeline.timeScale();
      perf.frameStart();
      perf.begin('fx'); fx.update(dt * ts); perf.end('fx');
      perf.begin('mixers'); board.update(dt * ts); perf.end('mixers');
      perf.begin('kinemat'); kinematics.update(dt * ts); perf.end('kinemat'); // after mixers and the cinematics tweens
      perf.begin('misc');
      markers.update(time);
      lighting.update(time, rig.camera.position.z);
      lighting.tick(dt, sequences.running); // shadow refresh: a few Hz when idle, every frame during a capture
      rig.update(dt);
      perf.end('misc');
      perf.begin('render'); post.render(dt); perf.end('render');
      fps.frame(dt);
      perf.frame();
      quality.update(realDt, sequences.running);
    };
    gsap.ticker.add(frame);
    quality.setMonitoring(true);
    document.addEventListener('visibilitychange', () => { quality.setMonitoring(!document.hidden); lastReal = performance.now(); });

    // ---- debug / test hook
    if (import.meta.env.DEV || params.has('debug')) {
      (window as unknown as Record<string, unknown>).__bc = {
        controller, rig, board, ui, settings, quality, bus, kit, post, fx, lighting, markers, services, attract,
        // screenshot / bench helpers: stop the render loop (tweens keep running), then draw single frames on demand
        loop: { pause: () => gsap.ticker.remove(frame), resume: () => gsap.ticker.add(frame), step: (ms = 50) => frame(gsap.ticker.time, ms) },
        squareToScreen: (sq: string) => rig.projectSquare(sq),
        pick: (x: number, y: number) => {
          const r = canvas.getBoundingClientRect();
          const ray = new Raycaster();
          ray.setFromCamera(new Vector2(((x - r.left) / r.width) * 2 - 1, -((y - r.top) / r.height) * 2 + 1), rig.camera);
          const a = board.pickActor(ray);
          return { actor: a ? `${a.id}@${a.square}` : null, square: board.pickSquare(ray), blocked: ui.modalOpen, state: controller.state, top: document.elementFromPoint(x, y)?.className ?? null };
        },
        factionOf: (side: 'w' | 'b') => SIDE_FACTION[side],
      };
    }

    step('ready');
    controller.setPhase('menu');
    await loading.showGate(); // the tap is also the audio-unlock gesture and starts the flyover
    unlock();
    loading.hide();
    attract?.start();
    ui.showMenu();
  } catch (err) {
    console.error('[boot] failed', err);
    loading.fail(`Could not start the game: ${err instanceof Error ? err.message : String(err)}`);
  }
}

void boot();
