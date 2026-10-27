// Screenshot runner (software GL friendly: the render loop is paused and frames are drawn on demand).
//   node perf/shots.mjs --w 1280 --h 720 --tier medium --out name [--scenes start,markers,graveyard,capture]
import { mkdirSync } from 'node:fs';
import { join } from 'node:path';
import { launch, root } from './lib.mjs';

const arg = (k, d) => { const i = process.argv.indexOf('--' + k); return i < 0 ? d : process.argv[i + 1]; };
const w = Number(arg('w', 1280)), h = Number(arg('h', 720)), tier = arg('tier', 'medium'), name = arg('out', 'shot');
const scenes = String(arg('scenes', 'start,markers,graveyard')).split(',');
const dir = join(root, 'perf', 'results', 'shots');
mkdirSync(dir, { recursive: true });
const hnd = await launch();
try {
  const { page, errors } = await hnd.open({ width: w, height: h, query: `debug&quality=${tier}&perf` });
  await page.keyboard.press('Space');
  await page.waitForTimeout(1500);
  const shot = async (tag, frames = 2) => {
    await page.evaluate((n) => { for (let i = 0; i < n; i++) window.__bc.loop.step(60); }, frames);
    await page.screenshot({ path: join(dir, `${name}-${tier}-${w}x${h}-${tag}.png`), timeout: 600000 });
    console.log('shot', tag);
  };
  await page.evaluate(async () => { window.__bc.loop.pause(); await window.__bc.attract?.stop(); });
  await page.evaluate(() => window.__bc.controller.newGame({ kind: 'hotseat', playerSide: 'w', aiLevel: 'easy' }));
  await page.waitForTimeout(3500); // camera settle (tweens run without rendering)
  if (!process.argv.includes('--ui')) await page.evaluate(() => { const u = document.getElementById('ui-root'); if (u) u.style.visibility = 'hidden'; });
  if (scenes.includes('start')) await shot('start', 3);
  if (scenes.includes('markers')) {
    for (const style of ['glow', 'brackets', 'tint', 'runes']) {
      await page.evaluate((st) => {
        const b = window.__bc;
        b.settings.set('highlightStyle', st);
        b.markers.setSelected('e2');
        b.markers.show([{ square: 'e3', capture: false }, { square: 'e4', capture: false }, { square: 'd5', capture: true }, { square: 'f5', capture: true }]);
        b.markers.setLastMove('g1', 'f3');
        b.board.tintSquare('e1', 0xff3a2a);
      }, style);
      await shot(`markers-${style}`, 2);
    }
    await page.evaluate(() => { const b = window.__bc; b.markers.clear(); b.markers.setSelected(null); b.markers.setLastMove(null, null); b.board.tintSquare('e1', null); });
  }
  if (scenes.includes('graveyard')) {
    await page.evaluate(() => {
      // a middlegame: several captures each side
      window.__bc.board.syncGraveyard([
        { faction: 'rime', role: 'pawn' }, { faction: 'rime', role: 'pawn' }, { faction: 'rime', role: 'knight' }, { faction: 'rime', role: 'bishop' }, { faction: 'rime', role: 'queen' },
        { faction: 'emberhold', role: 'pawn' }, { faction: 'emberhold', role: 'pawn' }, { faction: 'emberhold', role: 'pawn' }, { faction: 'emberhold', role: 'rook' }, { faction: 'emberhold', role: 'knight' },
      ]);
    });
    await page.waitForTimeout(1500);
    await shot('graveyard', 3);
  }
  if (scenes.includes('capture')) {
    await page.evaluate(() => { window.__bc.settings.set('captureMode', 'full'); window.__bc.loop.resume(); });
    const play = (f, t) => page.evaluate(([f, t]) => window.__bc.controller.playMove(f, t), [f, t]);
    await play('e2', 'e4'); await play('d7', 'd5');
    const cap = page.evaluate(() => window.__bc.controller.playMove('e4', 'd5'));
    for (let i = 1; i <= 3; i++) { await page.waitForTimeout(2500); await page.evaluate(() => { window.__bc.loop.pause(); window.__bc.loop.step(60); }); await page.screenshot({ path: join(dir, `${name}-${tier}-${w}x${h}-capture${i}.png`), timeout: 600000 }); await page.evaluate(() => window.__bc.loop.resume()); }
    await Promise.race([cap, page.waitForTimeout(120000)]);
    await page.evaluate(() => { window.__bc.loop.pause(); });
    await shot('after-capture', 3);
  }
  console.log('errors', JSON.stringify([...new Set(errors)].slice(0, 8)));
} finally { await hnd.close(); }
