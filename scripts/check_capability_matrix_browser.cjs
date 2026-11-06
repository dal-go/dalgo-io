/* Run only in the coordinator's contained browser namespace against generated public/. */
const assert = require('node:assert/strict');
const { join } = require('node:path');

async function checkCapabilityMatrix(browser, base, output) {
    for (const locale of ['', 'ru/']) {
      const context = await browser.newContext({ viewport: { width: 375, height: 812 } });
      await context.route('**/*', route => route.request().url().startsWith(base + '/') ? route.continue() : route.fulfill({ body: '', status: 200 }));
      const page = await context.newPage();
      await page.goto(base + '/' + locale + 'adapters/');
      // Fresh contexts have no stored decision; the failed local region lookup
      // intentionally shows analytics.js's actual consent banner.
      await page.locator('#ga-decline').waitFor({ state: 'visible' });
      await page.locator('#ga-decline').click();
      await page.locator('#ga-consent-banner').waitFor({ state: 'detached' });
      assert.equal(await page.evaluate(() => localStorage.getItem('dalgo.analytics-consent.v1')), 'denied');
      const rows = page.locator('details.cap-adapter');
      assert.ok(await rows.count() >= 56);
      const first = rows.nth(0), second = rows.nth(1), third = rows.nth(2);
      await first.locator('summary').click();
      await second.locator('summary').click();
      assert.equal(await first.getAttribute('open'), '');
      assert.equal(await second.getAttribute('open'), '');
      await third.locator('summary').focus();
      await page.keyboard.press('Enter');
      assert.equal(await third.getAttribute('open'), '');
      await page.keyboard.press('Space');
      assert.equal(await third.getAttribute('open'), null);
      assert.equal(await first.getAttribute('open'), '');
      assert.equal(await second.getAttribute('open'), '');
      for (const width of [375, 1280]) {
      await page.setViewportSize({ width, height: 900 });
      if (width === 375) {
        const region = first.locator('.cap-table-scroll');
        assert.equal(await region.getAttribute('tabindex'), '0');
        assert.ok(await region.getAttribute('aria-labelledby'));
        await region.focus();
        await page.keyboard.press('ArrowRight');
        await page.waitForFunction(() => document.querySelector('details[open] .cap-table-scroll').scrollLeft > 0);
        const scroll = await region.evaluate(element => ({ viewport: element.clientWidth, content: element.scrollWidth, outline: getComputedStyle(element).outlineWidth }));
        assert.ok(scroll.content >= 800 && scroll.viewport < scroll.content, JSON.stringify(scroll));
        assert.ok(parseFloat(scroll.outline) >= 2, 'keyboard scroll region has a visible focus indicator');
        await region.evaluate(element => { element.scrollLeft = 0; });
      }
      const palettes = [];
      for (const mode of ['light', 'dark']) {
        await page.locator('[data-theme-control] select, .theme-control select').first().selectOption(mode);
        await page.waitForFunction(expected => document.documentElement.dataset.theme === expected, mode);
        const measurements = await page.evaluate(() => ({ width: innerWidth, scroll: document.documentElement.scrollWidth, backgrounds: getComputedStyle(document.querySelector('.cap-table thead')).backgroundColor, ink: getComputedStyle(document.querySelector('.cap-status')).color, headings: [...document.querySelector('details[open] thead').querySelectorAll('th')].map(x => x.textContent) }));
        assert.ok(measurements.scroll <= measurements.width + 1, JSON.stringify(measurements));
        assert.equal(measurements.headings.length, 4);
        assert.ok(measurements.headings.some(text => text.includes('browser') || text.includes('браузер')));
        assert.ok(measurements.headings.some(text => text.includes('Node.js')));
        assert.notEqual(measurements.backgrounds, measurements.ink);
        palettes.push(measurements.backgrounds);
        if (output) {
          await first.screenshot({ path: join(output, `matrix-${locale ? 'ru' : 'en'}-${width}-${mode}-row1.png`) });
          await second.screenshot({ path: join(output, `matrix-${locale ? 'ru' : 'en'}-${width}-${mode}-row2.png`) });
          await first.locator('summary').scrollIntoViewIfNeeded();
          await page.screenshot({ path: join(output, `matrix-${locale ? 'ru' : 'en'}-${width}-${mode}-viewport.png`) });
          if (width === 375) {
            const region = first.locator('.cap-table-scroll');
            await region.evaluate(element => { element.scrollLeft = element.scrollWidth; });
            assert.ok(await region.evaluate(element => element.scrollLeft > 0));
            await region.screenshot({ path: join(output, `matrix-${locale ? 'ru' : 'en'}-${width}-${mode}-scrolled.png`) });
            await region.evaluate(element => { element.scrollLeft = 0; });
          }
        }
      }
      assert.notEqual(palettes[0], palettes[1], 'matrix header palette changes with theme');
      }
      await context.close();
    }
    const noScript = await browser.newContext({ javaScriptEnabled: false, viewport: { width: 375, height: 812 } });
    const page = await noScript.newPage();
    await page.goto(base + '/adapters/');
    await page.locator('details.cap-adapter summary').first().focus();
    await page.keyboard.press('Enter');
    assert.equal(await page.locator('details.cap-adapter').first().getAttribute('open'), '');
    await noScript.close();
    console.log('Capability matrix: EN/RU, independent rows, native keyboard/no-JS, light/dark, 375px PASS');
}

module.exports = { checkCapabilityMatrix };
