// Composition root: renderer + scene → post → fx → assets → board → camera → cinematics → audio → platform → controller → UI.
import { gsap } from 'gsap';
import { Raycaster, Vector2 } from 'three';
import { bus, SIDE_FACTION, type QualityTier } from './contracts';
import { createAssetRegistry } from './assets/registry';
import { createCameraRig } from './camera/cameraRig';
import { createSequencePlayer } from './cinematics';
import { createAudioBus } from './audio';
import { createAiPlayer } from './core/ai';
import { createGameController } from './core/game';
import { createLivePresenter } from './core/livePresenter';
import { START_FEN } from './core/rules';
import { createSettingsStore } from './core/settings';
import { createFx } from './fx';
import { createPlatform } from './platform';
import { createBoard } from './render/board';
import { createLighting } from './render/lighting';
import { createMarkers } from './render/markers';
import { createGuardedPost } from './render/postGuard';
import { createQuality } from './render/quality';
import { PIXEL_RATIO_CAP, createRenderKit } from './render/scene';
import { createBoardInput } from './ui/boardInput';
import { createUi } from './ui';
import { createPromotionPicker } from './ui/panels';
import { createLoadingScreen } from './ui/screens';

async function boot(): Promise<void> {
  const canvas = document.getElementById('scene') as HTMLCanvasElement;
  const uiRoot = document.getElementById('ui-root') as HTMLElement;
  const loading = createLoadingScreen();
  uiRoot.append(loading.el);

  try {
    gsap.ticker.lagSmoothing(500, 33);
    const platform = createPlatform();
    const settings = createSettingsStore({ bus });
    const params = new URLSearchParams(location.search);
    const forced = params.get('quality') as QualityTier | null; // ?quality=low|medium|high (tests, software GL)
    const step = (name: string) => console.debug(`[boot] ${name}`);
    const startTier: QualityTier = forced === 'low' || forced === 'medium' || forced === 'high' ? forced : settings.get().quality !== 'auto' ? (settings.get().quality as QualityTier) : platform.isMobile ? 'low' : 'medium';

    // ---- renderer, camera, lighting, post, fx
    step('renderer');
    const kit = createRenderKit(canvas);
    kit.setPixelRatioCap(PIXEL_RATIO_CAP[startTier]);
    const rig = createCameraRig(canvas, { aspect: window.innerWidth / window.innerHeight });
    step('lighting');
    const lighting = createLighting(kit.scene, kit.renderer);
    const post = createGuardedPost(kit.renderer, kit.scene, rig.camera, startTier);
    step('fx');
    const fx = createFx();
    await fx.init(kit.scene, kit.renderer, rig.camera);
    fx.setQuality(startTier);
    rig.setMode(settings.get().cameraMode);

    const resize = () => {
      const w = window.innerWidth, h = window.innerHeight;
      kit.setSize(w, h);
      rig.resize(w, h);
      post.setSize(w, h);
    };
    window.addEventListener('resize', resize);
    window.addEventListener('orientationchange', () => setTimeout(resize, 120));
    resize();

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

    // ---- assets
    step('assets');
    const registry = createAssetRegistry();
    await registry.preload((n, total) => loading.setProgress((n / total) * 0.9, `Casting the hosts… ${n}/${total}`));
    registry.lod = startTier === 'low' ? 1 : 0;
    step('board');
    const board = createBoard({ scene: kit.scene, registry, textureSize: platform.isMobile ? 1024 : 2048 });
    const markers = createMarkers(kit.scene);
    board.syncToFen(START_FEN);
    loading.setProgress(0.93, 'Lighting the braziers…');

    // ---- game
    step('game');
    const sequences = createSequencePlayer();
    const ai = createAiPlayer();
    const promotion = createPromotionPicker();
    const presenter = createLivePresenter({
      board, camera: rig, fx, registry, sequences, bus, settings,
      choosePromotion: (side) => promotion.choose(side), cancelPromotion: () => promotion.cancel(),
    });
    const controller = createGameController({ presenter, ai, bus, settings });
    controller.setPhase('loading');

    const startGame = (config: Parameters<typeof controller.newGame>[0]) => {
      void controller.newGame(config);
      void registry.warmFragments();
    };
    const ui = createUi({ root: uiRoot, controller, settings, bus, audio, loading, promotion, onStart: startGame });
    platform.onBack(() => ui.handleBack());
    createBoardInput({ canvas, rig, board, controller, markers, settings, bus, isBlocked: () => ui.modalOpen });

    // ---- settings fan-out
    // Cinematics owns gsap.globalTimeline.timeScale (hit-stop/slow-mo); animSpeed only drives our own tweens.
    rig.setSpeed(settings.get().animSpeed);
    settings.subscribe((s, key) => {
      if (key === 'cameraMode') rig.setMode(s.cameraMode);
      else if (key === 'animSpeed') rig.setSpeed(s.animSpeed);
      else if (key === 'musicEnabled' || key === 'musicVolume' || key === 'sfxVolume') syncAudio();
    });

    // ---- render loop (GSAP ticker: tweens update first, then we render the same frame)
    let benchmarking = false;
    gsap.ticker.add((time, deltaMs) => {
      if (benchmarking) return;
      const dt = Math.min(deltaMs / 1000, 0.1);
      const ts = gsap.globalTimeline.timeScale();
      fx.update(dt * ts);
      board.update(dt * ts);
      markers.update(time);
      lighting.update(time);
      rig.update(dt);
      post.render(dt);
    });

    // ---- quality (2 s benchmark on desktop; mobile → low)
    const quality = createQuality({
      kit, lighting, board, fx, post, platform, settings,
      renderFrame: (dt) => { board.update(dt); rig.update(dt); post.render(dt); },
    });
    loading.setProgress(0.96, 'Measuring the hall…');
    step('quality');
    if (forced) quality.apply(startTier);
    else {
      benchmarking = true;
      try { await quality.resolve(); } finally { benchmarking = false; }
    }
    step('ready');

    // ---- debug / test hook
    if (import.meta.env.DEV || params.has('debug')) {
      (window as unknown as Record<string, unknown>).__bc = {
        controller, rig, board, ui, settings, quality, bus, kit, post, fx, lighting, markers,
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

    controller.setPhase('menu');
    await loading.showGate();
    unlock();
    loading.hide();
    ui.showMenu();
  } catch (err) {
    console.error('[boot] failed', err);
    loading.fail(`Could not start the game: ${err instanceof Error ? err.message : String(err)}`);
  }
}

void boot();
