// Loads sandbox/audio.html via a Vite dev server, clicks every SFX button, asserts no console errors.
import { chromium } from '@playwright/test';
import { createServer } from 'vite';

const server = await createServer({ server: { port: 5191, host: '127.0.0.1' }, logLevel: 'error' });
await server.listen();
const browser = await chromium.launch({ channel: 'chrome', args: ['--autoplay-policy=no-user-gesture-required'] });
const errors = [];
try {
  const page = await browser.newPage();
  page.on('console', (m) => { if (m.type() === 'error' && !/Failed to load resource/.test(m.text())) errors.push(m.text()); });
  page.on('pageerror', (e) => errors.push(String(e)));
  await page.goto('http://127.0.0.1:5191/sandbox/audio.html');
  const buttons = page.locator('button');
  const n = await buttons.count();
  if (n < 20) errors.push(`expected many buttons, got ${n}`);
  for (let i = 0; i < n; i++) { await buttons.nth(i).click(); await page.waitForTimeout(40); }
  await page.waitForTimeout(500);
  const hasMusic = await page.evaluate(() => window.audio.hasMusic());
  console.log(`clicked ${n} buttons, hasMusic=${hasMusic}`);
} finally {
  await browser.close();
  await server.close();
}
if (errors.length) { console.error('FAIL', errors); process.exit(1); }
console.log('audio sandbox check passed');
