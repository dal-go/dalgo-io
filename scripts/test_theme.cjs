const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const { join } = require('node:path');
const { test } = require('node:test');
const { runInNewContext } = require('node:vm');

const source = readFileSync(join(__dirname, '../public/theme.js'), 'utf8');
function theme({ saved = null, dark = false, storageDenied = false, mediaDenied = false } = {}) {
  const events = {};
  const control = { value: '', addEventListener(name, fn) { this[name] = fn; } };
  const label = { hidden: true };
  const media = { matches: dark, addEventListener(name, fn) { this[name] = fn; } };
  const document = {
    readyState: 'complete', documentElement: { dataset: {} },
    querySelectorAll(selector) { return selector === '[data-theme-switch]' ? [control] : [label]; },
    dispatchEvent(event) { this.lastEvent = event; },
  };
  const window = {
    document,
    localStorage: {
      getItem() { if (storageDenied) throw Error('denied'); return saved; },
      setItem(key, value) { if (storageDenied) throw Error('denied'); saved = value; },
    },
    matchMedia() { if (mediaDenied) throw Error('unsupported'); return media; },
    addEventListener(name, fn) { events[name] = fn; },
    CustomEvent: class { constructor(name, options) { this.type = name; this.detail = options.detail; } },
  };
  runInNewContext(source, { window });
  return { window, document, media, control, label, events, stored: () => saved };
}

test('saved choice takes priority over the system theme', () => {
  assert.equal(theme({ saved: 'light', dark: true }).document.documentElement.dataset.theme, 'light');
  assert.equal(theme({ saved: 'dark' }).document.documentElement.dataset.theme, 'dark');
});
test('system preference is used without a saved choice; absent support falls back to light', () => {
  assert.equal(theme({ dark: true }).document.documentElement.dataset.theme, 'dark');
  assert.equal(theme({ mediaDenied: true }).document.documentElement.dataset.theme, 'light');
  assert.equal(theme({ saved: 'invalid', dark: true }).window.DALgoTheme.getPreference(), 'system');
});
test('manual choices apply and persist even when the system differs', () => {
  const t = theme({ dark: true });
  t.control.value = 'light'; t.control.change();
  assert.equal(t.document.documentElement.dataset.theme, 'light');
  assert.equal(t.stored(), 'light');
  assert.equal(t.label.hidden, false);
  assert.equal(t.document.lastEvent.type, 'dalgo-theme-change');
});
test('storage denial keeps the in-page switch working', () => {
  const t = theme({ storageDenied: true });
  t.window.DALgoTheme.setPreference('dark');
  assert.equal(t.document.documentElement.dataset.theme, 'dark');
});
test('OS changes affect only System mode', () => {
  const t = theme(); t.media.matches = true; t.media.change();
  assert.equal(t.document.documentElement.dataset.theme, 'dark');
  t.window.DALgoTheme.setPreference('light'); t.media.change();
  assert.equal(t.document.documentElement.dataset.theme, 'light');
  t.window.DALgoTheme.setPreference('system');
  assert.equal(t.document.documentElement.dataset.theme, 'dark');
});
test('cross-tab preference changes update the page', () => {
  const t = theme(); t.events.storage({ key: 'dalgo.theme', newValue: 'dark' });
  assert.equal(t.document.documentElement.dataset.theme, 'dark');
  t.events.storage({ key: 'unrelated', newValue: 'light' });
  assert.equal(t.document.documentElement.dataset.theme, 'dark');
});
