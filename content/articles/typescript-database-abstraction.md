---
title: Database abstraction layer for TypeScript: @dalgo/core
slug: typescript-database-abstraction
date: 2026-11-27
description: TypeScript database abstraction layer explained: how @dalgo/core models records, queries, and transactions, and where Prisma or Drizzle fit better.
summary: What a database abstraction layer is in TypeScript, how @dalgo/core models records, queries, and transactions for browser and server code, a type-checked example, and an honest comparison with Prisma, Drizzle ORM, TypeORM, and Kysely.
order: 1
schema: techarticle
dependencies: TypeScript
---

[DALgo](/) is an [open-source](https://github.com/dal-go/dalgo-js) database abstraction layer for [Go](https://go.dev/) and [TypeScript](https://www.typescriptlang.org/). A database abstraction layer, or DAL, is a library that sits between application code and a database, so the program can store and load records without calling one vendor's client. An adapter is the package that connects that interface to one particular database or runtime. [`@dalgo/core`](https://github.com/dal-go/dalgo-js) is DALgo's TypeScript package: it defines keys, typed collections, structured queries, records, and transaction contracts, and it does not connect to a database by itself. It is published on [npm](https://www.npmjs.com/package/@dalgo/core), the package registry for JavaScript, as an [ECMAScript module](https://developer.mozilla.org/docs/Web/JavaScript/Guide/Modules) (ESM) under the [MIT license](https://github.com/dal-go/dalgo-js/blob/main/LICENSE). Other terms on this page: an ORM is an object-relational mapper, a library that maps program objects to rows of a relational database; SQL is Structured Query Language, the language relational databases use for queries; CRUD is create, read, update, and delete, the four basic record operations; and an SDK is a software development kit, such as the Firebase library a Firestore app imports.

This page is an explainer, not the product overview: the [DALgo for TypeScript](/typescript/) page is that, and the [adapter matrix](/adapters/) is the inventory of what each adapter implements. The Go side of the same idea is in [Database abstraction layer in Go](/articles/go-database-abstraction-layer/), and [Go ORM and data-access libraries compared (2026)](/articles/go-orm-comparison-2026/) is the Go counterpart of the comparison below. The [quickstart](/quickstart/) and the [FAQ](/faq/) are the shorter product pages.

## What a database abstraction layer does in TypeScript

A TypeScript program usually reaches a database through a vendor library: the Firebase SDK for Firestore, `indexedDB` in the browser, a SQL driver on a server. A database abstraction layer puts one small interface in front of those libraries, so the code that decides what to store depends on the interface and only the start-up code names a vendor. That is the whole idea. It solves three practical problems:

- **One interface over several databases.** The same function can read a record whether the adapter behind it is IndexedDB or Firestore, as long as it uses only operations both adapters implement.
- **Browser and server code that shares logic.** The package is browser-neutral: it has no database SDK of its own and no Node-only imports, so the same domain code can be bundled for the browser or run in Node. The package declares Node 20 or later.
- **Testability.** Application code that accepts the interface can be given a different adapter in a test. The IndexedDB adapter, for example, accepts an injected `IDBFactory`, which is how the example below ran under Node.

A layer like this does not remove the differences between databases. It hides vendor client code, not the engine. An operation an adapter cannot do has to fail explicitly, and the [adapter matrix](/adapters/) records which adapter does what.

## How @dalgo/core models it

Everything below is exported from `@dalgo/core` 0.9.0.

**Keys.** A `Key` is a collection name plus an id, optionally under a parent key, so a record can live at `spaces/{id}/items/{id}`. `key("spaces", id)` builds one. `Key.path` joins the segments, escaping `.`, `$`, `#`, `[`, `]`, and `/` inside ids. Ids are strings or finite numbers.

**Typed collections.** `collection<T>("todos")` returns a `Collection<T>`. `collection.key(id)` makes a key, `collection.in(parentKey)` scopes it under a parent, and `collection.query()` starts a query. `collectionGroup<T>("items")` is the explicit constructor for a query across every collection of that name. An optional `Codec<T>` with `encode` and `decode` can convert between your type and the stored value.

**Records.** A read returns a `RecordSnapshot<T>`: either `{ exists: true, key, data }` or `{ exists: false, key }`. TypeScript narrows on `exists`, so `data` is only readable when the record is there.

**Structured queries.** The builder is immutable. `where(field, operator, value)` takes one of `==`, `!=`, `<`, `<=`, `>`, `>=`, `in`, `not-in`, `array-contains`, and `array-contains-any`. `orderBy(field, "asc" | "desc")`, `limit(n)`, and `offset(n)` shape the result, and `startAt`, `startAfter`, `endAt`, and `endBefore` take cursor values. `build()` returns a plain `StructuredQuery<T>` object. A query returns a `QueryPage<T>` with `records` and an optional `nextCursor`. Whether an adapter accepts every operator, offset, or cursor is the adapter's decision: the Firestore adapter, for instance, rejects query offsets.

**Database and transactions.** The `Database` interface has `get`, `getMany`, `query`, and `runReadwriteTransaction`. Writes (`insert`, `set`, `update`, `delete`) exist only on the transaction object passed to that callback, which is what the README means by transaction-only mutation. There is no separate read-only transaction type in the TypeScript package; reads happen on the database itself or inside the read-write callback.

**Errors and capabilities.** The package defines `DalgoError`, `NotFoundError`, `AlreadyExistsError`, and `UnsupportedError`. A database may also implement the optional `CapabilityAware` interface, whose `capabilities()` reports `read`, `query`, `write`, `delete`, `reset`, and `persistent`; the source says to discover these at runtime rather than infer them from the engine name.

`@dalgo/core` also ships a text query language, [TugQL](/tugql/), with a parser and a generic join executor. That is a separate query model and is not covered here. The package README states that the generic executor scans each relation through `QueryExecutor.query`, and that the current-core Firestore and IndexedDB adapters have no JOIN integration tests, so do not assume joins from the core alone.

## Install

```text
npm install @dalgo/core @dalgo/indexeddb
```

`pnpm add @dalgo/core @dalgo/indexeddb` is the README's own form. The facts here were checked on 27 November 2026. [`@dalgo/core`](https://www.npmjs.com/package/@dalgo/core) 0.9.0 is the latest version on npm. It was built from commit [`2ed7cf775838`](https://github.com/dal-go/dalgo-js/commit/2ed7cf775838d4d4df884ffddea1a75b807d919e) of [dal-go/dalgo-js](https://github.com/dal-go/dalgo-js), the commit that the `core@v0.9.0` tag points to. It has one runtime dependency, [`yaml`](https://www.npmjs.com/package/yaml).

The published adapters at that date, `@dalgo/indexeddb` 0.4.1 and `@dalgo/firestore` 0.4.2, declare the peer range `@dalgo/core >=0.8.0 <0.9.0`. Because of that, the command above installed `@dalgo/core` 0.8.1 next to the adapter on that date, not 0.9.0. None of the adapters in the table list 0.9.0 yet. If you install 0.9.0 yourself, npm refuses to resolve it (ERESOLVE) and needs `--legacy-peer-deps`. The example below type-checks and runs on both 0.8.1 and 0.9.0; only 0.8.1 is inside the adapter's declared range. Read the adapter's README for the version it supports before you pin.

## A typed example that does not name a database

The first file knows about `Database` and a record type, and nothing about IndexedDB or Firestore. `addTodo` reads a record and inserts it inside one read-write transaction; `openTodos` runs a query.

```ts
import { collection, type Database } from "@dalgo/core";

export interface Todo {
  title: string;
  done: boolean;
  rank: number;
}

const todos = collection<Todo>("todos");

export async function addTodo(db: Database, id: string, todo: Todo): Promise<boolean> {
  return db.runReadwriteTransaction(async (transaction) => {
    const existing = await transaction.get<Todo>(todos.key(id));
    if (existing.exists) {
      return false;
    }
    await transaction.insert(todos.key(id), todo);
    return true;
  });
}

export async function openTodos(db: Database): Promise<readonly Todo[]> {
  const page = await db.query(
    todos.query().where("done", "==", false).orderBy("rank").limit(20).build(),
  );
  return page.records.map((record) => record.data);
}
```

The browser entry point picks the adapter. This is the only file that imports `@dalgo/indexeddb`:

```ts
import { IndexedDbDatabase } from "@dalgo/indexeddb";
import { addTodo, openTodos } from "./app.js";

const db = new IndexedDbDatabase({ name: "my-app" });
await addTodo(db, "first", { title: "Try DALgo", done: false, rank: 1 });
console.log(await openTodos(db));
await db.close();
```

Moving the same `app.ts` to Firestore changes only the entry point, using the Firebase SDK's `initializeApp` and `getFirestore`:

```ts
import { initializeApp } from "firebase/app";
import { getFirestore } from "firebase/firestore";
import { FirestoreDatabase } from "@dalgo/firestore";
import { addTodo, openTodos } from "./app.js";

const db = new FirestoreDatabase(getFirestore(initializeApp({ projectId: "my-project" })));
await addTodo(db, "first", { title: "Try DALgo", done: false, rank: 1 });
console.log(await openTodos(db));
```

What was and was not checked. All three files were type-checked under TypeScript's `strict` mode against `@dalgo/core` 0.8.1 and 0.9.0, `@dalgo/indexeddb` 0.4.1, `@dalgo/firestore` 0.4.2, and `firebase` 13.4.0. The first file and the IndexedDB entry point were also run under Node 24 with an injected `fake-indexeddb` factory: the first `addTodo` returned `true`, a second call with the same id returned `false`, and `openTodos` returned the two records with `done: false`, ordered by `rank`. The Firestore entry point was type-checked only; it was not run against Firestore or its emulator. In a real browser the IndexedDB constructor uses the global `indexedDB`, and the adapter README says its transaction callback should await only DALgo operations.

"Unchanged calling code" holds for the operations both adapters implement. It does not make the stores equal. Firestore applies its own security rules and rejects query offsets, while the IndexedDB adapter evaluates filters and ordering as records arrive and can scan the whole collection. Treat the matrix and each adapter's README as the contract.

## TypeScript adapters and where they run

Adapter work for TypeScript lives in [dalgo-http-adapters](https://github.com/dal-go/dalgo-http-adapters). Earlier standalone repositories for these adapters are archived; see the legacy repositories list. The table lists adapters whose npm package and README were read on 27 November 2026. It is not a complete list, and this page does not count adapters.

| Package | Version on npm | Runs in | What its README says |
| --- | --- | --- | --- |
| [`@dalgo/indexeddb`](https://github.com/dal-go/dalgo-http-adapters/tree/main/packages/indexeddb) | 0.4.1 | Browser | Native IndexedDB persistence; real read-write transactions; same-origin only. |
| [`@dalgo/firestore`](https://github.com/dal-go/dalgo-http-adapters/tree/main/packages/firestore) | 0.4.2 | Browser, through Firebase's modular Web SDK | Called the reference adapter in the dalgo-http-adapters root README; needs the `firebase` peer. |
| [`@dalgo/sqlite-wasm`](https://github.com/dal-go/dalgo-http-adapters/tree/main/packages/sqlite-wasm) | 0.1.0 | Browser and Node | A read-write `Database` over one SQLite connection; peers on `@dalgo/sqlite-sql`. |
| [`@dalgo/bigquery`](https://github.com/dal-go/dalgo-http-adapters/tree/main/packages/bigquery) | 0.3.3 | Browser-compatible analytical entry | Read-only on the [adapter matrix](/adapters/); a record adapter plus a separate analytical export. |

The [adapter matrix](/adapters/) links each adapter to pinned source and says which runtime it applies to, and it is the page to read before you pick one. Its TypeScript rows were last audited on 1 November 2026, so check the matrix date against the npm version you install.

## How it compares with Prisma, Drizzle, TypeORM, and Kysely

These tools answer a different question from a database abstraction layer, and most of them are excellent at theirs. The claims below come from each project's own documentation, read on 27 November 2026. None of this is a benchmark, and the page makes no claim about speed, bundle size, or popularity.

| | What its docs call it | Databases its docs name | Where it fits better than DALgo |
| --- | --- | --- | --- |
| [Prisma ORM](https://www.prisma.io/docs/orm) | A typed data layer for TypeScript, with typed queries and migrations. | PostgreSQL, MongoDB, SQLite, and MySQL on the [overview](https://www.prisma.io/docs/orm), with more in the [supported databases](https://www.prisma.io/docs/orm/v7/core-concepts/supported-databases) page for version 7. Prisma ORM 8 is a release candidate; see its [release status](https://www.prisma.io/docs/orm/release-status) (updated 26 November 2026). | A server app with a modelled relational schema, generated types, and migrations. |
| [Drizzle ORM](https://orm.drizzle.team/docs/overview) | A headless TypeScript ORM with SQL-like and relational query APIs. | PostgreSQL, MySQL, SQLite, SingleStore, MSSQL, and CockroachDB drivers. | Teams that know SQL and want the schema in TypeScript and queries close to SQL. |
| [TypeORM](https://typeorm.io/) | An ORM for TypeScript with DataMapper and ActiveRecord patterns, a query builder, and migrations. | MySQL, PostgreSQL, MariaDB, SQLite, SQL Server, Oracle, MongoDB, and others. | Entity classes with decorators over a SQL database, including in the browser and on mobile platforms its docs list. |
| [Kysely](https://kysely.dev/) | A type-safe SQL query builder for TypeScript. | PostgreSQL, MySQL, SQL Server, SQLite, and PGlite built in; more through community dialects. | SQL-first code where compile-time checking of queries matters. See its [getting started](https://kysely.dev/docs/getting-started) guide. |
| [Firebase SDK](https://firebase.google.com/docs/firestore) | The Cloud Firestore client library for web, mobile, and server. | Cloud Firestore only. | An app that is committed to Firestore and wants its realtime listeners and offline support directly. |

Choose a SQL-first tool when the database engine is the product. If your code is relational, with joins, constraints, and migrations that you want generated from a schema, Prisma, Drizzle, TypeORM, and Kysely all give you that and `@dalgo/core` does not. DALgo's core has no schema language, no migrations, and no code generation; TugQL aside, it has no SQL builder and does not expose SQL.

Choose DALgo when the unit of work is a keyed record and the store may change. That is a browser app that keeps data in IndexedDB today and Firestore tomorrow, a codebase that shares record logic between browser and server, or a test that should not need the real database. The price is a smaller common denominator: operations an adapter cannot do fail, and the TypeScript package is at 0.x. TypeORM and Kysely both list browser support, so running in the browser alone is not what separates them. The difference is the model: tables and SQL on their side, keyed records and structured queries on this one.

These tools are not exclusive. A project can use Kysely or Prisma for its server's SQL database and still use `@dalgo/core` where a keyed-record interface helps. The Firebase SDK is not a rival either: the Firestore adapter is built on it.

## How it relates to the Go module

The Go module [`github.com/dal-go/dalgo`](https://github.com/dal-go/dalgo) and `@dalgo/core` share concepts: hierarchical keys, typed collections, structured queries, and transaction-scoped writes. They are separate codebases with no shared runtime, so a TypeScript program cannot call Go adapters and Go code cannot call TypeScript ones. Names differ: Go's handle is `dal.DB` and it has both `RunReadonlyTransaction` and `RunReadwriteTransaction`, while TypeScript's is `Database` and has `runReadwriteTransaction` only. [Database abstraction layer in Go](/articles/go-database-abstraction-layer/) shows the Go form, and [DALgo for TypeScript](/typescript/) is the product page for this one.

## FAQ

### What is a database abstraction layer in TypeScript?

A database abstraction layer is a library that sits between application code and a database, so the program can store and load records without calling one vendor's client. In TypeScript, `@dalgo/core` is one: it defines keys, collections, structured queries, and transactions, and an adapter connects them to a database such as IndexedDB or Firestore.

### Does @dalgo/core connect to a database by itself?

No. The package has no database SDK of its own and does not connect to a database. You install an adapter, such as `@dalgo/indexeddb` for the browser or `@dalgo/firestore` for Firestore through the Firebase Web SDK, and pass its database object to your code.

### Is @dalgo/core an ORM like Prisma, Drizzle, or TypeORM?

No. An ORM maps objects to rows of a relational database and usually brings a schema, migrations, or a SQL builder. `@dalgo/core` models keyed records, typed collections, and structured queries, and it has no schema language or migrations. TugQL aside, it has no SQL builder and does not expose SQL. Use a SQL-first tool when your data is relational; the [comparison above](/articles/typescript-database-abstraction/#how-it-compares-with-prisma-drizzle-typeorm-and-kysely) lists when each fits.

### Can I swap IndexedDB for Firestore without changing my code?

For the operations both adapters implement, yes: the example on this page keeps its domain code in one file that accepts a `Database`, and only the entry point changes. The two stores still differ. Firestore rejects query offsets and applies its own security rules, and each adapter's README states what it supports.

### Is @dalgo/core the same as the Go module?

No. They share concepts and are separate implementations. The Go module is `github.com/dal-go/dalgo`, and the TypeScript package is `@dalgo/core` from [dal-go/dalgo-js](https://github.com/dal-go/dalgo-js). Go adapters do not run in TypeScript, and the reverse.

## Sources

Public package metadata, documentation, and repository source, checked on 27 November 2026. This page is not a benchmark and reports no download counts, stars, or timings.

- [`@dalgo/core` on npm](https://www.npmjs.com/package/@dalgo/core) 0.9.0 (MIT, Node >=20, ESM, `gitHead` [`2ed7cf775838`](https://github.com/dal-go/dalgo-js/commit/2ed7cf775838d4d4df884ffddea1a75b807d919e)) and [dal-go/dalgo-js](https://github.com/dal-go/dalgo-js) at tag `core@v0.9.0`: the README, `CHANGELOG.md`, and `src/` (`key.ts`, `collection.ts`, `record.ts`, `query.ts`, `database.ts`, `errors.ts`, `capabilities.ts`). License: [MIT](https://github.com/dal-go/dalgo-js/blob/main/LICENSE).
- [dal-go/dalgo-http-adapters](https://github.com/dal-go/dalgo-http-adapters) with the READMEs and manifests of [`@dalgo/indexeddb`](https://www.npmjs.com/package/@dalgo/indexeddb) 0.4.1, [`@dalgo/firestore`](https://www.npmjs.com/package/@dalgo/firestore) 0.4.2, [`@dalgo/sqlite-wasm`](https://www.npmjs.com/package/@dalgo/sqlite-wasm) 0.1.0, and [`@dalgo/bigquery`](https://www.npmjs.com/package/@dalgo/bigquery) 0.3.3, and its [legacy repositories list](https://github.com/dal-go/dalgo-http-adapters/blob/main/LEGACY_REPOSITORIES.md).
- [Adapter matrix](/adapters/) and [DALgo for TypeScript](/typescript/).
- Prisma: [Prisma ORM documentation](https://www.prisma.io/docs/orm) (page dated 26 November 2026), [supported databases](https://www.prisma.io/docs/orm/v7/core-concepts/supported-databases), and [release status](https://www.prisma.io/docs/orm/release-status) (updated 26 November 2026).
- Drizzle: [Drizzle ORM overview](https://orm.drizzle.team/docs/overview).
- TypeORM: [typeorm.io](https://typeorm.io/).
- Kysely: [kysely.dev](https://kysely.dev/) and [getting started](https://kysely.dev/docs/getting-started).
- Firebase: [Cloud Firestore documentation](https://firebase.google.com/docs/firestore) (last updated 19 November 2026).
- [TypeScript](https://www.typescriptlang.org/), [ECMAScript modules (MDN)](https://developer.mozilla.org/docs/Web/JavaScript/Guide/Modules), [npm](https://www.npmjs.com/), and Wikipedia on [database abstraction layers](https://en.wikipedia.org/wiki/Database_abstraction_layer).
