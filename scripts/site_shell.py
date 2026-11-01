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
.adapter-table-wrap {max-width:100%;overflow-x:auto;margin-top:24px}
.adapter-table {border-collapse:collapse;width:100%;font-size:14px}
.adapter-table th,.adapter-table td {padding:16px;text-align:left;vertical-align:top;border:1px solid var(--border-default)}
.adapter-table thead {background:var(--canvas-subtle)}
.adapter-table td {min-width:230px;width:40%}
.adapter-table td p {margin:8px 0}.adapter-table details {margin-top:10px}
.adapter-table summary {cursor:pointer;color:var(--accent-fg)}
.adapter-status,.runtime-badge {display:inline-block;border:1px solid var(--border-default);border-radius:6px;padding:2px 7px;margin:0 4px 4px 0;background:var(--canvas-subtle)}
.runtime-badge {border-color:var(--accent-fg);color:var(--accent-fg)}
.runtime-note {display:block;color:var(--fg-muted);font-size:12px}
@media(max-width:1000px){.AppHeader-inner{height:auto;min-height:56px;flex-wrap:wrap;padding-top:10px;padding-bottom:10px}.AppHeader-nav{order:3;flex-basis:100%;display:flex!important;flex-wrap:wrap;justify-content:center;gap:4px 12px;margin:0}.AppHeader-actions{margin-left:auto}.AppHeader-nav a{font-size:13px}.AppHeader-brand{padding:0}}
"""
