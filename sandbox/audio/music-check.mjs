// Headless Brave check: music starts on first click, advances, loops; with and without theme.mp3 (?nofile=1 simulates absence).
import { chromium } from '@playwright/test';
import { createServer } from 'vite';

const server = await createServer({ server: { port: 5192, host: '127.0.0.1', strictPort: true }, logLevel: 'error' });
await server.listen();
const browser = await chromium.launch({
  executablePath: '/Applications/Brave Browser.app/Contents/MacOS/Brave Browser', timeout: 180000,
  args: ['--autoplay-policy=no-user-gesture-required'],
});
let failed = false;
try {
  for (const mode of ['file', 'score']) {
    const page = await browser.newPage();
    const errs = [];
    page.on('pageerror', (e) => errs.push(String(e)));
    if (mode === 'score') await page.route('**/audio/theme.mp3', (r) => r.fulfill({ status: 404, body: '' }));
    await page.goto('http://127.0.0.1:5192/sandbox/audio.html');
    await page.locator('button', { hasText: 'ui:click' }).click(); // first gesture
    await page.waitForTimeout(2500);
    const probe = () => page.evaluate(() => window.audio.debug());
    const a = await probe();
    await page.waitForTimeout(1500);
    const b = await probe();
    // duck/unduck, hide/show
    await page.evaluate(() => { document.dispatchEvent(new Event('visibilitychange')); });
    const ok = mode === 'file'
      ? a.kind === 'file' && !a.paused && a.loop && b.currentTime > a.currentTime
      : a.kind === 'score' && a.scoreRunning && b.ctxTime > a.ctxTime && b.gain > 0.05;
    console.log(mode, JSON.stringify({ a, b }), ok ? 'OK' : 'FAIL', errs);
    if (!ok || errs.length) failed = true;
    await page.close();
  }
} finally { await browser.close(); await server.close(); }
process.exit(failed ? 1 : 0);
