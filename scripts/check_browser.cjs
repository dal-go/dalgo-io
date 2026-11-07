// CI-owned loopback server and browser; finally closes both, CI kills on timeout.
const assert = require('node:assert/strict');
const { createServer } = require('node:http');
const { readFile, mkdir } = require('node:fs/promises');
const { resolve, extname, join } = require('node:path');
const { chromium } = require(resolve(process.env.DALGO_PLAYWRIGHT_DIR, 'node_modules/playwright'));
const root = resolve(__dirname, '../public');
const output = process.env.DALGO_SCREENSHOTS || join(process.env.RUNNER_TEMP, 'dalgo-screenshots');
const mime = { '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css', '.svg': 'image/svg+xml', '.json': 'application/json', '.webp': 'image/webp', '.txt': 'text/plain', '.xml': 'application/xml' };
const server = createServer(async (request, response) => {
  try {
    let pathname = decodeURIComponent(new URL(request.url, 'http://localhost').pathname);
    if (pathname.endsWith('/')) pathname += 'index.html';
    const file = resolve(root, '.' + pathname);
    if (!file.startsWith(root + '/')) throw Error('Invalid path');
    const data = await readFile(file);
    response.writeHead(200, { 'Content-Type': mime[extname(file)] || 'application/octet-stream' });
    response.end(data);
  } catch {
    response.writeHead(404); response.end('Not found');
  }
});

(async () => {
  let browser;
  try {
    await new Promise((done, reject) => { server.once('error', reject); server.listen(0, '127.0.0.1', done); });
    const origin = `http://127.0.0.1:${server.address().port}`;
    browser = await chromium.launch();
    await mkdir(output, { recursive: true });
    const context = await browser.newContext({ colorScheme: 'dark', viewport: { width: 1280, height: 900 } });
    await context.route('**/*', (route) => route.request().url().startsWith(origin + '/') ? route.continue() : route.fulfill({ body: '', status: 200 }));
    const page = await context.newPage();
    const errors = []; page.on('pageerror', (error) => errors.push(error.message));
    for (const route of ['/', '/adapters/', '/go/', '/typescript/', '/quickstart/', '/privacy/', '/collections/', '/ru/adapters/', '/ru/go/']) {
      const response = await page.goto(origin + route);
      assert.equal(response.status(), 200, route);
      await page.locator('[data-theme-control]:not([hidden])').waitFor();
      assert.equal(await page.locator('.AppHeader-nav a').count(), 4, route);
      assert.equal(await page.locator('h1').count(), 1, route);
      assert.equal(await page.locator('html').getAttribute('data-theme'), 'dark', route);
      await page.locator('[data-theme-switch]').selectOption('light');
      const light = await page.evaluate(() => getComputedStyle(document.body).backgroundColor);
      await page.locator('[data-theme-switch]').selectOption('dark');
      const dark = await page.evaluate(() => getComputedStyle(document.body).backgroundColor);
      assert.notEqual(light, dark, `theme palette ${route}`);
      if (route === '/') {
        await page.locator('#cy canvas').first().waitFor();
        // A real canvas image must change when the graph palette changes.
        await page.locator('[data-theme-switch]').selectOption('light');
        await page.evaluate(() => new Promise(requestAnimationFrame));
        const before = await page.locator('#cy canvas').evaluateAll((canvases) => canvases.map((canvas) => canvas.toDataURL()));
        await page.locator('[data-theme-switch]').selectOption('dark');
        await page.evaluate(() => new Promise((done) => requestAnimationFrame(() => requestAnimationFrame(done))));
        assert.notDeepEqual(before, await page.locator('#cy canvas').evaluateAll((canvases) => canvases.map((canvas) => canvas.toDataURL())), 'graph canvas follows theme');
        await page.screenshot({ path: join(output, 'home-dark.png'), fullPage: true });
      }
      if (route === '/adapters/') {
        assert.deepEqual(await page.getByRole('columnheader').allTextContents(), ['Adapter', 'Go', 'TypeScript']);
        assert.equal(await page.locator('.adapter-table tbody tr').count(), 49);
        assert.match(await page.getByRole('row').filter({ has: page.getByRole('rowheader', { name: 'Oracle', exact: true }) }).innerText(), /Not implemented/);
      }
      if (route.startsWith('/ru/')) assert.equal(await page.locator('.AppHeader-brand').getAttribute('href'), '/ru/');
    }
    await page.goto(origin + '/collections/');
    const tabs = page.getByRole('tab');
    await tabs.first().focus(); await page.keyboard.press('End');
    assert.equal(await tabs.last().getAttribute('aria-selected'), 'true');
    assert.equal(await tabs.first().getAttribute('tabindex'), '-1');
    await page.keyboard.press('Home');
    assert.equal(await tabs.first().getAttribute('aria-selected'), 'true');
    await page.keyboard.press('ArrowLeft');
    assert.equal(await tabs.last().getAttribute('aria-selected'), 'true');
    await page.keyboard.press('ArrowRight');
    assert.equal(await tabs.first().getAttribute('aria-selected'), 'true');
    await page.locator('[data-theme-switch]').selectOption('light');
    await page.reload();
    assert.equal(await page.locator('html').getAttribute('data-theme'), 'light', 'saved light overrides dark system');
    await page.locator('[data-theme-switch]').selectOption('system');
    assert.equal(await page.locator('html').getAttribute('data-theme'), 'dark');
    await page.emulateMedia({ colorScheme: 'light' });
    await page.waitForFunction(() => document.documentElement.dataset.theme === 'light');
    for (const width of [375, 1280]) {
      await page.setViewportSize({ width, height: 900 });
      for (const route of ['/', '/adapters/', '/quickstart/', '/ru/adapters/']) {
        await page.goto(origin + route);
        const overflow = await page.evaluate(() => {
          const elements = Array.from(document.querySelectorAll('body *')).filter((element) => {
            const box = element.getBoundingClientRect();
            return box.width && (box.right > innerWidth + 1 || box.left < -1) && getComputedStyle(element).position !== 'fixed';
          }).slice(0, 12).map((element) => ({ tag: element.tagName, className: element.className, width: element.getBoundingClientRect().width }));
          return { pageWidth: document.documentElement.scrollWidth, viewportWidth: innerWidth, elements };
        });
        assert.ok(overflow.pageWidth <= overflow.viewportWidth + 1, `no page overflow: ${width} ${route}: ${JSON.stringify(overflow)}`);
        assert.equal(await page.locator('.AppHeader-nav a:visible').count(), 4);
        await page.screenshot({ path: join(output, `${width}-${route.replaceAll('/', '_') || 'home'}.png`), fullPage: true });
      }
    }
    for (const route of ['/llms.txt', '/llms-full.txt', '/robots.txt', '/sitemap.xml']) {
      const response = await page.goto(origin + route);
      assert.equal(response.status(), 200, route);
      assert.match(await response.text(), /dalgo\.io/, route);
    }
    const robots = await (await page.goto(origin + '/robots.txt')).text();
    assert.match(robots, /User-agent:\s*\*/);
    assert.match(robots, /Allow:\s*\//);
    assert.doesNotMatch(robots, /Disallow:\s*\//);
    assert.match(robots, /Sitemap:\s*https:\/\/dalgo\.io\/sitemap\.xml/);
    for (const route of ['/', '/ru/', '/go/', '/ru/go/', '/privacy/', '/tugql/', '/tugql/examples/', '/articles/']) {
      await page.goto(origin + route);
      assert.equal(await page.locator('link[rel="canonical"]').getAttribute('href'), 'https://dalgo.io' + route, route);
      const description = await page.locator('meta[name="description"]').getAttribute('content');
      assert.ok(description && [...description].length >= 120 && [...description].length <= 160, `${route} description ${description && description.length}`);
    }
    await page.goto(origin + '/');
    const homeLd = await page.locator('script[type="application/ld+json"]').textContent();
    assert.match(homeLd, /"@type":"Organization"/);
    assert.match(homeLd, /"@type":"WebSite"/);
    assert.match(homeLd, /"@type":"SoftwareSourceCode"/);
    assert.match(homeLd, /https:\/\/github\.com\/dal-go\/dalgo"/);
    assert.match(homeLd, /https:\/\/github\.com\/dal-go\/dalgo-js"/);
    await page.goto(origin + '/go/');
    assert.match(await page.locator('script[type="application/ld+json"]').textContent(), /BreadcrumbList/);
    await page.goto(origin + '/ru/');
    const russian = await page.locator('link[rel="alternate"]').evaluateAll((links) => links.map((link) => link.hreflang + ' ' + link.href));
    assert.ok(russian.includes('ru https://dalgo.io/ru/'));
    assert.ok(russian.includes('en https://dalgo.io/'));
    assert.deepEqual(errors, [], 'no uncaught browser exceptions');
    console.log('Browser acceptance passed: routes, themes, graph, keyboard tabs and mobile layout.');
    await context.close();
  } finally {
    if (browser) await browser.close();
    await new Promise((done) => server.close(done));
  }
})().catch((error) => { console.error(error); process.exitCode = 1; });
