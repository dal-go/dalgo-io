"""Topic pages share home sections; the adapter matrix uses audited source data."""
from __future__ import annotations

import html
import json
import re
from pathlib import Path

from render_articles import page_shell
from site_shell import TITLES, UI, enhance_page, href, title

from capability_matrix import load_inventory as adapter_inventory, render_matrix as adapter_table

SITE = "https://dalgo.io"


def go_section(locale: str) -> str:
    text = ('Use typed keys, records, collections and structured queries in Go. Start locally with the built-in in-memory adapter, then choose a database adapter by its supported operations.' if locale == 'en' else
            'Используйте типизированные ключи, записи, коллекции и структурированные запросы в Go. Начните со встроенного адаптера в памяти, затем выберите адаптер по поддерживаемым операциям.')
    return f'<section id="go" class="section"><div class="container"><h2 class="section-title">{title("go", locale)}</h2><p>{text}</p><p><a href="https://github.com/dal-go/dalgo">Go source</a> · <a href="https://pkg.go.dev/github.com/dal-go/dalgo">Go API</a> · <a href="{href("quickstart", locale)}">{title("quickstart", locale)}</a></p></div></section>'


def section_slug(section: str) -> str | None:
    match = re.search(r'<section\b[^>]*\bid="([^"]+)"', section)
    if match and match[1] in TITLES:
        return match[1]
    return 'datatug' if 'aria-labelledby="datatug-heading"' in section else None


def home_sections(page: str, locale: str) -> tuple[str, dict[str, str]]:
    page = page.replace('<section id="typescript"', go_section(locale) + '\n<section id="typescript"', 1)
    sections = {}
    def link(match):
        section = match[0]
        slug = section_slug(section)
        if slug:
            sections[slug] = section
            section = section.replace('</section>', f'<div class="container"><a class="topic-link" href="{href(slug, locale)}">{UI[locale]["more"]}: {html.escape(title(slug, locale))} →</a></div></section>')
        return section
    return re.sub(r'<section\b[\s\S]*?</section>', link, page), sections


def topic_pages(page: str, locale: str, inventory: dict, source: Path, public: Path) -> dict[Path, str]:
    _, sections = home_sections(page, locale)
    result = {}
    for slug in TITLES:
        if slug == 'adapters':
            body = adapter_table(inventory, locale)
        else:
            if slug not in sections and slug == 'film':
                sections[slug] = '<section class="section"><h2>' + html.escape(title(slug, locale)) + '</h2><p>' + ('The film is currently unavailable.' if locale == 'en' else 'Фильм сейчас недоступен.') + '</p></section>'
            if slug not in sections:
                raise ValueError(f'Missing home topic section: {slug}')
            body = re.sub(r'<h2\b([^>]*)>[\s\S]*?</h2>', lambda match: '<h1' + match[1] + '>' + html.escape(title(slug, locale)) + '</h1>', sections[slug], count=1)
            if slug == 'go':
                body += sections['interfaces'] + sections['collections']
            if slug == 'quickstart':
                starter = (source / 'typescript-quickstart.html').read_text(encoding='utf-8')
                strings = {
                    'ts_start_title': 'TypeScript · browser' if locale == 'en' else 'TypeScript · браузер',
                    'ts_start_intro': ('In a TypeScript browser project with a bundler, install the core and IndexedDB adapter. No database account is needed. IndexedDB stores data on this browser origin; this example does not run in Node.js.' if locale == 'en' else 'В браузерном TypeScript-проекте со сборщиком установите ядро и адаптер IndexedDB. Аккаунт базы данных не нужен. Данные хранятся в браузере для этого origin; пример не запускается в Node.js.'),
                    'ts_start_file': 'Use this in the browser entrypoint, then open the app and inspect the console:' if locale == 'en' else 'Добавьте код в браузерную точку входа, откройте приложение и посмотрите консоль:',
                    'ts_start_code': html.escape((source / 'typescript-quickstart.ts').read_text(encoding='utf-8')),
                }
                for key, value in strings.items():
                    starter = starter.replace('{{' + key + '}}', value)
                body += starter
            if slug == 'typescript':
                body += f'<h2>{"Choose a runtime" if locale == "en" else "Выберите среду выполнения"}</h2><p>' + (
                    'Browser-local adapters and browser HTTP adapters have different requirements from Node.js/server drivers. Use explicit per-adapter lazy imports. Keep server SDKs and service-account credentials on the server. Review CORS, authorization and runtime conditions in the adapter matrix.' if locale == 'en' else
                    'Локальные и HTTP-адаптеры браузера отличаются от драйверов Node.js/сервера. Загружайте выбранный адаптер лениво. Серверные SDK и сервисные учётные данные остаются на сервере. Смотрите условия CORS, авторизации и среды выполнения в таблице адаптеров.') + f'</p><a href="{href("adapters", locale)}">{title("adapters", locale)}</a>'
            if slug == 'film':
                body += '<script src="/video.js" defer></script>'
        canonical = SITE + href(slug, locale)
        alternates = ''.join(f'<link rel="alternate" hreflang="{language}" href="{SITE}{href(slug, language)}" />\n' for language in ('en', 'ru'))
        alternates += f'<link rel="alternate" hreflang="x-default" href="{SITE}{href(slug, "en")}" />\n'
        main = f'<main id="top" class="container topic-page"><p><a href="{href("", locale)}">DALgo</a> / {html.escape(title(slug, locale))}</p>{body}</main>'
        rendered = page_shell(title=title(slug, locale) + ' · DALgo', description=title(slug, locale), canonical=canonical, og_type='website', main=main, context_label=title(slug, locale), context_href=href(slug, locale), extra_head=alternates, locale=locale, section=slug)
        result[public / ('ru' if locale == 'ru' else '') / slug / 'index.html'] = rendered
    return result
