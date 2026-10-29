#!/usr/bin/env python3
"""Render the localized landing pages and the sitemap.

Sources (all under content/site/):
  index.template.html  the page, with {{key}} placeholders for every string
  en.json, ru.json     one catalog per locale (same keys; --check enforces it)
  adapters.json        adapter names, URLs and import paths (shared by locales)
  video.json           the film slot: one switch plus a YouTube id per locale

Outputs (committed, like the generated articles):
  public/index.html       English, served at /
  public/ru/index.html    Russian, served at /ru/
  public/sitemap.xml      every page, with en/ru alternates for the landing pair

`--check` fails when the committed outputs drift from the sources. The site
still deploys public/ with no production build step.
"""

from __future__ import annotations

import argparse
import difflib
import html
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "content" / "site"
PUBLIC = ROOT / "public"
SITE = "https://dalgo.io"

LOCALES = ("en", "ru")
DEFAULT_LOCALE = "en"
LOCALE_INFO = {
    "en": {"og": "en_US", "prefix": "/", "out": PUBLIC / "index.html", "switch": "EN"},
    "ru": {"og": "ru_RU", "prefix": "/ru/", "out": PUBLIC / "ru" / "index.html", "switch": "RU"},
}
PLACEHOLDER = re.compile(r"\{\{([A-Za-z0-9_.]+)\}\}")
YOUTUBE_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")

PLAY_ICON = (
    '<svg viewBox="0 0 68 48" width="68" height="48" aria-hidden="true" focusable="false">'
    '<rect width="68" height="48" rx="12" fill="#0d1117" fill-opacity=".85"/>'
    '<path d="M27 34V14l18 10-18 10Z" fill="#fff"/></svg>'
)


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def flatten(data: dict, prefix: str = "") -> dict[str, str]:
    out: dict[str, str] = {}
    for key, value in data.items():
        if isinstance(value, dict):
            out.update(flatten(value, f"{prefix}{key}."))
        else:
            out[f"{prefix}{key}"] = value
    return out


def load_catalogs() -> dict[str, dict]:
    catalogs = {loc: load_json(SRC / f"{loc}.json") for loc in LOCALES}
    base = set(flatten(catalogs[DEFAULT_LOCALE]))
    for loc in LOCALES:
        keys = set(flatten(catalogs[loc]))
        if keys != base:
            raise SystemExit(
                f"{loc}.json keys differ from {DEFAULT_LOCALE}.json: "
                f"missing {sorted(base - keys)}, extra {sorted(keys - base)}"
            )
    return catalogs


def check_attribute_safe(loc: str, flat: dict[str, str]) -> None:
    for key, value in flat.items():
        if (key.endswith("_label") or key.startswith("meta.")) and re.search(r'["<>]', value):
            raise SystemExit(f"{loc}.json {key}: attribute text must not contain quotes or tags")


def alternates() -> str:
    lines = [
        f'<link rel="alternate" hreflang="{loc}" href="{SITE}{LOCALE_INFO[loc]["prefix"]}" />'
        for loc in LOCALES
    ]
    lines.append(f'<link rel="alternate" hreflang="x-default" href="{SITE}{LOCALE_INFO[DEFAULT_LOCALE]["prefix"]}" />')
    return "\n".join(lines)


def lang_switch(loc: str, label: str) -> str:
    parts = []
    for other in LOCALES:
        info = LOCALE_INFO[other]
        if other == loc:
            parts.append(f'<span class="lang-switch-item" aria-current="true" lang="{other}">{info["switch"]}</span>')
        else:
            parts.append(
                f'<a class="lang-switch-item" href="{info["prefix"]}" hreflang="{other}" lang="{other}" data-lang-link>{info["switch"]}</a>'
            )
    return f'<nav class="lang-switch" aria-label="{label}">{"".join(parts)}</nav>'


def adapter_cards(loc: str, catalog: dict, adapters: dict) -> str:
    core_icon = (
        '<svg class="octicon" viewBox="0 0 16 16" width="14" height="14" aria-hidden="true">'
        '<path fill="currentColor" d="M8 0a8.2 8.2 0 0 1 .701.031C13.444.443 16 4.273 16 8c0 .43-.025.85-.075 1.255A8 8 0 1 1 8 0Z"/></svg>\n            '
    )
    items = []
    for card in adapters["cards"]:
        text = catalog["adapters"][card["id"]]
        cls = "Box adapter adapter-core" if card.get("core") else "Box adapter"
        icon = core_icon if card.get("core") else ""
        items.append(
            f"""      <li>
        <a class="{cls}" href="{card["url"]}" rel="noopener">
          <span class="adapter-kind">
            {icon}{text["kind"]}
          </span>
          <h3>{card["name"]}</h3>
          <p>{text["desc"]}</p>
          <span class="adapter-go">{card["gopath"]}</span>
        </a>
      </li>"""
        )
    label = html.escape(catalog["adapters.cards_label"], quote=True)
    return f'    <ul class="adapter-grid" role="list" aria-label="{label}">\n' + "\n\n".join(items) + "\n    </ul>"


def adapter_more(catalog: dict, adapters: dict) -> str:
    rows = "\n".join(
        f'        <li><a href="{item["url"]}" rel="noopener"><strong>{item["name"]}</strong></a> — {catalog["adapters_more"][item["id"]]}</li>'
        for item in adapters["more"]
    )
    return (
        '    <aside class="Box companion adapters-more">\n'
        f'      <h3>{catalog["adapters.more_title"]}</h3>\n'
        f'      <p>{catalog["adapters.more_lead"]}</p>\n'
        f'      <ul role="list">\n{rows}\n      </ul>\n'
        "    </aside>"
    )


def video_section(loc: str, catalog: dict, video: dict) -> str:
    """Empty unless video.json enables the slot and both locales have an id."""
    if not video.get("enabled"):
        return ""
    for each in LOCALES:
        vid = video["locales"][each]["youtubeId"]
        if not YOUTUBE_ID.match(vid):
            raise SystemExit(f"video.json: enabled, but locales.{each}.youtubeId is not an 11-character YouTube id")
        if not re.fullmatch(r"\d{1,2}:\d{2}", video["locales"][each].get("duration", "")):
            raise SystemExit(f"video.json: enabled, but locales.{each}.duration is not m:ss")
    cfg = video["locales"][loc]
    title = html.escape(re.sub(r"<[^>]+>", "", catalog["video.title"]), quote=True)
    play = html.escape(catalog["video.play"].replace("{duration}", cfg["duration"]), quote=True)
    return f"""<!-- ============================ FILM ============================ -->
<section id="film" class="section">
  <div class="container">
    <header class="section-head">
      <span class="section-eyebrow">{catalog["video.eyebrow"]}</span>
      <h2 class="section-title">{catalog["video.title"]}</h2>
      <p class="section-kicker">{catalog["video.kicker"]}</p>
    </header>
    <div class="film" data-film data-video-id="{cfg["youtubeId"]}" data-video-title="{title}">
      <button class="film-play" type="button" lang="{loc}" aria-label="{play}: {title}">
        <img src="{cfg["poster"]}" width="{cfg["width"]}" height="{cfg["height"]}" alt="" decoding="async" />
        <span class="film-play-icon">{PLAY_ICON}</span>
        <span class="film-duration" aria-hidden="true">{cfg["duration"]}</span>
      </button>
    </div>
    <p class="film-note">{catalog["video.note"]}</p>
  </div>
</section>
<script src="/video.js" defer></script>"""


def render_page(loc: str, template: str, catalogs: dict, adapters: dict, video: dict) -> str:
    catalog = catalogs[loc]
    flat = flatten(catalog)
    check_attribute_safe(loc, flat)
    info = LOCALE_INFO[loc]
    other = next(x for x in LOCALES if x != loc)
    cy_labels = json.dumps(catalog["cy"], ensure_ascii=False)
    computed = {
        "lang": loc,
        "canonical": SITE + info["prefix"],
        "og_locale": info["og"],
        "og_locale_alt": LOCALE_INFO[other]["og"],
        "hreflang_links": alternates(),
        "home_href": "#top",
        "lang_switch": lang_switch(loc, flat["lang.label"]),
        "adapter_cards": adapter_cards(loc, catalog, adapters),
        "adapter_more": adapter_more(catalog, adapters),
        "video_section": video_section(loc, flat, video),
        "cy_labels_json": cy_labels,
    }
    used: set[str] = set()

    def fill(match: re.Match) -> str:
        key = match.group(1)
        if key in computed:
            return computed[key]
        if key not in flat:
            raise SystemExit(f"template placeholder {{{{{key}}}}} has no entry in {loc}.json")
        used.add(key)
        return flat[key]

    out = PLACEHOLDER.sub(fill, template)
    # Catalog strings are plain HTML, not templates: the first pass fills every
    # placeholder the template names, and nothing may be left over.
    leftover = PLACEHOLDER.findall(out)
    if leftover:
        raise SystemExit(f"{loc}: unresolved placeholders after rendering: {leftover}")
    return out


def unused_keys(template: str, catalogs: dict, adapters: dict) -> list[str]:
    """Catalog keys that nothing renders: the template names most of them; the
    adapter, diagram and film keys are rendered by code, so check them here."""
    named = set(PLACEHOLDER.findall(template))
    by_code = {"lang.label", "adapters.more_title", "adapters.more_lead", "adapters.cards_label"}
    by_code |= {f"adapters.{c['id']}.{part}" for c in adapters["cards"] for part in ("kind", "desc")}
    by_code |= {f"adapters_more.{m['id']}" for m in adapters["more"]}
    by_code |= {f"cy.{name}" for name in re.findall(r"\bL\.(\w+)", template)}
    by_code |= {f"video.{k}" for k in ("eyebrow", "title", "kicker", "play", "note")}
    return sorted(k for k in flatten(catalogs[DEFAULT_LOCALE]) if k not in named and k not in by_code)


def sitemap() -> str:
    pages = []
    for index in sorted(PUBLIC.rglob("index.html")):
        rel = index.parent.relative_to(PUBLIC)
        parts = rel.parts
        if parts and parts[0] in ("dtql", "ru"):
            continue
        path = "/" + "/".join(parts) + ("/" if parts else "")
        pages.append(path)
    pages.sort(key=lambda p: (p != "/", p))
    entries = []
    for path in pages:
        loc = f"{SITE}{path}"
        if path == "/":
            alt = "".join(
                f'\n    <xhtml:link rel="alternate" hreflang="{l}" href="{SITE}{LOCALE_INFO[l]["prefix"]}"/>' for l in LOCALES
            ) + f'\n    <xhtml:link rel="alternate" hreflang="x-default" href="{SITE}/"/>'
            for url in (loc, f"{SITE}{LOCALE_INFO['ru']['prefix']}"):
                entries.append(f"  <url>\n    <loc>{url}</loc>{alt}\n  </url>")
        else:
            entries.append(f"  <url>\n    <loc>{loc}</loc>\n  </url>")
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">\n'
        + "\n".join(entries)
        + "\n</urlset>\n"
    )


def build() -> dict[Path, str]:
    template = (SRC / "index.template.html").read_text(encoding="utf-8")
    catalogs = load_catalogs()
    adapters = load_json(SRC / "adapters.json")
    video = load_json(SRC / "video.json")
    stale = unused_keys(template, catalogs, adapters)
    if stale:
        raise SystemExit(f"catalog keys not used by the template: {stale}")
    outputs = {LOCALE_INFO[loc]["out"]: render_page(loc, template, catalogs, adapters, video) for loc in LOCALES}
    outputs[PUBLIC / "sitemap.xml"] = sitemap()
    return outputs


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true", help="fail if committed pages differ from the sources")
    args = parser.parse_args()
    outputs = build()
    if args.check:
        bad = False
        for path, text in outputs.items():
            current = path.read_text(encoding="utf-8") if path.exists() else ""
            if current != text:
                bad = True
                diff = difflib.unified_diff(current.splitlines(), text.splitlines(), str(path.relative_to(ROOT)), "generated", lineterm="", n=1)
                print("\n".join(list(diff)[:40]))
        if bad:
            print("Generated pages are stale. Run: python3 scripts/render_site.py", file=sys.stderr)
            return 1
        print("Landing pages and sitemap are up to date.")
        return 0
    for path, text in outputs.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        print(f"wrote {path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
