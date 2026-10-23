// Google Analytics 4 with Consent Mode and a consent banner.
// EEA/UK (and GB/EFTA) visitors: gtag.js is never fetched and nothing is sent to
// Google until the visitor chooses "Accept". Elsewhere it loads normally.
// Region comes from one Cloudflare lookup (/cdn-cgi/trace); if it fails the
// visitor is treated as gated. Stored choice: localStorage "dalgo.analytics-consent.v1".
(function () {
  "use strict";
  var GA_ID = "G-DLR3FRM1DZ";
  var KEY = "dalgo.analytics-consent.v1";
  var GATED = ["AT","BE","BG","HR","CY","CZ","DK","EE","FI","FR","DE","GR","HU","IE","IT","LV","LT","LU","MT","NL","PL","PT","RO","SK","SI","ES","SE","IS","LI","NO","CH","GB","GI","JE","GG","IM","RE","GP","MQ","GF","YT","MF","AX","XX","T1"];
  var loaded = false, banner = null, opener = null, decided = false;

  function stored() {
    try { var v = localStorage.getItem(KEY); return v === "granted" || v === "denied" ? v : null; } catch (e) { return null; }
  }
  function store(v) { try { localStorage.setItem(KEY, v); } catch (e) {} }

  function load() {
    window["ga-disable-" + GA_ID] = false;
    window.dataLayer = window.dataLayer || [];
    if (!window.gtag) window.gtag = function () { window.dataLayer.push(arguments); };
    if (loaded) { window.gtag("consent", "update", { analytics_storage: "granted" }); return; }
    loaded = true;
    window.gtag("consent", "default", { analytics_storage: "denied", ad_storage: "denied", ad_user_data: "denied", ad_personalization: "denied" });
    window.gtag("consent", "update", { analytics_storage: "granted" });
    window.gtag("js", new Date());
    window.gtag("config", GA_ID, { allow_google_signals: false, allow_ad_personalization_signals: false });
    var s = document.createElement("script");
    s.async = true;
    s.src = "https://www.googletagmanager.com/gtag/js?id=" + GA_ID;
    document.head.appendChild(s);
  }

  function expireCookies() {
    var host = location.hostname, labels = host.split(".");
    var scopes = [""], names = [host];
    if (labels.length > 2 && !/^[\d.]+$/.test(host)) names.push(labels.slice(-2).join("."));
    names.forEach(function (d) { scopes.push("; domain=" + d, "; domain=." + d); });
    document.cookie.split(";").forEach(function (c) {
      var n = c.split("=")[0].trim();
      if (n !== "_ga" && n.indexOf("_ga_") !== 0) return;
      scopes.forEach(function (sc) { document.cookie = n + "=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/" + sc; });
    });
  }

  function withdraw() {
    if (loaded) window.gtag("consent", "update", { analytics_storage: "denied" });
    window["ga-disable-" + GA_ID] = true;
    expireCookies();
  }

  function hide() { if (banner && banner.parentNode) banner.parentNode.removeChild(banner); banner = null; }

  function decide(v) {
    decided = true;
    store(v);
    hide();
    if (v === "granted") load(); else withdraw();
    if (opener) { opener.focus(); opener = null; }
  }

  function btn(label, v, id) {
    var b = document.createElement("button");
    b.type = "button"; b.id = id; b.textContent = label;
    b.addEventListener("click", function () { decide(v); });
    return b;
  }

  function show(focus) {
    if (banner) { if (focus) banner.focus(); return; }
    banner = document.createElement("section");
    banner.id = "ga-consent-banner";
    banner.setAttribute("role", "region");
    banner.setAttribute("aria-label", "Analytics choice");
    banner.tabIndex = -1;
    var p = document.createElement("p");
    p.appendChild(document.createTextNode("We’d like to use Google Analytics to count visits. It loads and sets cookies only if you accept. "));
    var a = document.createElement("a");
    a.href = "/privacy/#analytics"; a.textContent = "Privacy notice";
    p.appendChild(a);
    var row = document.createElement("div");
    row.className = "ga-consent-actions";
    row.appendChild(btn("Decline", "denied", "ga-decline"));
    row.appendChild(btn("Accept", "granted", "ga-accept"));
    banner.appendChild(p); banner.appendChild(row);
    document.body.appendChild(banner);
    if (focus) banner.focus();
  }

  function wireOpeners() {
    var els = document.querySelectorAll("[data-analytics-choices]");
    for (var i = 0; i < els.length; i++) {
      els[i].hidden = false;
      els[i].addEventListener("click", function () { opener = this; show(true); });
    }
  }

  function start() {
    wireOpeners();
    var c = stored();
    if (c === "denied") { withdraw(); return; }
    fetch("/cdn-cgi/trace").then(function (r) { return r.text(); }).then(function (t) {
      var m = /(?:^|\n)loc=([A-Z]{2})/.exec(t);
      return !(m && GATED.indexOf(m[1]) === -1); // unknown region (XX, T1, no match) is gated
    }, function () { return true; }).then(function (gated) {
      if (decided) return; // the visitor chose while the lookup ran; decide() already applied it
      var now = stored();
      if (now === "denied") return;
      if (now === "granted" || !gated) load(); else show(false);
    });
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start); else start();
})();
