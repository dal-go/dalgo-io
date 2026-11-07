"""Topic pages share home sections; the adapter matrix uses audited source data."""
from __future__ import annotations

import html
import json
import re
from pathlib import Path

from render_articles import page_shell
from seo import breadcrumb_script, page_meta
from site_shell import TITLES, UI, enhance_page, href, title

SITE = "https://dalgo.io"
STATUS = {
    "en": {"implemented": "Implemented", "readonly": "Read-only", "partial": "Partial", "source-only": "Source only", "absent": "Not implemented", "bootstrap": "Repository scaffold"},
    "ru": {"implemented": "Реализован", "readonly": "Только чтение", "partial": "Частично", "source-only": "Только исходники", "absent": "Не реализован", "bootstrap": "Заготовка репозитория"},
}
RUNTIME = {
    "browser-local": ("Browser · local", "Браузер · локально"),
    "browser-web-sdk": ("Browser · Web SDK", "Браузер · Web SDK"),
    "browser-direct-http-conditional": ("Browser · HTTP, conditional", "Браузер · HTTP, с условиями"),
    "trusted-server-http-default": ("Trusted server · HTTP", "Доверенный сервер · HTTP"),
    "worker-binding-and-conditional-browser-http": ("Worker binding / conditional browser HTTP", "Worker binding / HTTP из браузера с условиями"),
}


def adapter_inventory(path: Path) -> dict:
    inventory = json.loads(path.read_text(encoding="utf-8"))
    ids = set()
    for row in inventory["adapters"]:
        if row["id"] in ids:
            raise ValueError(f"Duplicate adapter: {row['id']}")
        ids.add(row["id"])
        for language in ("go", "typescript"):
            cell = row[language]
            if cell["status"] not in STATUS["en"]:
                raise ValueError(f"Unknown adapter status: {cell['status']}")
            runtime = cell.get("runtime")
            if runtime and runtime["classification"] not in RUNTIME:
                raise ValueError("Unknown runtime classification")
            for url in cell.get("sources", []) + (runtime.get("sources", []) if runtime else []):
                if not url.startswith("https://github.com/"):
                    raise ValueError("Adapter evidence must link to the canonical GitHub source")
    return inventory


def adapter_cell(cell: dict, locale: str) -> str:
    escape = html.escape
    result = f'<span class="adapter-status">{STATUS[locale][cell["status"]]}</span>'
    implementation = cell.get("implementation_status")
    if implementation and implementation != cell["status"]:
        result += f'<span class="runtime-note">{STATUS[locale][implementation]}</span>'
    runtime = cell.get("runtime")
    if runtime:
        result += f'<p><span class="runtime-badge">{RUNTIME[runtime["classification"]][locale == "ru"]}</span></p>'
        result += '<span class="runtime-note">Node.js / edge: ' + ('qualification unverified' if locale == 'en' else 'проверка выполнения не подтверждена') + '</span>'
    if cell.get("manifest_private"):
        result += '<p>' + ('Private npm manifest · use source' if locale == 'en' else 'Приватный npm-манифест · исходный код') + '</p>'
    details = []
    for limit in cell.get("limits", []):
        details.append(f'<li lang="en">{escape(limit)}</li>')
    if runtime:
        browser = runtime["browser"]
        for text in (browser.get("conditions_and_limits"), browser.get("note"), runtime["node"].get("note"), runtime["edge"].get("note")):
            if text:
                details.append(f'<li lang="en">{escape(text)}</li>')
    sources = cell.get("sources", []) + (runtime.get("sources", []) if runtime else [])
    if details or sources:
        label = 'Limits and source' if locale == 'en' else 'Ограничения и исходники'
        result += f'<details><summary>{label}</summary><ul>{"".join(details)}</ul>'
        result += ' · '.join(f'<a href="{escape(url, quote=True)}">{"Source" if locale == "en" else "Исходник"} {index + 1}</a>' for index, url in enumerate(dict.fromkeys(sources)))
        result += '</details>'
    return result


def adapter_table(inventory: dict, locale: str) -> str:
    heading = 'Implementation and runtime support' if locale == 'en' else 'Реализация и среды выполнения'
    note = ('Implementation, package publication and runtime are tracked separately. Package publication was not verified by this source audit. Runtime badges describe the source and documented contract; they are not live-service test receipts. Browser HTTP access requires suitable CORS and user-scoped authentication. Node.js and edge execution were not qualified in this audit. A server driver can be exposed through an explicitly implemented HTTP service; that does not make the driver browser-compatible.' if locale == 'en' else
            'Реализация, публикация пакета и среда выполнения учитываются отдельно. Публикация пакетов в этом аудите исходников не проверялась. Метки сред описывают код и документацию; проверка живого сервиса ими не подтверждается. Для HTTP из браузера нужны подходящие CORS и авторизация пользователя. Выполнение в Node.js и edge в этом аудите не проверялось. Серверный драйвер можно предоставить через реализованный HTTP-сервис; сам драйвер при этом остаётся серверным.')
    rows = ''.join(f'<tr><th scope="row">{html.escape(row["name"])}</th><td>{adapter_cell(row["go"], locale)}</td><td>{adapter_cell(row["typescript"], locale)}</td></tr>' for row in inventory['adapters'])
    return f'''<header class="section-head"><h1>{html.escape(title("adapters", locale))}</h1><p>{note}</p></header>
<p>{"Source audit" if locale == "en" else "Аудит исходников"}: <time>{inventory["auditDate"]}</time> · <a href="/adapters/status.json">JSON</a></p>
<div class="adapter-table-wrap"><table class="adapter-table"><caption>{heading}</caption><thead><tr><th scope="col">{"Adapter" if locale == "en" else "Адаптер"}</th><th scope="col">Go</th><th scope="col">TypeScript</th></tr></thead><tbody>{rows}</tbody></table></div>'''


def go_section(locale: str) -> str:
    text = ('Use typed keys, records, collections and structured queries in Go. Start locally with the built-in in-memory adapter, then choose a database adapter by its supported operations. The definition of that layer is <a href="/articles/go-database-abstraction-layer/">Database abstraction layer in Go</a>.' if locale == 'en' else
            'Используйте типизированные ключи, записи, коллекции и структурированные запросы в Go. Начните со встроенного адаптера в памяти, затем выберите адаптер по поддерживаемым операциям. Определение этого слоя — в статье <a href="/articles/go-database-abstraction-layer/">Database abstraction layer in Go</a> (англ.).')
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
        meta = page_meta(slug, locale)
        crumbs = breadcrumb_script([("DALgo", SITE + href("", locale)), (title(slug, locale), canonical)])
        main = f'<main id="top" class="container topic-page"><p><a href="{href("", locale)}">DALgo</a> / {html.escape(title(slug, locale))}</p>{body}</main>'
        rendered = page_shell(title=meta["title"], description=meta["description"], canonical=canonical, og_type='website', main=main, context_label=title(slug, locale), context_href=href(slug, locale), extra_head=alternates + crumbs, locale=locale, section=slug)
        result[public / ('ru' if locale == 'ru' else '') / slug / 'index.html'] = rendered
    return result
