(function (window) {
  'use strict';
  var document = window.document;
  var key = 'dalgo.theme';
  var allowed = ['system', 'light', 'dark'];
  var preference = 'system';
  var media;
  try {
    var saved = window.localStorage.getItem(key);
    if (allowed.indexOf(saved) >= 0) preference = saved;
  } catch (_) { /* The in-page choice still works when storage is unavailable. */ }
  try { media = window.matchMedia('(prefers-color-scheme: dark)'); } catch (_) { /* Light fallback. */ }
  function apply() {
    var theme = preference === 'system' ? (media && media.matches ? 'dark' : 'light') : preference;
    document.documentElement.dataset.theme = theme;
    document.querySelectorAll('[data-theme-switch]').forEach(function (control) { control.value = preference; });
    document.querySelectorAll('[data-theme-control]').forEach(function (control) { control.hidden = false; });
    document.dispatchEvent(new window.CustomEvent('dalgo-theme-change', { detail: { theme: theme, preference: preference } }));
  }
  function setPreference(next) {
    if (allowed.indexOf(next) < 0) return;
    preference = next;
    try { window.localStorage.setItem(key, next); } catch (_) { /* Keep the current in-memory preference. */ }
    apply();
  }
  window.DALgoTheme = { setPreference: setPreference, getPreference: function () { return preference; } };
  apply();
  function init() {
    document.querySelectorAll('[data-theme-switch]').forEach(function (control) {
      control.addEventListener('change', function () { setPreference(control.value); });
    });
    apply();
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init, { once: true });
  else init();
  if (media) {
    var changed = function () { if (preference === 'system') apply(); };
    if (media.addEventListener) media.addEventListener('change', changed);
    else if (media.addListener) media.addListener(changed);
  }
  window.addEventListener('storage', function (event) {
    if (event.key !== key) return;
    preference = allowed.indexOf(event.newValue) >= 0 ? event.newValue : 'system';
    apply();
  });
}(window));
