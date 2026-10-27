// Render benchmark. Starts its own Vite dev server (port 5290 - never 5173) and ONE headless Brave, then for each
// quality tier measures three scenarios: the start position (idle board), a capture cinematic, and attract mode.
//   node perf/bench.mjs [--tiers low,medium,high] [--label name] [--viewport 1280x720] [--secs 5] [--shots] [--scen start,capture,attract]
// Output: perf/results/<label>.json plus a markdown table on stdout.
// NOTE: reports WEBGL_debug_renderer_info. If it says SwiftShader/llvmpipe the fps numbers are software-GL and
// only draw calls / triangles / CPU ms are meaningful proxies.
import { chromium } from '@playwright/test';
import { mkdirSync, writeFileSync, rmSync, symlinkSync, existsSync, readFileSync } from 'node:fs';
import { execSync } from 'node:child_process';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { createServer } from 'vite';

const here = dirname(fileURLToPath(import.meta.url));
const root = join(here, '..');
const arg = (k, d) => { const i = process.argv.indexOf('--' + k); return i < 0 ? d : (process.argv[i + 1] && !process.argv[i + 1].startsWith('--') ? process.argv[i + 1] : true); };
const tiers = String(arg('tiers', 'low,medium,high')).split(',');
const label = String(arg('label', 'run'));
const [vw, vh] = String(arg('viewport', '800x450')).split('x').map(Number);
const secs = Number(arg('secs', 5));
const shots = !!arg('shots', false);
const scen = String(arg('scen', 'start,capture,attract')).split(',');
const want = (n) => scen.includes(n);
const gate = async (page) => { await page.keyboard.press('Space').catch(() => {}); await page.evaluate(() => document.querySelector('.gate-btn')?.click()); };
const BRAVE = '/Applications/Brave Browser.app/Contents/MacOS/Brave Browser';
const t0 = Date.now();
const dog = setTimeout(() => { console.error('[bench] watchdog: closing'); Promise.resolve(browser?.close()).catch(() => {}).finally(() => process.exit(2)); }, 3300000); // the finally block below closes browser+server on normal failure
const log = (...a) => console.error(`[bench ${((Date.now() - t0) / 1000).toFixed(0)}s]`, ...a);
mkdirSync(join(here, 'results'), { recursive: true });

// --ui-head: other agents may be mid-rewrite of src/ui. Bench a snapshot of the working tree whose src/ui comes from git HEAD.
// --head:    baseline run - the committed (HEAD) render/assets/main code plus only the perf instrumentation.
let benchRoot = root;
if (arg('ui-head', false) || arg('head', false)) {
  benchRoot = '/private/tmp/claude-501/bench-root';
  mkdirSync(benchRoot, { recursive: true });
  rmSync(join(benchRoot, 'src'), { recursive: true, force: true });
  if (arg('head', false)) {
    execSync(`cd "${root}" && git archive HEAD src | tar -x -C "${benchRoot}"`);
    execSync(`cp "${root}/src/render/perf.ts" "${benchRoot}/src/render/perf.ts"`);
    const mp = join(benchRoot, 'src/main.ts');
    const m = readFileSync(mp, 'utf8')
      .replace("import { createQuality } from './render/quality';", "import { createQuality } from './render/quality';\nimport { createPerf } from './render/perf';")
      .replace("const fps = createFpsOverlay(uiRoot);", "const perf = createPerf(kit.renderer, uiRoot);\n    const fps = createFpsOverlay(uiRoot);")
      .replace("      fx.update(dt * ts);\n      board.update(dt * ts);\n      kinematics.update(dt * ts); // after mixers and the cinematics tweens\n      markers.update(time);\n      lighting.update(time, rig.camera.position.z);\n      rig.update(dt);\n      post.render(dt);\n      fps.frame(dt);",
        "      perf.frameStart();\n      perf.begin('fx'); fx.update(dt * ts); perf.end('fx');\n      perf.begin('mixers'); board.update(dt * ts); perf.end('mixers');\n      perf.begin('kinemat'); kinematics.update(dt * ts); perf.end('kinemat');\n      perf.begin('misc'); markers.update(time); lighting.update(time, rig.camera.position.z); rig.update(dt); perf.end('misc');\n      perf.begin('render'); post.render(dt); perf.end('render');\n      fps.frame(dt);\n      perf.frame();");
    if (!m.includes('perf.frameStart')) throw new Error('could not patch HEAD main.ts');
    writeFileSync(mp, m);
  } else {
    execSync(`rsync -a --exclude ui "${root}/src/" "${benchRoot}/src/" && cd "${root}" && git archive HEAD src/ui | tar -x -C "${benchRoot}"`);
  }
  execSync(`cp "${root}/index.html" "${root}/tsconfig.json" "${root}/vite.config.ts" "${root}/package.json" "${benchRoot}/"`);
  for (const d of ['node_modules', 'public']) if (!existsSync(join(benchRoot, d))) symlinkSync(join(root, d), join(benchRoot, d));
}
const server = await createServer({ root: benchRoot, cacheDir: join('/private/tmp/claude-501', 'vite-cache-bench'), server: { fs: { allow: [root, benchRoot] }, port: 5290, strictPort: false, host: '127.0.0.1', hmr: false, watch: null }, logLevel: 'warn' });
await server.listen();
const base = `http://127.0.0.1:${server.config.server.port}/`;
let browser;
const results = { label, viewport: `${vw}x${vh}`, gpu: null, tiers: {} };
try {
  for (let a = 1; !browser; a++) {
    try {
      browser = await chromium.launch({
        executablePath: BRAVE, headless: true, timeout: 180000,
        args: ['--enable-gpu', '--ignore-gpu-blocklist', '--use-angle=metal', '--enable-features=Vulkan'],
      });
    } catch (e) { if (a >= 3) throw e; log('launch retry', e.message.split('\n')[0]); }
  }
  for (const tier of tiers) {
    const ctx = await browser.newContext({ viewport: { width: vw, height: vh }, deviceScaleFactor: 1 });
    const page = await ctx.newPage();
    const errs = [];
    page.on('pageerror', (e) => errs.push(e.message));
    page.on('console', (m) => { if (m.type() === 'error' && !/favicon/.test(m.text())) errs.push(m.text()); });
    await page.goto(`${base}?perf&debug&quality=${tier}`, { waitUntil: 'load', timeout: 120000 });
    await page.waitForFunction(() => { const b = document.querySelector('.gate-btn'); return !!b && !b.hidden; }, null, { polling: 1000, timeout: 900000 });
    if (!results.gpu) results.gpu = await page.evaluate(() => window.__gpuInfo());
    log(tier, 'ready; gpu =', JSON.stringify(results.gpu));
    const out = (results.tiers[tier] = {});
    const measure = async (name, ms) => {
      await page.evaluate(() => window.__perf.start());
      await page.waitForTimeout(ms);
      out[name] = await page.evaluate(() => window.__perf.stop());
      log(tier, name, JSON.stringify(out[name]));
    };
    // --- scenario 1: start position, idle board (attract stopped, camera at the White seat)
    await gate(page);
    await page.waitForTimeout(1500);
    await page.evaluate(async () => { await window.__bc.attract?.stop(); window.__bc.services.board.syncToFen('rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1'); });
    await page.waitForTimeout(2500);
    if (want('start')) {
      await measure('start', secs * 1000);
      if (shots) await page.screenshot({ path: join(here, 'results', `${label}-${tier}-start-${vw}x${vh}.png`) });
    }
    // --- scenario 2: capture cinematic (hot-seat e4 d5 exd5). Measure from the capture command until the turn settles.
    if (want('capture')) {
      await page.evaluate(() => window.__bc.controller.newGame({ kind: 'hotseat', playerSide: 'w', aiLevel: 'easy' }));
      const play = (f, t) => page.evaluate(([f, t]) => window.__bc.controller.playMove(f, t), [f, t]);
      await page.waitForTimeout(2500);
      await play('e2', 'e4'); await page.waitForTimeout(500);
      await play('d7', 'd5'); await page.waitForTimeout(1800);
      await page.evaluate(() => window.__perf.start());
      const cap = page.evaluate(() => window.__bc.controller.playMove('e4', 'd5'));
      if (shots) { await page.waitForTimeout(2200); await page.screenshot({ path: join(here, 'results', `${label}-${tier}-capture-${vw}x${vh}.png`) }); }
      await Promise.race([cap, page.waitForTimeout(25000)]);
      out.capture = await page.evaluate(() => window.__perf.stop());
      log(tier, 'capture', JSON.stringify(out.capture));
    }
    // --- scenario 3: attract mode (reload to the menu, let the flyover + background duels run)
    if (want('attract')) {
      await page.goto(`${base}?perf&debug&quality=${tier}`, { waitUntil: 'load', timeout: 120000 });
      await page.waitForFunction(() => { const b = document.querySelector('.gate-btn'); return !!b && !b.hidden; }, null, { polling: 1000, timeout: 900000 });
      await gate(page);
      await page.waitForTimeout(3000);
      await measure('attract', Math.max(secs, 8) * 1000);
      if (shots) await page.screenshot({ path: join(here, 'results', `${label}-${tier}-attract-${vw}x${vh}.png`) });
    }
    if (errs.length) out.errors = [...new Set(errs)].slice(0, 5);
    await ctx.close();
  }
} finally {
  clearTimeout(dog);
  await Promise.race([browser?.close().catch(() => {}), new Promise((r) => setTimeout(r, 15000))]);
  await Promise.race([server.close(), new Promise((r) => setTimeout(r, 10000))]);
}
writeFileSync(join(here, 'results', `${label}.json`), JSON.stringify(results, null, 2));
const f = (r, k) => (r ? r[k] : '-');
console.log(`\nGPU: ${results.gpu?.renderer}  viewport ${results.viewport}  label ${label}\n`);
console.log('| tier | scenario | fps | frame ms avg | p95 | max | draw calls | tris (k) | programs | CPU ms: ' + 'fx / mixers / kin / misc / render |');
console.log('|---|---|---|---|---|---|---|---|---|---|');
for (const [tier, o] of Object.entries(results.tiers)) for (const sc of ['start', 'capture', 'attract']) {
  const r = o[sc]; if (!r) continue;
  const s = r.systems;
  console.log(`| ${tier} | ${sc} | ${r.fps} | ${r.frameMsAvg} | ${r.frameMsP95} | ${r.frameMsMax} | ${r.calls} | ${(r.triangles / 1000).toFixed(0)} | ${r.programs} | ${s.fx ?? '-'} / ${s.mixers ?? '-'} / ${s.kinemat ?? '-'} / ${s.misc ?? '-'} / ${s.render ?? '-'} |`);
}

process.exit(0);
