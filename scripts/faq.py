"""DALgo FAQ at /faq/ and /ru/faq/. Answers come from the DALgo repositories and site pages.

The FAQPage JSON-LD is built from the same strings as the visible page, so the two always match.
"""
from __future__ import annotations

import html
import re
from pathlib import Path

GO = "https://github.com/dal-go/dalgo"
GO_LICENSE = "https://github.com/dal-go/dalgo/blob/main/LICENSE"
TS = "https://github.com/dal-go/dalgo-js"
TS_LICENSE = "https://github.com/dal-go/dalgo-js/blob/main/LICENSE"
CONTRIBUTING = "https://github.com/dal-go/dalgo/blob/main/CONTRIBUTING.md"

INTRO = {
    "en": f'<a href="/">DALgo</a> is an <a href="{GO}">open-source</a> database abstraction layer (DAL) for Go and TypeScript: one interface for records, queries and transactions, with adapters for different databases. An ORM (object-relational mapper) maps objects to relational tables; SQL (Structured Query Language) is the query language of relational databases; CRUD means create, read, update and delete, the four basic record operations. Start with <a href="/go/">DALgo for Go</a>, <a href="/typescript/">DALgo for TypeScript</a>, the <a href="/adapters/">adapter matrix</a> or the <a href="/articles/">articles</a>.',
    "ru": f'<a href="/ru/">DALgo</a> — <a href="{GO}">библиотека с открытым исходным кодом</a>, слой абстракции базы данных (DAL, database abstraction layer) для Go и TypeScript: один интерфейс для записей, запросов и транзакций и адаптеры для разных баз данных. ORM (object-relational mapper, объектно-реляционное отображение) связывает объекты с реляционными таблицами; SQL (Structured Query Language) — язык запросов реляционных баз данных; CRUD (create, read, update, delete) — четыре базовые операции с записями: создание, чтение, изменение и удаление. Начните со страниц <a href="/ru/go/">DALgo для Go</a>, <a href="/ru/typescript/">DALgo для TypeScript</a>, <a href="/ru/adapters/">таблицы адаптеров</a> или <a href="/articles/">статей</a> (англ.).',
}

QA = {
    "en": [
        ("What is DALgo?",
         f'DALgo is a database abstraction layer for Go applications. Its <a href="{GO}">README</a> describes one small, consistent API for records, queries, transactions, hooks and schema-aware key mapping, while the storage backend stays an implementation choice. A TypeScript implementation, <code>@dalgo/core</code>, lives in a separate repository. See <a href="/go/">DALgo for Go</a>.'),
        ("Is DALgo an ORM (object-relational mapper)?",
         'DALgo is a database abstraction layer, not a full ORM. GORM\'s guide calls it an ORM library for Go; DALgo gives the same record calls on SQL and on other stores, such as memory and Firestore. The core module has a small <code>orm</code> package that maps collections and fields onto DALgo collection references and conditions. <a href="/articles/dalgo-vs-gorm/">DALgo vs GORM</a> compares the two.'),
        ("Which databases does DALgo support?",
         'The core module includes <code>dalgo2memory</code> (in memory) and <code>dalgo2fs</code> (filesystem). The README lists separate adapter modules for SQL engines through <code>dalgo2sql</code>, PostgreSQL, SQLite, MySQL, Microsoft SQL Server, Oracle, Firestore, Datastore, MongoDB, Redis, DynamoDB and more. Each adapter supports different operations; the <a href="/adapters/">adapter matrix</a> lists them one by one.'),
        ("Is DALgo open-source, and under what licence?",
         f'Yes. The Go module is <a href="{GO}">dal-go/dalgo</a> under the <a href="{GO_LICENSE}">MIT License</a>. The TypeScript package <code>@dalgo/core</code> is <a href="{TS}">dal-go/dalgo-js</a>, also under the <a href="{TS_LICENSE}">MIT License</a>.'),
        ("Does DALgo support transactions?",
         'Yes. <code>RunReadonlyTransaction</code> runs a function with read access, and <code>RunReadwriteTransaction</code> runs one that can also write. With typed collections, reads take a read session and writes take a write session, so writes are only reachable inside <code>RunReadwriteTransaction</code>. See <a href="/interfaces/">Interfaces</a>.'),
        ("How do I test code without a real database?",
         'Use <code>dalgo2memory</code>, the built-in in-memory adapter: <code>dalgo2memory.NewDB()</code> returns a database that runs the same record, query and transaction code. The README says it can run many structured query features end to end, which makes it a practical default for unit tests. The <a href="/quickstart/">Quick Start</a> starts with it.'),
        ("What happens when an adapter does not support a feature?",
         'The adapter returns <code>dal.ErrNotSupported</code>. DALgo does not try to hide every database difference; the error keeps the core API honest. The <a href="/adapters/">adapter matrix</a> shows which operations each adapter supports.'),
        ("How do I install DALgo?",
         'For Go, run <code>go get github.com/dal-go/dalgo</code>, then add the adapter module for your database. For TypeScript, run <code>pnpm add @dalgo/core</code>; the core package does not connect to a database by itself, so you add an adapter too. See the <a href="/quickstart/">Quick Start</a>.'),
        ("Is there a TypeScript version of DALgo?",
         f'Yes. <a href="{TS}"><code>@dalgo/core</code></a> is the browser-neutral TypeScript implementation, with hierarchical keys, typed collections, structured queries, records, database sessions and transaction-only writes. Its first adapter is for Firestore and uses Firebase\'s modular Web SDK in the browser. See <a href="/typescript/">DALgo for TypeScript</a>.'),
        ("Does DALgo work with Firestore?",
         'Yes. In Go, the <code>dalgo2firestore</code> adapter connects DALgo to Cloud Firestore. <a href="/articles/go-firestore-tutorial/">Firestore in Go: CRUD and transactions with DALgo</a> creates, reads, updates and deletes a document and runs a read-write transaction, and runs the same functions on the in-memory adapter in tests.'),
        ("Can I switch a Go service from PostgreSQL to Firestore without rewriting business code?",
         'Yes, for the record operations both adapters implement. Write the domain against <code>dal.DB</code>, open <code>dalgo2postgres</code> or <code>dalgo2firestore</code> in <code>main</code>, and use <code>dalgo2memory</code> in tests. <a href="/articles/switch-postgres-to-firestore/">Switching between PostgreSQL and Firestore in Go without rewriting business code</a> walks through a users repository, what stays the same, and what still differs (schema, joins, transactions).'),
        ("When should I not use DALgo?",
         'DALgo earns its place when the same domain code must run against more than one store, including a test double. It is the wrong tool when the engine\'s own query language is the product. <a href="/articles/when-to-use-dalgo/">When to use DALgo, and when not to</a> lists the cases.'),
        ("What is TugQL?",
         'TugQL is a readable YAML format for DALgo structured queries. Its Go implementation is the <code>tugql</code> package in the main module, which serializes <code>dal.StructuredQuery</code>. See <a href="/tugql/">TugQL</a>.'),
        ("Who maintains DALgo?",
         f'DALgo is developed in the <a href="https://github.com/dal-go">dal-go</a> GitHub organization by the DALgo contributors; <a href="{CONTRIBUTING}">CONTRIBUTING.md</a> explains how to contribute. DALgo provides the data-access seam in DataTug\'s development ecosystem, and Sneat Go services also depend on the module. See <a href="/about/tech-stack/">Technology behind DALgo</a>.'),
    ],
    "ru": [
        ("Что такое DALgo?",
         f'DALgo — слой абстракции базы данных для приложений на Go. В <a href="{GO}">README</a> он описан как небольшой единый API для записей, запросов, транзакций, хуков и отображения ключей по схеме, а хранилище остаётся деталью реализации. Реализация на TypeScript, <code>@dalgo/core</code>, живёт в отдельном репозитории. Подробнее: <a href="/ru/go/">DALgo для Go</a>.'),
        ("DALgo — это ORM?",
         'DALgo — слой абстракции базы данных, а не полноценная ORM. Руководство GORM называет его ORM-библиотекой для Go; DALgo даёт одни и те же вызовы для записей в SQL и в других хранилищах, например в памяти и в Firestore. В основном модуле есть небольшой пакет <code>orm</code>, который связывает коллекции и поля со ссылками на коллекции и условиями DALgo. Сравнение — в статье <a href="/articles/dalgo-vs-gorm/">DALgo vs GORM</a> (англ.).'),
        ("Какие базы данных поддерживает DALgo?",
         'В основной модуль входят <code>dalgo2memory</code> (в памяти) и <code>dalgo2fs</code> (файловая система). README перечисляет отдельные модули адаптеров: SQL-движки через <code>dalgo2sql</code>, PostgreSQL, SQLite, MySQL, Microsoft SQL Server, Oracle, Firestore, Datastore, MongoDB, Redis, DynamoDB и другие. Адаптеры поддерживают разные операции; <a href="/ru/adapters/">таблица адаптеров</a> показывает их по отдельности.'),
        ("DALgo — открытый исходный код? Какая лицензия?",
         f'Да. Модуль Go — <a href="{GO}">dal-go/dalgo</a> под <a href="{GO_LICENSE}">лицензией MIT</a>. Пакет TypeScript <code>@dalgo/core</code> — <a href="{TS}">dal-go/dalgo-js</a>, тоже под <a href="{TS_LICENSE}">лицензией MIT</a>.'),
        ("Поддерживает ли DALgo транзакции?",
         'Да. <code>RunReadonlyTransaction</code> выполняет функцию с доступом на чтение, а <code>RunReadwriteTransaction</code> — с доступом и на запись. В типизированных коллекциях чтение принимает сессию чтения, а запись — сессию записи, поэтому записать можно только внутри <code>RunReadwriteTransaction</code>. Подробнее: <a href="/ru/interfaces/">Интерфейсы</a>.'),
        ("Как тестировать код без настоящей базы данных?",
         'Используйте <code>dalgo2memory</code>, встроенный адаптер в памяти: <code>dalgo2memory.NewDB()</code> возвращает базу, на которой работает тот же код записей, запросов и транзакций. По README он выполняет многие возможности структурированных запросов целиком, поэтому подходит по умолчанию для модульных тестов. <a href="/ru/quickstart/">Быстрый старт</a> начинается с него.'),
        ("Что будет, если адаптер не поддерживает возможность?",
         'Адаптер вернёт <code>dal.ErrNotSupported</code>. DALgo не пытается скрыть все различия баз данных; эта ошибка сохраняет основной API честным. <a href="/ru/adapters/">Таблица адаптеров</a> показывает, какие операции поддерживает каждый адаптер.'),
        ("Как установить DALgo?",
         'Для Go выполните <code>go get github.com/dal-go/dalgo</code> и добавьте модуль адаптера для своей базы данных. Для TypeScript выполните <code>pnpm add @dalgo/core</code>; сам пакет к базе не подключается, поэтому нужен ещё адаптер. Подробнее: <a href="/ru/quickstart/">Быстрый старт</a>.'),
        ("Есть ли версия DALgo для TypeScript?",
         f'Да. <a href="{TS}"><code>@dalgo/core</code></a> — реализация на TypeScript, не привязанная к браузеру или серверу: иерархические ключи, типизированные коллекции, структурированные запросы, записи, сессии базы данных и запись только в транзакциях. Первый адаптер — для Firestore, он работает в браузере через модульный Web SDK Firebase. Подробнее: <a href="/ru/typescript/">DALgo для TypeScript</a>.'),
        ("Работает ли DALgo с Firestore?",
         'Да. В Go адаптер <code>dalgo2firestore</code> подключает DALgo к Cloud Firestore. В статье <a href="/articles/go-firestore-tutorial/">Firestore in Go: CRUD and transactions with DALgo</a> (англ.) документ создаётся, читается, изменяется и удаляется, выполняется транзакция чтения и записи, а те же функции в тестах работают на адаптере в памяти.'),
        ("Можно ли перевести сервис на Go с PostgreSQL на Firestore, не переписывая бизнес-код?",
         'Да, для операций с записями, которые реализуют оба адаптера. Пишите предметный код против <code>dal.DB</code>, в <code>main</code> открывайте <code>dalgo2postgres</code> или <code>dalgo2firestore</code>, а в тестах используйте <code>dalgo2memory</code>. Разбор — в статье <a href="/articles/switch-postgres-to-firestore/">Switching between PostgreSQL and Firestore in Go without rewriting business code</a> (англ.): репозиторий пользователей, что остаётся общим и чем хранилища всё же различаются (схема, соединения, транзакции).'),
        ("Когда DALgo не нужен?",
         'DALgo оправдан, когда один и тот же код предметной области должен работать с несколькими хранилищами, включая тестовую замену. Он не подходит, когда сам язык запросов движка и есть продукт. Случаи перечислены в статье <a href="/articles/when-to-use-dalgo/">When to use DALgo, and when not to</a> (англ.).'),
        ("Что такое TugQL?",
         'TugQL — читаемый формат YAML для структурированных запросов DALgo. Его реализация на Go — пакет <code>tugql</code> в основном модуле, он сериализует <code>dal.StructuredQuery</code>. Подробнее: <a href="/tugql/">TugQL</a> (англ.).'),
        ("Кто поддерживает DALgo?",
         f'DALgo разрабатывают участники DALgo в организации <a href="https://github.com/dal-go">dal-go</a> на GitHub; как внести вклад, описано в <a href="{CONTRIBUTING}">CONTRIBUTING.md</a>. DALgo служит слоем доступа к данным в инструментах разработки DataTug, а сервисы Sneat на Go тоже зависят от этого модуля. Подробнее: <a href="/ru/about/tech-stack/">Технологии DALgo</a>.'),
    ],
}


def plain(markup: str) -> str:
    """Visible text of an answer, as a browser shows it and the JSON-LD repeats it."""
    return html.unescape(re.sub(r"<[^>]+>", "", markup))


def faq_ld(locale: str) -> dict:
    return {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "inLanguage": locale,
        "mainEntity": [
            {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": plain(a)}}
            for q, a in QA[locale]
        ],
    }


def faq_body(locale: str, heading: str) -> str:
    items = "".join(
        f'<section class="faq-item"><h2 id="q{index}">{html.escape(q)}</h2><p>{a}</p></section>'
        for index, (q, a) in enumerate(QA[locale], start=1)
    )
    return f"<h1>{html.escape(heading)}</h1>\n<p>{INTRO[locale]}</p>\n{items}"


def markdown_answer(markup: str, site: str = "https://dalgo.io") -> str:
    """An answer as Markdown with absolute links, for llms-full.txt."""
    def link(match: re.Match) -> str:
        url = match[1] if match[1].startswith("http") else site + match[1]
        return f"[{plain(match[2])}]({url})"

    text = re.sub(r'<a href="([^"]+)">(.*?)</a>', link, markup)
    text = re.sub(r"</?code>", "`", text)
    return plain(text)


def llms_faq(locale: str) -> str:
    return "\n\n".join(f"### {q}\n\n{markdown_answer(a)}" for q, a in QA[locale])
