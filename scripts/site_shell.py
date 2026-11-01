"""Shared small navigation and theme controls for static DALgo pages."""
from __future__ import annotations

import html
import re

TITLES = {
    "go": ("DALgo for Go", "DALgo для Go"),
    "typescript": ("DALgo for TypeScript", "DALgo для TypeScript"),
    "quickstart": ("Quick Start", "Быстрый старт"),
    "adapters": ("Adapters and runtime support", "Адаптеры и среды выполнения"),
    "why": ("Why DALgo", "Зачем DALgo"),
    "collections": ("Typed collections", "Типизированные коллекции"),
    "interfaces": ("Interfaces", "Интерфейсы"),
    "queries": ("Queries and schema", "Запросы и схема"),
    "film": ("Swap the adapter", "Смените адаптер"),
    "datatug": ("DALgo and DataTug", "DALgo и DataTug"),
}
UI = {
    "en": {"theme": "Theme", "system": "System", "light": "Light", "dark": "Dark", "docs": "Documentation", "more": "Read more", "language": "Language"},
    "ru": {"theme": "Тема", "system": "Системная", "light": "Светлая", "dark": "Тёмная", "docs": "Документация", "more": "Подробнее", "language": "Язык"},
}


def title(slug: str, locale: str) -> str:
    return TITLES[slug][locale == "ru"]


def href(slug: str, locale: str) -> str:
    return ("/ru/" if locale == "ru" else "/") + (slug + "/" if slug else "")


def enhance_page(page: str, locale: str = "en", slug: str | None = None) -> str:
    ui = UI[locale]
    if 'src="/theme.js"' not in page:
        page = page.replace('<meta charset="utf-8" />', '<meta charset="utf-8" />\n<script src="/theme.js"></script>')
        page = page.replace('</head>', '<link rel="stylesheet" href="/theme.css" />\n<script src="/site.js" defer></script>\n</head>')
    # Minimal reference pages may start with only the brand in their header.
    header = re.search(r'<header class="AppHeader"[^>]*>[\s\S]*?</header>', page)
    if header:
        markup = header.group()
        additions = ''
        if 'class="AppHeader-nav"' not in markup:
            additions += '<nav class="AppHeader-nav"></nav>'
        if 'class="AppHeader-actions"' not in markup:
            additions += '<div class="AppHeader-actions"></div>'
        markup = re.sub(r'(\s*</div>\s*</header>)$', lambda match: additions + match.group(), markup)
        page = page[:header.start()] + markup + page[header.end():]
    primary = "".join(f'<a href="{href(key, locale)}">{label}</a>' for key, label in [
        ("go", "Go"), ("typescript", "TypeScript"),
        ("adapters", "Адаптеры" if locale == "ru" else "Adapters"),
        ("quickstart", "Быстрый старт" if locale == "ru" else "Quick Start"),
    ])
    page = re.sub(r'<nav class="AppHeader-nav"[^>]*>[\s\S]*?</nav>', f'<nav class="AppHeader-nav" aria-label="{ui["docs"]}">{primary}</nav>', page, count=1)
    page = re.sub(r'<nav class="AppHeader-context"[^>]*>[\s\S]*?</nav>', '', page, count=1)
    page = re.sub(r'<a class="btn[^\"]*" href="https://github.com/dal-go/dalgo"[^>]*>[\s\S]*?</a>', '', page, count=1)
    if 'data-theme-switch' not in page:
        control = f'<label class="theme-control" data-theme-control hidden><span aria-hidden="true">◐</span><select data-theme-switch aria-label="{ui["theme"]}">'
        control += "".join(f'<option value="{mode}">{ui[mode]}</option>' for mode in ("system", "light", "dark"))
        control += '</select></label>'
        page = page.replace('<div class="AppHeader-actions">', '<div class="AppHeader-actions">' + control, 1)
    if slug is not None and 'class="lang-switch"' not in page:
        languages = f'<nav class="lang-switch" aria-label="{ui["language"]}">'
        for other in ("en", "ru"):
            languages += (f'<span class="lang-switch-item" aria-current="true" lang="{other}">{other.upper()}</span>' if other == locale else
                          f'<a class="lang-switch-item" href="{href(slug, other)}" hreflang="{other}" lang="{other}" data-lang-link>{other.upper()}</a>')
        languages += '</nav>'
        page = page.replace('<div class="AppHeader-actions">', '<div class="AppHeader-actions">' + languages, 1)
    if 'data-topic-footer' not in page:
        secondary = "".join(f'<a href="{href(key, locale)}">{html.escape(title(key, locale))}</a>' for key in TITLES)
        secondary += '<a href="/articles/">Articles</a><a href="/tugql/">TugQL</a>'
        page = page.replace('</footer>', f'<nav class="topic-footer container" data-topic-footer aria-label="{ui["docs"]}">{secondary}</nav></footer>', 1)
    return re.sub(r'[ \t]+$', '', page, flags=re.MULTILINE)


def theme_styles(styles: str) -> str:
    light = re.search(r':root\s*\{([^}]+)\}', styles).group(1)
    dark = re.search(r'@media\s*\(prefers-color-scheme: dark\)\s*\{\s*:root\s*\{([^}]+)\}', styles).group(1)
    variables = lambda text: dict(re.findall(r'(--[\w-]+)\s*:\s*([^;]+);', text))
    palettes = {"light": variables(light), "dark": variables(dark)}
    result = '/* Generated from the primary styles.css palette. */\n'
    for mode, values in palettes.items():
        result += f':root[data-theme="{mode}"] {{color-scheme:{mode};'
        result += ''.join(f'{key}:{values[key]};' for key in palettes['dark']) + '}\n'
        for suffix in ('', ':hover', ':focus-visible'):
            blocks = re.findall(r'^[ \t]*\.site-feedback button' + re.escape(suffix) + r'\s*\{([^}]+)\}', styles, re.MULTILINE)
            if blocks:
                result += f':root[data-theme="{mode}"] .site-feedback button{suffix}{{{blocks[0 if mode == "light" else -1]}}}\n'
    result += ':root[data-theme="light"] .feedback-mark rect{fill:#d4ef83}:root[data-theme="dark"] .feedback-mark rect{fill:#9bb67b}\n'
    return result + """
.theme-control {display:inline-flex;align-items:center;gap:6px;color:var(--header-fg)}
.theme-control[hidden] {display:none}
.theme-control select {background:var(--header-bg);color:var(--header-fg);border:1px solid var(--header-fg-muted);border-radius:6px;padding:7px;max-width:125px}
.theme-control select:focus-visible,a:focus-visible {outline:2px solid var(--accent-fg);outline-offset:3px}
.topic-footer {display:flex;gap:12px 20px;flex-wrap:wrap;padding-top:20px;padding-bottom:24px;font-size:14px}
.topic-footer a {color:var(--fg-muted)}
.topic-link {display:inline-block;margin-top:16px;font-weight:600}
.topic-page {padding-top:32px;padding-bottom:48px}
.topic-page h1 {font-size:clamp(1.8rem,4vw,2.8rem)}
.cap-matrix {margin:24px 0;max-width:100%}
.cap-adapter {border-top:1px solid var(--border-default);margin:0;padding:0}
.cap-adapter:last-child {border-bottom:1px solid var(--border-default)}
.cap-adapter>summary {display:grid;grid-template-columns:minmax(130px,1.2fr) repeat(3,minmax(0,1fr));gap:14px;align-items:center;padding:14px 8px;cursor:pointer;list-style:none}
.cap-adapter>summary::-webkit-details-marker {display:none}
.cap-adapter-name {font-weight:650;overflow-wrap:anywhere}
.cap-adapter-name::before {content:"+ ";color:var(--accent-fg)}
.cap-adapter[open]>.cap-adapter-name::before,.cap-adapter[open]>summary .cap-adapter-name::before {content:"− "}
.cap-adapter>summary:focus-visible {outline:3px solid var(--accent-fg);outline-offset:2px}
.cap-overview {display:flex;flex-direction:column;gap:3px;min-width:0;font-size:12px;color:var(--fg-muted);overflow-wrap:anywhere}
.cap-runtime-name {font-weight:600;color:var(--fg-default)}
.cap-expanded {padding:4px 8px 18px}
.cap-table-scroll {max-width:100%;overflow-x:auto;overscroll-behavior-x:contain}
.cap-table-scroll:focus-visible {outline:3px solid var(--accent-fg);outline-offset:-3px}
.cap-scroll-hint {font-size:12px;color:var(--fg-muted);margin:8px 0}
.cap-table {border-collapse:collapse;width:100%;min-width:800px;table-layout:fixed;font-size:13px}
.cap-table caption {text-align:left;font-weight:650;padding:10px 0}
.cap-table th,.cap-table td {padding:10px 8px;vertical-align:top;text-align:left;border:1px solid var(--border-default);overflow-wrap:anywhere}
.cap-table th:first-child {width:17%}
.cap-table thead {background:var(--canvas-subtle)}
.cap-table p {margin:7px 0}
.cap-status {display:inline-block;border:1px solid var(--border-default);border-radius:4px;padding:2px 5px;font-size:12px;background:var(--canvas-subtle);color:var(--fg-default);max-width:100%;overflow-wrap:anywhere}
.cap-supported {border-style:double}.cap-partial {border-style:dashed}.cap-not-implemented {border-style:dotted}.cap-unsupported {font-weight:650}
.cap-legend {display:flex;gap:6px;flex-wrap:wrap}
.cap-proof,.cap-publication {color:var(--fg-muted)}
.cap-expanded a {overflow-wrap:anywhere}
@media(min-width:901px) {.cap-scroll-hint {display:none}}
@media(max-width:600px) {.cap-adapter>summary {grid-template-columns:repeat(3,minmax(0,1fr));gap:10px;padding:12px 4px}.cap-adapter-name {grid-column:1/-1}.cap-table {font-size:12px}.cap-table th,.cap-table td {padding:7px 4px}.cap-status {font-size:11px;padding:2px 3px}.cap-expanded {padding:0 0 14px}.cap-table th:first-child {width:19%}}

@media(max-width:1000px){.AppHeader-inner{height:auto;min-height:56px;flex-wrap:wrap;padding-top:10px;padding-bottom:10px}.AppHeader-nav{order:3;flex-basis:100%;display:flex!important;flex-wrap:wrap;justify-content:center;gap:4px 12px;margin:0}.AppHeader-actions{margin-left:auto}.AppHeader-nav a{font-size:13px}.AppHeader-brand{padding:0}}
"""
