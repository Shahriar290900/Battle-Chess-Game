import { createServer } from 'vite';
import { chromium } from 'playwright';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const server = await createServer({ root, server: { port: 5199, strictPort: false, host: '127.0.0.1' }, logLevel: 'error' });
await server.listen();
const url = server.resolvedUrls.local[0] + 'sandbox/ai.html';
const browser = await chromium.launch({ channel: 'chrome' });
let failed = false;
const fail = (m) => { console.error('FAIL:', m); failed = true; };
try {
  const page = await browser.newPage();
  const errors = [];
  page.on('console', (m) => { if (m.type() === 'error' && !/404/.test(m.text()) || m.type() === 'warning' && /\[ai\]/.test(m.text())) errors.push(m.text()); });
  page.on('response', (r) => { if (r.status() >= 400 && !/favicon/.test(r.url())) errors.push(`HTTP ${r.status()} ${r.url()}`); });
  page.on('pageerror', (e) => errors.push(String(e)));
  await page.goto(url);
  await page.waitForFunction(() => window.__aiResult?.done, null, { timeout: 120000 });
  const r = await page.evaluate(() => window.__aiResult);
  if (r.error) fail(r.error);
  else {
    for (const x of r.results) console.log(x.level.padEnd(7), x.move.padEnd(8), x.legal ? 'legal' : 'ILLEGAL', x.ms + 'ms');
    if (r.results.length !== 12) fail('expected 12 results');
    if (r.results.some((x) => !x.legal)) fail('illegal move');
    if (!r.cancelled) fail('cancel did not reject with cancelled');
    if (!r.afterCancel) fail('no move after cancel');
    if (r.results.some((x) => x.ms < 550)) fail('response faster than min time');
  }
  // prove the real worker (not fallback) was used: no [ai] warnings
  if (errors.length) fail('console errors/warnings: ' + errors.join(' | '));
} finally {
  await browser.close();
  await server.close();
}
console.log(failed ? 'CHECK FAILED' : 'CHECK PASSED');
process.exit(failed ? 1 : 0);
