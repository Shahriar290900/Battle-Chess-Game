// Headless Brave check: every manifest file fetches + decodes, every key plays without console errors.
// Own Vite port (5192); never touches other browser processes — closes only the instance it launched.
import { chromium } from '@playwright/test';
import { createServer } from 'vite';

const BRAVE = '/Applications/Brave Browser.app/Contents/MacOS/Brave Browser';
const server = await createServer({ server: { port: 5192, host: '127.0.0.1', strictPort: true }, logLevel: 'error' });
await server.listen();
const browser = await chromium.launch({ executablePath: BRAVE, headless: true, timeout: 180000, args: ['--autoplay-policy=no-user-gesture-required'] });
const errors = [];
try {
  const page = await browser.newPage();
  // Resource 404s are judged by URL below (theme.mp3 is gitignored and favicon is absent in the sandbox).
  page.on('console', (m) => { if (['error', 'warning'].includes(m.type()) && !/Failed to load resource/.test(m.text())) errors.push(`${m.type()}: ${m.text()}`); });
  page.on('response', (r) => { if (r.status() >= 400 && !/theme\.mp3|favicon/.test(r.url())) errors.push(`HTTP ${r.status()} ${r.url()}`); });
  page.on('pageerror', (e) => errors.push(String(e)));
  await page.goto('http://127.0.0.1:5192/sandbox/audio.html');
  await page.waitForSelector('#app h3');
  const probe = await page.evaluate(() => window.sfxProbe());
  console.log('probe', JSON.stringify({ ...probe, failed: probe.failed.length }));
  if (probe.failed.length) errors.push(...probe.failed);
  // play every key (and the legacy SfxName buttons), after unlock
  const buttons = page.locator('button');
  const n = await buttons.count();
  for (let i = 0; i < n; i++) { await buttons.nth(i).click(); await page.waitForTimeout(25); }
  await page.waitForTimeout(800);
  // The sample player (not just the probe) must have fetched a cinematic hit on demand.
  const page2 = await browser.newPage();
  await page2.goto('http://127.0.0.1:5192/sandbox/audio.html');
  await page2.waitForSelector('#app h3');
  await page2.getByRole('button', { name: /^hit:rook:emberhold/ }).click();
  await page2.waitForTimeout(1500);
  await page2.getByRole('button', { name: /^hit:rook:emberhold/ }).click();
  const fetched = await page2.evaluate(() => performance.getEntriesByType('resource').filter((e) => /hit_rook_emberhold__\d\.mp3/.test(e.name)).length);
  console.log('on-demand hit fetches:', fetched);
  if (!fetched) errors.push('sample player never fetched hit_rook_emberhold');
  const st = await page.evaluate(() => window.audio.debug());
  console.log(`clicked ${n} buttons; ctx=${st.state}`);
} finally {
  await browser.close();
  await server.close();
}
if (errors.length) { console.error('FAIL', errors.slice(0, 20)); process.exit(1); }
console.log('sfx check passed');
