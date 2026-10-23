// First-launch guided tutorial on the real board: controls, a turn, capture / check / mate cinematics, skipping,
// animation settings, how the animations are built, and the two game modes. Uses real pieces and real sequences.
import type { MoveResult } from '../contracts';
import { START_FEN } from '../core/rules';
import { btn, h, isTouch, sleep, tip } from './dom';
import type { Session } from './session';
import { TUTORIAL_POSITIONS, scriptMove } from './script';
import { TINT, type LearnStage } from './stage';
import { createCaption, segmented, slider } from './ui';
import type { ProgressStore } from './progress';

export interface TutorialDeps { progress: ProgressStore; startBeginnerGame(): void }

interface Ctx {
  session: Session; stage: LearnStage; say(text: string, kind?: 'info' | 'hint' | 'ok'): void;
  /** Enable / disable the Next button. */
  gate(open: boolean): void;
  extra: HTMLElement;
  live: HTMLElement;
}
interface Step {
  id: string;
  title: string;
  text: (touch: boolean) => string[];
  enter?(c: Ctx): void | Promise<void>;
  leave?(c: Ctx): void;
  /** Starts locked until the step's own goal is met. */
  locked?: boolean;
}

const PHASES: Record<string, string> = {
  'capture:begin': '1. Approach: the attacker closes in',
  'attack:whoosh': '2. Strike: the Attack clip plays',
  'capture:impact': '3. Impact: hit-stop, camera shake, sparks',
  'capture:shatter': '4. Shatter: physics fragments burst',
  'capture:end': '5. Settle: the winner returns to Idle',
};

export function runTutorial(session: Session, deps: TutorialDeps): void {
  const s = session.services;
  const stage = session.stage();
  const card = createCaption(session);
  const live = h('p', { class: 'learn-live', 'aria-live': 'polite' });
  card.extra.append(live);
  const stepExtra = h('div', { class: 'learn-step-extra' });
  card.extra.append(stepExtra);
  let index = 0;
  let token = 0;
  let nextBtn!: HTMLButtonElement;
  let backBtn!: HTMLButtonElement;
  let finished = false;

  const offs = (['capture:begin', 'attack:whoosh', 'capture:impact', 'capture:shatter', 'capture:end'] as const).map((n) => s.bus.on(n, () => { live.textContent = PHASES[n]; }));
  session.addCleanup(() => { offs.forEach((f) => f()); card.dispose(); });

  const finish = async (toGame: boolean) => {
    if (finished) return;
    finished = true;
    s.settings.set('tutorialSeen', true);
    if (toGame) { deps.progress.setTutorialDone(); await session.close({ toMenu: false, keepBoard: true }); deps.startBeginnerGame(); return; }
    await session.close();
  };
  const finishAndDone = () => { deps.progress.setTutorialDone(); void finish(false); };

  const play = async (pos: keyof typeof TUTORIAL_POSITIONS, override: Partial<import('../contracts').Settings> = { captureMode: 'full', animSpeed: 1 }) => {
    const sm = scriptMove(TUTORIAL_POSITIONS[pos]);
    stage.setPosition(sm.fen, 'w', true);
    stage.tint([sm.from], TINT.focus); stage.tint([sm.to], TINT.goal);
    await sleep(700);
    stage.clearTints();
    const res = stage.rules.move(sm.from, sm.to) as MoveResult;
    await stage.play(res, override);
  };

  const watchButton = (c: Ctx, label: string, tipText: string, run: () => Promise<void>) => {
    const b = btn(label, tipText, async () => {
      b.disabled = true; c.gate(false); live.textContent = '';
      c.say('Watch the board…');
      try { await run(); } finally { b.disabled = false; b.textContent = 'Watch again'; c.gate(true); c.say(''); }
    }, 'learn-primary');
    stepExtra.append(b);
    return b;
  };

  const steps: Step[] = [
    {
      id: 'welcome', title: 'Welcome to the Field',
      text: () => ['Two hosts meet on the board: the Emberhold (White) and the Rime Host (Black). This short tour covers the controls, how a turn plays out, what the battles look like and how to tune them.', 'It takes about three minutes, and you can skip it at any time.'],
      enter: (c) => { c.stage.setPosition(START_FEN, 'w', true); },
    },
    {
      id: 'controls', title: 'Looking and Choosing',
      text: (t) => t
        ? ['Touch: tap one of your pieces to select it. Glowing discs mark squares it can reach; red rings mark captures. Tap a disc to move, or drag the piece there.', 'In Free camera mode (Settings), drag with one finger to orbit and pinch to zoom.']
        : ['Mouse: click one of your pieces to select it. Glowing discs mark squares it can reach; red rings mark captures. Click a disc to move, or drag the piece there.', 'In Free camera mode (Settings), drag to orbit and use the wheel to zoom. Press Esc for the menu.'],
      enter: (c) => { c.stage.setPosition(START_FEN, 'w', true); c.stage.tint(['e2'], TINT.focus); },
    },
    {
      id: 'move', title: 'Your First Move', locked: true,
      text: (t) => [`${t ? 'Tap' : 'Click'} the glowing pawn on e2, then move it to e4. Try dragging it too.`],
      enter(c) {
        const st = c.stage;
        st.setPosition(START_FEN, 'w', true);
        st.tint(['e2'], TINT.focus); st.tint(['e4'], TINT.goal);
        st.selectable = (sq) => sq === 'e2';
        st.onSelect = () => c.say('Glowing discs are legal squares. Pick e4, the highlighted one.');
        c.say('Select the pawn on e2.');
        st.onAttempt = async (from, to) => {
          if (from !== 'e2' || (to !== 'e4' && to !== 'e3')) { c.say(from === 'e2' ? 'Move the pawn straight ahead: e3 or e4.' : 'Select the glowing pawn on e2 first.', 'hint'); return 'illegal'; }
          st.clearTints();
          const res = st.rules.move('e2', to)!;
          c.gate(false);
          await st.play(res);
          st.onAttempt = null;
          c.say('Well played. Now it is the Rime Host\'s turn…', 'ok');
          await sleep(500);
          const reply = st.rules.move('e7', 'e5');
          if (reply) await st.play(reply);
          st.selectable = null;
          c.say('A full turn: you move, the board animates, then the opponent answers. Black replied e5.', 'ok');
          c.gate(true);
          return 'ok';
        };
      },
      leave(c) { c.stage.onAttempt = null; c.stage.onSelect = null; c.stage.selectable = null; },
    },
    {
      id: 'turns', title: 'How a Turn Proceeds',
      text: () => ['Select, move, watch: the move plays out as a short scene, then the other side acts. Against the Computer it answers automatically; in Two Players the board swings round to face whoever is next.', 'A check, a capture, a castle or a promotion each get their own scene.'],
    },
    {
      id: 'capture', title: 'The Capture Duel', locked: true,
      text: () => ['A capture is a duel. The attacker closes in and strikes with its own style: a spear thrust, a slam, a leap, a spell. The defender shatters into fragments.', 'The camera cuts between shots, lights flare and every hit has its sound. Press the button and watch the Emberhold bishop take the Rime knight.'],
      enter(c) {
        c.stage.setPosition(scriptMove(TUTORIAL_POSITIONS.capture).fen, 'w', true);
        watchButton(c, 'Watch the capture', 'Capture|Play the real capture cinematic on this position.', () => play('capture'));
      },
    },
    {
      id: 'skip', title: 'Skipping Animations', locked: true,
      text: (t) => [`Impatient? ${t ? 'Tap' : 'Click'} anywhere on the board during a scene to skip it; the position snaps to its final state. The skip key on the HUD does the same.`, 'Try it: start the scene and skip it straight away.'],
      enter(c) {
        c.stage.setPosition(scriptMove(TUTORIAL_POSITIONS.capture).fen, 'w', true);
        watchButton(c, 'Play, then skip it', 'Skip|Start a capture, then tap the board to skip it.', async () => {
          const p = play('capture');
          c.say(`${isTouch() ? 'Tap' : 'Click'} the board now to skip!`, 'hint');
          await p;
        });
      },
    },
    {
      id: 'check', title: 'Check', locked: true,
      text: () => ['When a piece attacks the enemy king it gives check. The attacker turns on the king and taunts it, an aura pulses and the king\'s tile glows red.', 'The king must then escape, block or capture the attacker: you can never leave a king in check.'],
      enter(c) {
        c.stage.setPosition(scriptMove(TUTORIAL_POSITIONS.check).fen, 'w', true);
        watchButton(c, 'Watch the check', 'Check|Play the real check provoke sequence.', () => play('check'));
      },
    },
    {
      id: 'mate', title: 'Checkmate', locked: true,
      text: () => ['If the king cannot escape, block or capture, it is checkmate and the game ends. The mated king falls to its knees, its army drops their weapons and the winners celebrate.', 'This is the famous scholar\'s mate: a queen takes on f7 with the bishop behind her.'],
      enter(c) {
        c.stage.setPosition(scriptMove(TUTORIAL_POSITIONS.mate).fen, 'w', true);
        watchButton(c, 'Watch the checkmate', 'Checkmate|Play the capture and the surrender sequence.', () => play('mate'));
      },
    },
    {
      id: 'settings', title: 'Animation Speed and Style',
      text: () => ['Tune the scenes to taste. Full is the whole cinematic, Quick plays a fast version, Off skips straight to the result. Speed scales everything. These are the same options as in Settings.'],
      enter(c) {
        c.stage.setPosition(scriptMove(TUTORIAL_POSITIONS.capture).fen, 'w', true);
        const st = s.settings;
        stepExtra.append(
          segmented('Capture scenes', 'Capture scenes', [
            { value: 'full', label: 'Full', tip: 'The full cinematic for every capture.' },
            { value: 'quick', label: 'Quick', tip: 'A faster, shorter version.' },
            { value: 'off', label: 'Off', tip: 'No cinematic: pieces just change places.' },
          ], st.get().captureMode, (v) => st.set('captureMode', v)).el,
          slider('Animation speed', 'Speed|Scale every animation from half to double speed.', 0.5, 2, 0.25, st.get().animSpeed, (v) => `${v.toFixed(2)}x`, (v) => st.set('animSpeed', v)),
        );
        watchButton(c, 'Try it on a capture', 'Try|Replay the capture with your settings.', () => play('capture', {}));
      },
    },
    {
      id: 'craft', title: 'How the Animations Are Made',
      text: () => ['Every piece is a skinned model with its own clips: Idle, Move, Attack, Hit, Victory, and for checks and mates Taunt and Surrender. A director lays a GSAP timeline over them: approach, strike, impact.', 'On impact the camera shakes, the defender is swapped for a ready-cut fragment set and a physics engine scatters it. Lights, particles and sounds are cued on the same timeline. Watch it at half speed with the stages named below.'],
      enter(c) {
        c.stage.setPosition(scriptMove(TUTORIAL_POSITIONS.capture).fen, 'w', true);
        watchButton(c, 'Slow-motion breakdown', 'Breakdown|Replay a capture at half speed with its stages labelled.', () => play('capture', { captureMode: 'full', animSpeed: 0.5 }));
      },
    },
    {
      id: 'modes', title: 'Two Ways to Play',
      text: () => ['Play vs Computer: choose your side and a level from Easy to Master. The camera stays behind your host.', 'Two Players: pass the device. The board turns to face whoever is to move. Watch it swing to the Rime Host\'s seat.'],
      enter(c) {
        c.stage.setPosition(START_FEN, 'w', true);
        const turn = async (side: 'w' | 'b') => { c.gate(false); await s.camera.toSeat(side); c.gate(true); };
        stepExtra.append(
          btn('Rime Host\'s seat', tip('Black\'s seat', 'Swing the camera round to the Rime Host side.'), () => { void turn('b'); }),
          btn('Emberhold\'s seat', tip('White\'s seat', 'Swing the camera back to the Emberhold side.'), () => { void turn('w'); }),
        );
      },
      leave(c) { void s.camera.toSeat('w', { instant: true }); void c; },
    },
    {
      id: 'done', title: 'Ready for Battle',
      text: () => ['That is everything. The How to Play book has a lesson for every piece and rule, and the Piece Library lets you inspect each warrior and watch it duel.', 'Want a gentle first game? Start a beginner game against the Computer on Easy, with move hints on.'],
    },
  ];

  const ctx: Ctx = {
    session, stage, extra: stepExtra, live,
    say: (t, k) => card.setStatus(t, k),
    gate: (open) => { nextBtn.disabled = !open; },
  };

  const show = async (i: number) => {
    token++;
    steps[index]?.leave?.(ctx);
    index = i;
    const step = steps[i];
    stage.onAttempt = null; stage.onSelect = null; stage.selectable = null;
    stage.clearTints();
    while (stepExtra.firstChild) stepExtra.removeChild(stepExtra.firstChild);
    live.textContent = '';
    card.setKicker(`Step ${i + 1} of ${steps.length}`);
    card.setTitle(step.title);
    card.setText(step.text(isTouch()));
    card.setStatus('');
    nextBtn.textContent = i === steps.length - 1 ? 'Finish' : 'Next';
    nextBtn.disabled = !!step.locked;
    backBtn.disabled = i === 0;
    s.sequences.skip();
    await step.enter?.(ctx);
  };

  backBtn = btn('Back', tip('Back', 'Return to the previous step.'), () => { if (index > 0) void show(index - 1); });
  nextBtn = btn('Next', tip('Next', 'Go on to the next step.'), () => { if (index < steps.length - 1) void show(index + 1); else finishAndDone(); }, 'learn-primary');
  const skipBtn = btn('Skip tutorial', tip('Skip tutorial', 'Leave the tour. You can replay it from How to Play any time.'), () => { void finish(false); });
  const beginner = btn('Beginner game', tip('Beginner game', 'Start a game against the Computer on Easy with move hints.'), () => { deps.progress.setTutorialDone(); void finish(true); }, 'learn-gold');
  beginner.hidden = true;
  card.actions.append(skipBtn, backBtn, nextBtn, beginner);
  // show the beginner-game shortcut on the last step
  const obs = new MutationObserver(() => { beginner.hidden = index !== steps.length - 1; });
  obs.observe(nextBtn, { childList: true, characterData: true, subtree: true });
  session.addCleanup(() => { obs.disconnect(); });
  session.onBack = () => { void finish(false); return true; };
  void show(0);
}
