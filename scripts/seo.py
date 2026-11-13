"""Titles, descriptions, JSON-LD, and llms.txt for the static site.

Home titles and descriptions stay in content/site/en.json and ru.json.
Every other routable page takes them from content/site/seo.json so the
published copy and the llms files are generated from the same sources.
"""

from __future__ import annotations

import html
import json
import re
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE = "https://dalgo.io"
SEO_PATH = ROOT / "content" / "site" / "seo.json"
DESCRIPTION_MIN = 120
DESCRIPTION_MAX = 160

PAIRED = (
    "go",
    "typescript",
    "quickstart",
    "adapters",
    "why",
    "collections",
    "interfaces",
    "queries",
    "film",
    "datatug",
    "about/tech-stack",
)
ENGLISH_ONLY = ("articles", "privacy", "tugql", "tugql/examples")
GO_REPO = "https://github.com/dal-go/dalgo"
GO_LICENSE = "https://github.com/dal-go/dalgo/blob/main/LICENSE"
TS_REPO = "https://github.com/dal-go/dalgo-js"
TS_LICENSE = "https://github.com/dal-go/dalgo-js/blob/main/LICENSE"
TS_ADAPTERS_REPO = "https://github.com/dal-go/dalgo-http-adapters"

CORE_REPOS = (
    (GO_REPO, "dalgo", "Go module and the main DALgo implementation."),
    (TS_REPO, "dalgo-js", "TypeScript package @dalgo/core."),
    (
        TS_ADAPTERS_REPO,
        "dalgo-http-adapters",
        "Qualification matrix and catalog for DALgo TypeScript HTTP data adapters.",
    ),
)

_LINKED_CLAIM = re.compile(r"open[\s-]*source|\bMIT\b|licen[cs]e", re.I)


def plain(value: str) -> str:
    text = re.sub(r"<[^>]+>", "", value)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text.replace("\xa0", " ")).strip()


def _fail(message: str) -> None:
    raise SystemExit(message)


def check_description(where: str, description: str) -> None:
    length = len(description)
    if length < DESCRIPTION_MIN or length > DESCRIPTION_MAX:
        _fail(f"{where} description is {length} characters; need {DESCRIPTION_MIN}-{DESCRIPTION_MAX}")
    if re.search(r"[<>]", description):
        _fail(f"{where} description must not contain HTML tags")


@lru_cache(maxsize=1)
def load_seo() -> dict:
    data = json.loads(SEO_PATH.read_text(encoding="utf-8"))
    expected = set(PAIRED) | set(ENGLISH_ONLY)
    if set(data) != expected:
        _fail(f"seo.json pages differ from the renderer: missing {sorted(expected - set(data))}, extra {sorted(set(data) - expected)}")
    titles: list[str] = []
    descriptions: list[str] = []
    for slug in PAIRED:
        for locale in ("en", "ru"):
            entry = data[slug].get(locale)
            if not entry:
                _fail(f"seo.json missing {slug}/{locale}")
            check_description(f"{slug}/{locale}", entry["description"])
            if not str(entry.get("title", "")).strip():
                _fail(f"seo.json {slug}/{locale} title is empty")
            titles.append(entry["title"])
            descriptions.append(entry["description"])
    for slug in ENGLISH_ONLY:
        if set(data[slug]) != {"en"}:
            _fail(f"seo.json {slug} is English-only and must not invent a Russian page")
        entry = data[slug]["en"]
        check_description(slug, entry["description"])
        if not str(entry.get("title", "")).strip():
            _fail(f"seo.json {slug} title is empty")
        titles.append(entry["title"])
        descriptions.append(entry["description"])
    if len(titles) != len(set(titles)):
        _fail("seo.json titles are not unique")
    if len(descriptions) != len(set(descriptions)):
        _fail("seo.json descriptions are not unique")
    return data


def page_meta(slug: str, locale: str) -> dict[str, str]:
    try:
        entry = load_seo()[slug][locale]
    except KeyError as exc:
        _fail(f"seo.json missing {slug}/{locale}")
        raise exc
    return {"title": entry["title"], "description": entry["description"]}


def check_home_copy(catalogs: dict[str, dict]) -> None:
    seen = {entry["title"] for page in load_seo().values() for entry in page.values()}
    descriptions = {entry["description"] for page in load_seo().values() for entry in page.values()}
    for locale in ("en", "ru"):
        title = catalogs[locale]["meta.title"]
        description = catalogs[locale]["meta.description"]
        check_description(f"home/{locale}", description)
        if title in seen:
            _fail(f"home {locale} title duplicates another page")
        seen.add(title)
        if description in descriptions:
            _fail(f"home {locale} description duplicates another page")
        descriptions.add(description)
        og = catalogs[locale]["meta.og_description"]
        check_description(f"home/{locale} og", og)


def dumps(payload: object) -> str:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")


def json_ld_script(payload: object) -> str:
    return f'<script type="application/ld+json">{dumps(payload)}</script>\n'


def breadcrumb_script(items: list[tuple[str, str]]) -> str:
    return json_ld_script(
        {
            "@context": "https://schema.org",
            "@type": "BreadcrumbList",
            "itemListElement": [
                {"@type": "ListItem", "position": index, "name": name, "item": url}
                for index, (name, url) in enumerate(items, start=1)
            ],
        }
    )


def home_json_ld() -> str:
    organization = f"{SITE}/#organization"
    return json_ld_script(
        {
            "@context": "https://schema.org",
            "@graph": [
                {
                    "@type": "Organization",
                    "@id": organization,
                    "name": "DALgo",
                    "url": f"{SITE}/",
                    "sameAs": ["https://github.com/dal-go", GO_REPO, TS_REPO],
                },
                {
                    "@type": "WebSite",
                    "@id": f"{SITE}/#website",
                    "name": "DALgo",
                    "url": f"{SITE}/",
                    "inLanguage": ["en", "ru"],
                    "publisher": {"@id": organization},
                },
                {
                    "@type": "SoftwareSourceCode",
                    "name": "DALgo",
                    "description": "Database Abstraction Layer (DAL) in Go language",
                    "codeRepository": GO_REPO,
                    "programmingLanguage": "Go",
                    "license": GO_LICENSE,
                    "url": f"{SITE}/go/",
                    "author": {"@id": organization},
                },
                {
                    "@type": "SoftwareSourceCode",
                    "name": "@dalgo/core",
                    "description": "Database abstraction layer for TypeScript and browser applications",
                    "codeRepository": TS_REPO,
                    "programmingLanguage": "TypeScript",
                    "license": TS_LICENSE,
                    "url": f"{SITE}/typescript/",
                    "author": {"@id": organization},
                },
            ],
        }
    )


def static_crumbs(route: str) -> list[tuple[str, str]]:
    home = ("DALgo", f"{SITE}/")
    if route == "privacy":
        return [home, ("Privacy", f"{SITE}/privacy/")]
    if route == "tugql":
        return [home, ("TugQL", f"{SITE}/tugql/")]
    if route == "tugql/examples":
        return [home, ("TugQL", f"{SITE}/tugql/"), ("Examples", f"{SITE}/tugql/examples/")]
    _fail(f"no breadcrumb for {route}")
    return []


def _upsert(page: str, pattern: str, tag: str, anchor: str) -> str:
    if re.search(pattern, page, re.I):
        return re.sub(pattern, lambda _match: tag, page, count=1, flags=re.I)
    return page.replace(anchor, tag + "\n" + anchor, 1)


def apply_static_seo(page: str, route: str) -> str:
    meta = page_meta(route, "en")
    canonical = f"{SITE}/{route}/"
    title = f"<title>{html.escape(meta['title'])}</title>"
    description = f'<meta name="description" content="{html.escape(meta["description"], quote=True)}" />'
    canon = f'<link rel="canonical" href="{canonical}" />'
    quoted = html.escape(meta["description"], quote=True)
    page = _upsert(page, r"<title>.*?</title>", title, "</head>")
    page = _upsert(page, r'<meta name="description" content="[^"]*"\s*/?>', description, "</head>")
    page = _upsert(page, r'<link rel="canonical" href="[^"]*"\s*/?>', canon, "</head>")
    if re.search(r'<meta property="og:title"', page):
        page = _upsert(
            page,
            r'<meta property="og:title" content="[^"]*"\s*/?>',
            f'<meta property="og:title" content="{html.escape(meta["title"], quote=True)}" />',
            "</head>",
        )
    if re.search(r'<meta property="og:description"', page):
        page = _upsert(
            page,
            r'<meta property="og:description" content="[^"]*"\s*/?>',
            f'<meta property="og:description" content="{quoted}" />',
            "</head>",
        )
    if re.search(r'<meta property="og:url"', page):
        page = _upsert(
            page,
            r'<meta property="og:url" content="[^"]*"\s*/?>',
            f'<meta property="og:url" content="{canonical}" />',
            "</head>",
        )
    script = breadcrumb_script(static_crumbs(route))
    if "application/ld+json" not in page:
        page = page.replace("</head>", script + "</head>", 1)
    return page


def _link(label: str, url: str, description: str) -> str:
    return f"- [{label}]({url}): {plain(description)}"


def _page_links(locale: str, slugs: tuple[str, ...], catalogs: dict[str, dict]) -> list[str]:
    lines = []
    prefix = "/ru" if locale == "ru" else ""
    if "home" in slugs:
        lines.append(_link("Home" if locale == "en" else "Главная", f"{SITE}{prefix or ''}/", catalogs[locale]["meta.description"]))
    labels = {
        "en": {
            "go": "Go",
            "typescript": "TypeScript",
            "quickstart": "Quick start",
            "adapters": "Adapters",
            "why": "Why DALgo",
            "collections": "Typed collections",
            "interfaces": "Interfaces",
            "queries": "Queries",
            "film": "Films",
            "datatug": "DataTug",
            "about/tech-stack": "Tech stack",
            "articles": "Articles",
            "privacy": "Privacy",
            "tugql": "TugQL",
            "tugql/examples": "TugQL examples",
        },
        "ru": {
            "go": "Go",
            "typescript": "TypeScript",
            "quickstart": "Быстрый старт",
            "adapters": "Адаптеры",
            "why": "Зачем DALgo",
            "collections": "Коллекции",
            "interfaces": "Интерфейсы",
            "queries": "Запросы",
            "film": "Фильм",
            "datatug": "DataTug",
            "about/tech-stack": "Технологии",
        },
    }
    for slug in slugs:
        if slug == "home":
            continue
        url = f"{SITE}{prefix}/{slug}/"
        lines.append(_link(labels[locale][slug], url, page_meta(slug, locale)["description"]))
    return lines


def _repo_lines(adapters: dict, catalogs: dict[str, dict], include_more: bool) -> list[str]:
    lines = [_link(name, url, description) for url, name, description in CORE_REPOS]
    seen = {url for url, _name, _description in CORE_REPOS}
    groups = list(adapters["cards"])
    if include_more:
        groups += list(adapters["more"])
    for item in groups:
        url = item["url"]
        if url in seen:
            continue
        seen.add(url)
        if item in adapters["cards"]:
            description = plain(catalogs["en"]["adapters"][item["id"]]["desc"])
        else:
            description = plain(catalogs["en"]["adapters_more"][item["id"]])
        lines.append(_link(item["name"], url, description))
    return lines


def _prose_blocks(catalog: dict) -> list[str]:
    blocks = [plain(catalog["hero.lede"])]
    for index in range(1, 7):
        blocks.append(f"{plain(catalog[f'why.{index}.title'])}. {plain(catalog[f'why.{index}.text'])}")
    for key in ("ts.prose", "ts.adapters", "if.prose", "q.prose", "dt.text"):
        blocks.append(plain(catalog[key]))
    return [block for block in blocks if block and not _LINKED_CLAIM.search(block)]


def llms_documents(catalogs: dict[str, dict], adapters: dict, articles: list) -> tuple[str, str]:
    check_home_copy(catalogs)
    primary = ("home", "go", "typescript", "adapters", "articles")
    secondary = ("quickstart", "why", "collections", "interfaces", "queries", "film", "datatug", "about/tech-stack")
    english = _page_links("en", primary, catalogs)
    russian = _page_links("ru", ("home", "go", "typescript", "adapters") + secondary, catalogs)
    optional = _page_links("en", secondary + ("privacy", "tugql", "tugql/examples"), catalogs)
    intro = (
        "# DALgo\n\n"
        f"> {catalogs['en']['meta.description']}\n\n"
        f"DALgo is [open-source]({GO_REPO}). The Go module is the main implementation "
        f"([MIT license]({GO_LICENSE})). The TypeScript package @dalgo/core is published on npm "
        f"from [dalgo-js]({TS_REPO}) ([MIT license]({TS_LICENSE})). "
        "English pages are the default. Russian pages use the same paths under /ru/.\n\n"
        "## English\n\n"
        + "\n".join(english)
        + "\n\n## Russian\n\n"
        + "\n".join(russian)
        + "\n\n## Repositories\n\n"
        + "\n".join(_repo_lines(adapters, catalogs, include_more=False))
        + "\n\n## Optional\n\n"
        + "\n".join(optional)
        + "\n"
    )
    article_lines = []
    for article in articles:
        summary = plain(article.summary)
        if _LINKED_CLAIM.search(summary):
            summary = article.description
        article_lines.append(_link(article.title, article.canonical, f"{article.iso_date}. {article.description} {summary}"))
    full = (
        intro
        + "\n## English product copy\n\n"
        + "\n\n".join(_prose_blocks(catalogs["en"]))
        + "\n\n## Russian product copy\n\n"
        + "\n\n".join(_prose_blocks(catalogs["ru"]))
        + "\n\n## Adapter catalogue\n\n"
        + "\n".join(_repo_lines(adapters, catalogs, include_more=True))
        + "\n\n## Articles\n\n"
        + "\n".join(article_lines)
        + "\n"
    )
    return intro, full
