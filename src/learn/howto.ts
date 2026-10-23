// How to Play: a contents page of interactive lessons (one per piece, rules, mates, tactics). A lesson sets up its
// preset position on the real board; the learner plays the move themselves. Wrong tries get a gentle hint; the
// right move plays the real sequence and earns a "lesson complete" stamp that is saved.
import { Rules, START_FEN } from '../core/rules';
import { btn, clear, h, sleep, tip } from './dom';
import { GROUP_ORDER, GROUP_TITLE, LESSONS, isSolved, lessonsInGroup, successText, type Lesson } from './lessons';
import type { ProgressStore } from './progress';
import type { Session } from './session';
import { TINT } from './stage';
import { createCaption } from './ui';

export interface HowToDeps { progress: ProgressStore; startBeginnerGame(): void; openTutorial(): void }

export function runHowTo(session: Session, deps: HowToDeps, startAt?: string): void {
  const s = session.services;
  const stage = session.stage();
  const { progress } = deps;
  let current: Lesson | null = null;
  let solved = false;
  let busyReset = false;

  // ---------------------------------------------------------------- contents page
  const screen = h('section', { class: 'learn-screen learn-contents' });
  const bar = h('div', { class: 'learn-progress-bar' }, h('i'));
  const barText = h('p', { class: 'learn-progress-text' });
  const lists = h('div', { class: 'learn-groups' });
  const head = h('header', { class: 'learn-head' },
    h('h1', { class: 'learn-title', text: 'How to Play' }),
    h('p', { class: 'learn-script', text: 'Lessons for the field of battle' }),
    barText, bar,
  );
  const foot = h('div', { class: 'learn-foot' },
    btn('Beginner game', tip('Beginner game', 'Play the Computer on Easy with move hints.'), () => { void session.close({ toMenu: false, keepBoard: true }).then(() => deps.startBeginnerGame()); }, 'learn-gold'),
    btn('Replay tutorial', tip('Tutorial', 'Take the guided tour of the controls and cinematics again.'), () => { deps.openTutorial(); }),
    btn('Back to menu', tip('Back', 'Return to the main menu.'), () => { void session.close(); }),
  );
  screen.append(head, lists, foot);
  session.root.append(screen);

  function renderContents() {
    clear(lists);
    const done = progress.doneCount(LESSONS.map((l) => l.id));
    barText.textContent = `${done} of ${LESSONS.length} lessons complete`;
    (bar.firstChild as HTMLElement).style.width = `${(done / LESSONS.length) * 100}%`;
    for (const g of GROUP_ORDER) {
      const items = lessonsInGroup(g);
      lists.append(h('section', { class: 'learn-group' },
        h('h2', { class: 'learn-group-title', text: `${GROUP_TITLE[g]} (${progress.doneCount(items.map((l) => l.id))}/${items.length})` }),
        h('ul', { class: 'learn-lessons' }, ...items.map((l) => h('li', null, h('button', {
          class: `learn-lesson${progress.isDone(l.id) ? ' done' : ''}`, type: 'button',
          'data-tip': `${l.title}|${l.blurb}${progress.isDone(l.id) ? ' (complete)' : ''}`,
          onClick: () => openLesson(l),
        }, h('span', { class: 'learn-lesson-mark', 'aria-hidden': 'true', text: progress.isDone(l.id) ? '✓' : '' }),
        h('span', { class: 'learn-lesson-name', text: l.title }), h('span', { class: 'learn-lesson-blurb', text: l.blurb })))))));
    }
  }

  // ---------------------------------------------------------------- lesson view
  const card = createCaption(session);
  card.el.hidden = true;
  const contentsBtn = btn('Contents', tip('Contents', 'Back to the list of lessons.'), () => showContents(), 'learn-quiet');
  const resetBtn = btn('Reset', tip('Reset', 'Put the pieces back and try again.'), () => { void resetLesson(); }, 'learn-quiet');
  const showBtn = btn('Show me', tip('Show me', 'Highlight a move that solves the lesson.'), () => showMe());
  const nextBtn = btn('Next lesson', tip('Next lesson', 'Go on to the next lesson.'), () => { const i = LESSONS.indexOf(current!); if (i >= 0 && i < LESSONS.length - 1) openLesson(LESSONS[i + 1]); else showContents(); }, 'learn-primary');
  card.actions.append(contentsBtn, resetBtn, showBtn, nextBtn);
  session.addCleanup(() => card.dispose());

  function showContents() {
    stage.onAttempt = null; stage.inputEnabled = false;
    s.sequences.skip();
    stage.setPosition(START_FEN, 'w', true);
    session.onBack = () => { void session.close(); return true; };
    card.el.hidden = true;
    session.setReserve(0);
    screen.hidden = false;
    current = null;
    renderContents();
    (lists.querySelector('.learn-lesson') as HTMLElement | null)?.focus({ preventScroll: true });
  }

  async function resetLesson() {
    if (!current || busyReset) return;
    busyReset = true;
    solved = false;
    stage.inputEnabled = true;
    stage.setPosition(current.fen, 'w', false);
    stage.tint(current.focus, TINT.focus);
    stage.tint(current.goal, TINT.goal);
    card.clearStamp();
    card.setStatus(current.task, 'info');
    nextBtn.disabled = true;
    showBtn.disabled = false;
    busyReset = false;
  }

  function openLesson(l: Lesson) {
    current = l;
    screen.hidden = true;
    card.el.hidden = false;
    card.setKicker(GROUP_TITLE[l.group]);
    card.setTitle(l.title);
    card.setText([...l.intro, `Your task: ${l.task}`]);
    nextBtn.hidden = false;
    stage.onSelect = null;
    stage.selectable = null;
    stage.onAttempt = attempt;
    void resetLesson();
    session.onBack = () => { showContents(); return true; };
  }

  function showMe() {
    if (!current || solved) return;
    const sol = current.solutions[0];
    stage.showHintMove(sol.from, sol.to);
    card.setStatus(`A good move: ${sol.from} to ${sol.to}.`, 'hint');
  }

  async function attempt(from: string, to: string, promotion?: import('../contracts').PromotionRole): Promise<'ok' | 'illegal' | 'wrong'> {
    const lesson = current;
    if (!lesson || solved) return 'wrong';
    const rules = stage.rules;
    stage.clearHintMove();
    if (!rules.isLegal(from, to, promotion ?? (rules.legalMovesFrom(from).find((m) => m.to === to)?.isPromotion ? 'queen' : undefined))) {
      progress.attempt(lesson.id);
      card.setStatus(lesson.hints?.[from + to] ?? lesson.illegalHint, 'hint');
      stage.flash([to], TINT.wrong);
      return 'illegal';
    }
    const trial = new Rules(rules.fen());
    const res = trial.move(from, to, promotion);
    if (!res) { card.setStatus(lesson.illegalHint, 'hint'); return 'illegal'; }
    if (isSolved(lesson, res, rules)) {
      rules.move(from, to, promotion);
      solved = true;
      stage.clearTints();
      card.setStatus(successText(lesson, res), 'ok');
      nextBtn.disabled = true;
      await stage.play(res);
      if (session.closed) return 'ok';
      progress.complete(lesson.id);
      card.stamp('Lesson complete');
      card.setStatus(`${successText(lesson, res)} ${lesson.tip}`, 'ok');
      nextBtn.disabled = false;
      showBtn.disabled = true;
      return 'ok';
    }
    progress.attempt(lesson.id);
    const verdict = lesson.explainWrong?.(res);
    if (verdict) {
      card.setStatus(verdict.text, 'hint');
      if (verdict.demo) {
        rules.move(from, to, promotion);
        await stage.play(res);
        await sleep(1500);
        if (!session.closed && current === lesson) await resetLesson();
        return 'ok';
      }
      return 'wrong';
    }
    card.setStatus(lesson.hints?.[from + to] ?? lesson.wrongHint, 'hint');
    stage.flash([to], TINT.wrong);
    return 'wrong';
  }

  showContents();
  const first = startAt ? LESSONS.find((l) => l.id === startAt) : undefined;
  if (first) openLesson(first);
}
