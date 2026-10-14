// Frontend-only responsive regression. Uses installed tooling and a mocked auth API.
// Does not connect to, seed, migrate or change any application database.
import { createRequire } from 'node:module';
import { mkdir } from 'node:fs/promises';
import { spawn } from 'node:child_process';
import { createServer } from 'node:net';
import assert from 'node:assert/strict';
const require = createRequire(import.meta.url);
const { chromium } = require(process.env.WHATNOT_PLAYWRIGHT_MODULE);
const socket = createServer();
await new Promise(resolve => socket.listen(0, '127.0.0.1', resolve));
const port = socket.address().port;
await new Promise(resolve => socket.close(resolve));
const origin = `http://127.0.0.1:${port}`;
const server = spawn(process.execPath, ['node_modules/vite/bin/vite.js', 'preview', '--host', '127.0.0.1', '--port', String(port), '--strictPort'], { stdio: 'ignore', windowsHide: true });
let browser;
try {
  let ready = false;
  for (let attempt = 0; attempt < 100; attempt++) {
    if (server.exitCode !== null) throw new Error('Owned preview server exited');
    try { ready = (await fetch(origin)).ok; } catch { /* wait for owned server */ }
    if (ready) break;
    await new Promise(resolve => setTimeout(resolve, 100));
  }
  assert(ready, 'Owned preview server did not become ready');
  browser = await chromium.launch({ headless: true, ...(process.env.WHATNOT_BROWSER_EXECUTABLE ? { executablePath: process.env.WHATNOT_BROWSER_EXECUTABLE } : {}) });
  const page = await browser.newPage();
  const errors = [], requests = [];
  page.on('pageerror', error => errors.push(error.name));
  await page.route('**/*', async route => {
    const url = new URL(route.request().url());
    if (url.origin === origin) return route.continue();
    if (url.pathname.startsWith('/api/v1/')) {
      requests.push({ path: url.pathname, method: route.request().method() });
      const user = { id: 1, name: 'Sample buyer', email: 'scope@example.test', role: 'BUYER' };
      const body = url.pathname === '/api/v1/auth/login'
        ? { access_token: 'browser-sample-token', expires_in: 900, token_type: 'bearer', user }
        : url.pathname === '/api/v1/auth/me' ? user : {};
      return route.fulfill({ status: ['/api/v1/auth/login', '/api/v1/auth/me'].includes(url.pathname) ? 200 : 501, json: body });
    }
    return route.abort(); // External imagery/fonts blocked for an offline layout check.
  });
  const out = 'docs/phase6-scope/screenshots';
  await mkdir(out, { recursive: true });
  async function checkSizes(name) {
    for (const [label, width, height] of [['desktop', 1280, 900], ['tablet', 768, 1024], ['mobile', 390, 844], ['small-mobile', 320, 740]]) {
      await page.setViewportSize({ width, height });
      const region = page.getByRole('region', { name: 'Explore What Not?' });
      for (const vertical of ['Homemade', 'Real Estate', 'Creative Services']) {
        assert(await region.getByRole('heading', { name: vertical, exact: true }).isVisible(), `${name}/${label}: ${vertical}`);
      }
      const dimensions = await page.evaluate(() => ({ body: document.documentElement.scrollWidth, viewport: innerWidth }));
      assert(dimensions.body <= dimensions.viewport + 1, `${name}/${label}: horizontal overflow`);
      const columns = await region.locator('.vertical-grid').evaluate(element => getComputedStyle(element).gridTemplateColumns.split(' ').length);
      assert.equal(columns, width > 1000 ? 3 : width > 520 && name === 'landing' ? 2 : 1, `${name}/${label}: card columns`);
      for (const vertical of ['Real Estate', 'Creative Services']) {
        const card = region.getByRole('article', { name: vertical });
        assert(await card.getByText('Coming soon', { exact: true }).isVisible());
        assert(await card.getByRole('button').isDisabled());
        assert.equal(await card.getByRole('link').count(), 0);
      }
      if (name === 'landing') {
        const toggle = page.getByRole('button', { name: 'Toggle navigation' });
        if (width <= 1000) await toggle.click();
        const nav = page.getByRole('navigation', { name: 'Main navigation' });
        for (const vertical of ['Homemade', 'Real Estate', 'Creative Services']) {
          assert(await nav.getByRole('link', { name: vertical, exact: true }).isVisible());
        }
        if (width <= 1000) {
          await nav.getByRole('link', { name: 'Creative Services', exact: true }).click();
          assert.equal(await toggle.getAttribute('aria-expanded'), 'false');
        }
      }
      await page.screenshot({ path: `${out}/${name}-${label}.png`, fullPage: true });
    }
  }
  await page.goto(origin);
  await checkSizes('landing');
  await page.goto(origin + '/login/buyer');
  await page.getByLabel('Email address').fill('scope@example.test');
  await page.getByLabel('Password', { exact: true }).fill('frontend-sample-only');
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  await page.getByRole('heading', { name: 'Homemade samples', exact: true }).waitFor();
  await checkSizes('buyer');
  await page.getByRole('link', { name: 'Explore Homemade samples', exact: true }).click();
  await page.waitForFunction(() => Math.abs(document.getElementById('homemade-catalogue').getBoundingClientRect().top - 24) <= 2);
  await page.getByRole('button', { name: 'Homemade Food', exact: true }).click();
  await page.getByRole('heading', { name: 'Homemade Laddus', exact: true }).waitFor();
  await page.getByRole('link', { name: 'View product', exact: false }).click();
  assert(await page.getByRole('button', { name: 'Contact unavailable for samples' }).isDisabled());
  assert(await page.getByRole('button', { name: 'Checkout unavailable' }).isDisabled());
  await page.getByRole('button', { name: 'Add to Cart' }).click();
  await page.getByRole('link', { name: 'View cart' }).click();
  assert(await page.getByRole('button', { name: 'Checkout unavailable' }).isDisabled());
  assert(await page.getByText(/Sample catalogue: geography/).isVisible());
  assert(requests.every(request => ['/api/v1/auth/login', '/api/v1/auth/me'].includes(request.path)), 'Unsupported API requested');
  assert.equal(errors.length, 0, 'Browser runtime errors');
  console.log('Frontend scope browser check passed: landing/buyer at 1280, 768, 390 and 320px; navigation, card layouts, sample food/cart, disabled checkout/contact, no unsupported API requests. Authentication responses were mocked; no database was used.');
} finally {
  if (browser) await browser.close();
  if (server.exitCode === null) {
    const closed = new Promise(resolve => server.once('exit', resolve));
    server.kill();
    await closed;
  }
}
