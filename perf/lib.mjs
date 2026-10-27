// Shared launcher for perf/screenshot scripts: ONE Vite server (own port, never 5173) + ONE headless Brave. Close with `await h.close()`.
// Headless Brave on this machine renders with SwiftShader (software GL): see perf/README notes in bench.mjs.
import { chromium } from '@playwright/test';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { createServer } from 'vite';

const here = dirname(fileURLToPath(import.meta.url));
export const root = join(here, '..');
const BRAVE = '/Applications/Brave Browser.app/Contents/MacOS/Brave Browser';

export async function launch({ port = 5291, root: r = root } = {}) {
  const server = await createServer({ root: r, server: { port, strictPort: false, host: '127.0.0.1', hmr: false, watch: null }, logLevel: 'warn' });
  await server.listen();
  const base = `http://127.0.0.1:${server.config.server.port}/`;
  let browser;
  for (let a = 1; !browser; a++) {
    try {
      browser = await chromium.launch({ executablePath: BRAVE, headless: true, timeout: 180000, args: ['--enable-gpu', '--ignore-gpu-blocklist', '--use-angle=metal'] });
    } catch (e) { if (a >= 3) throw e; }
  }
  const open = async ({ width = 1280, height = 720, query = 'debug&quality=low', isMobile = false } = {}) => {
    const ctx = await browser.newContext({ viewport: { width, height }, deviceScaleFactor: 1, isMobile, hasTouch: isMobile });
    const page = await ctx.newPage();
    const errors = [];
    if (process.env.BC_LOG) page.on('console', (m) => console.error('[page]', m.type(), m.text().slice(0, 300)));
    page.on('pageerror', (e) => errors.push(e.message));
    page.on('console', (m) => { if (m.type() === 'error' && !/favicon/.test(m.text())) errors.push(m.text()); });
    await page.goto(`${base}?${query}`, { waitUntil: 'load', timeout: 180000 });
    // polling (not rAF): under software GL a frame can take seconds and rAF-based waits starve
    await page.waitForFunction(() => { const b = document.querySelector('.gate-btn'); return !!b && !b.hidden; }, null, { polling: 1000, timeout: Number(process.env.BC_GATE_MS || 900000) });
    return { ctx, page, errors };
  };
  const close = async () => { clearTimeout(dog); await browser?.close().catch(() => {}); await server.close(); };
  // Watchdog: a script must never leave a browser or server running.
  const dog = setTimeout(async () => { console.error('[perf] watchdog: closing'); await close(); process.exit(2); }, Number(process.env.BC_MAX_MS || 1500000));
  return { open, close, base };
}
