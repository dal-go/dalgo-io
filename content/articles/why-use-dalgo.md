---
title: Why use DALgo
slug: why-use-dalgo
date: 2026-10-27
description: What DALgo gives Go and TypeScript applications — one record, query, and transaction API across real adapters — and the limits it refuses to hide.
summary: DALgo keeps domain code on one record, query, and transaction API while the storage backend stays replaceable. This is the case for it, grounded in the modules and the projects that already sit on that seam.
order: 1
---

DALgo is a database abstraction layer. The Go module, [`github.com/dal-go/dalgo`](https://github.com/dal-go/dalgo), is the one production services import. A separate TypeScript package, [`@dalgo/core`](https://github.com/dal-go/dalgo-js), carries the same idea into browser and Node code: hierarchical keys, typed collections, structured queries, and transaction-scoped writes, with no database SDK of its own. Adapters are the part that knows Firestore, Postgres, SQLite, a Git working tree, or an HTTP API.

The point of the split is ordinary. Application code spends years naming records, reading them back, and updating them inside a transaction. Those operations do not have to name `*sql.DB`, a Firestore client, or an HTTP route. When they don't, the storage choice can move without a rewrite of the domain, and the test suite can run against a stand-in that speaks the same interface.

That is the whole pitch. The rest of this article is what the repositories actually ship, and where teams in the same orbit already use it. The companion article, [When to use DALgo, and when not to](/articles/when-to-use-dalgo/), is the other half: the jobs this layer should not be given.

## The seam you program against

Most application code should accept `dal.DB`, `dal.ReadSession`, or `dal.ReadwriteSession`, and never a concrete adapter. `dal.DB` is the database handle: identity, schema metadata, transactions, and reads. It is built with `dal.NewDB` from an adapter's `dal.Backend`, and it owns the write pipeline, so validation and before-save hooks run before any adapter is entered. An adapter cannot quietly skip them, and two adapters cannot disagree about whether a write was checked.

Day-to-day CRUD can sit on a generic, session-less `dal.Collection[K, T]`. The handle holds no connection, so it can live as a package-level variable. Reads take a `ReadSession` and return `T`. Writes take a `WriteSession`, which means a write that is handed a plain `dal.DB` is a compile error. The transaction callback is where mutation is allowed.

```go
type User struct {
    Name  string
    Email string
}

func (User) CollectionName() string { return "users" }

var Users = dal.CollectionOf[string, User]()

func GetUser(ctx context.Context, db dal.DB, id string) (User, error) {
    return Users.GetData(ctx, db, id)
}
```

That function is the same whether `db` was opened with the in-memory adapter, Firestore, SQL, or a filesystem. The core README shows the same shape against `database/sql`, where the function knows the table, the placeholder, and `sql.ErrNoRows`. The DALgo version knows a collection name and an id. Missing rows come back through `dal.IsNotFound`.

Keys can be hierarchical (`countries/ireland/cities/dublin`), which is the natural shape for Firestore-style data and also how a SQL adapter maps a parent into columns. Queries are a structured builder — filters, order, limit, projection, grouping, aggregates, inner and left equi-joins — plus [TugQL](/tugql/), a YAML serialization of that query so a saved query can round-trip without being a string of SQL dialect.

Transactions are callbacks. The adapter owns begin, commit, retry, and rollback. The callback receives a session and returns an error.

```go
err := db.RunReadwriteTransaction(ctx, func(ctx context.Context, tx dal.ReadwriteTransaction) error {
    return Users.SetByID(ctx, tx, "u1", User{Name: "Ada", Email: "ada@example.com"})
})
```

A record whose data implements `Validate() error` is validated on `Insert`, `Set`, `UpdateRecord`, and the multi-record variants before any row is written. A batch that fails validation writes nothing. `dal.WithoutValidation` is the explicit opt-out for a repair or a bulk import, and it is visible at the call site. Hooks still run.

## What you get for taking the dependency

**One vocabulary for records, queries, and transactions.** Driver-specific types stay inside the adapter. Domain packages, HTTP handlers, and job workers talk about keys, records, updates, and sessions. That is a readability win on its own, before anyone swaps a database. The same call shape is also what makes a review possible: a write outside a transaction, or a read of a path the caller should not see, has one place to be illegal.

**A real test double, not a pile of hand-written fakes.** `dalgo2memory` ships in the core module. The project describes it as the store for tests, examples, and local development, and as something that can run many structured-query features end to end, including schema registration and typed records. Generated mocks for the interfaces live in the core `mocks` package. The older standalone `mocks4dalgo` repository is archived. Shared scenarios live in the core `end2end` package; the standalone `dalgo-end2end-tests` repository is archived too.

**A place to put policy, once.** Access policies wrap any adapter and run before the adapter sees a get, an exists check, a query, a mutation, or a transaction. `Get`, `Exists`, and `Query` are separate read capabilities. `Insert`, `Set`, `Update`, `Delete`, and a reserved `Truncate` are separate write capabilities. Write access does not imply read access. A secured handle with no policy in force denies every request. Rules are default-deny, hierarchical, and intersecting: adding another policy can only narrow authority. A denial comes back as an `access.DeniedError` that names the operation, the resource, the policy, and the rule. Policies load from YAML or JSON via an `io.Reader`. The same wrapper is what the project recommends for extension code, tenants, jobs, and support tools. Sneat's Go core uses a related idea at the edge: `facade.ProtectSneatDB` applies a reviewed root-collection registry when `db.Adapter().Name()` is `"firestore"`, and returns any other adapter untouched, so a non-Firestore deployment keeps its own layout.

**Explicit failure when a backend cannot do the thing.** The core README states the rule directly: DALgo does not try to hide every database difference. An adapter returns `dal.ErrNotSupported` for a capability it does not have. Callers can share one query shape in tests and skip, or fail, when a store cannot run it. That is less convenient than an ORM that silently rewrites your query into something else. It is also how the abstraction stays honest. The next article is about living with that rule.

**SQL engines keep their own compilers where it matters.** [`dalgo2sql`](https://github.com/dal-go/dalgo2sql) is the shared SQL adapter. Its own README describes a SQLite structured emitter and a typed compiler for PostgreSQL, MySQL, Oracle, and SQL Server. With a dialect set, values are bound parameters and identifiers are quoted. [`dalgo2postgres`](https://github.com/dal-go/dalgo2postgres) forces the `postgres` dialect in its constructors, so a structured query on that handle cannot fall through to the legacy text emitter, which interpolates values into SQL text. Engine-specific modules add the parts a portable interface cannot invent: `dalgo2postgres` introspects catalogs and applies Postgres DDL; `dalgo2sqlite` reports `Concurrency() = 1` on the write path because SQLite has a single writer, and it introspects `sqlite_master`. The `dalgo2sqlite` README names DataTug's `db copy` as the kind of consumer that wants schema changes and concurrency hints through this API rather than a hand-rolled `CREATE TABLE` per engine.

**Stores that are not a hosted database still fit the same calls.** The dal-go organization also publishes adapters whose backends are files, Git, HTTP, or a vendor API:

- The built-in `dalgo2fs` for filesystem persistence, and [`dalgo2files`](https://github.com/dal-go/dalgo2files), which today is read-only and handles JSON files only.
- [`dalgo2openvaultdb`](https://github.com/dal-go/dalgo2openvaultdb) for the OpenVaultDB HTTP API.
- [`ingitdb/dalgo2ingitdb`](https://github.com/ingitdb/dalgo2ingitdb), [`dalgo2ingitdb4local`](https://github.com/ingitdb/dalgo2ingitdb4local), and [`dalgo2ingitdb4github`](https://github.com/ingitdb/dalgo2ingitdb4github) for [inGitDB](https://github.com/ingitdb/ingitdb) projects on a local tree or through the GitHub API.
- Narrower modules whose descriptions are the feature: read-only Cloudflare D1 (`dalgo2d1`), read-only HTTP/JSON (`dalgo2http`), bounded local log files (`dalgo2logs`), Namecheap domains and DNS records (`dalgo2namecheap`), bounded BigQuery reads (`dalgo2bigquery`), and a DuckDB driver (`dalgo2duckdb`).

The BuntDB and BadgerDB adapters are archived and deprecated. They are not current targets.

The TypeScript side is a catalog as much as a runtime. [`dalgo-http-adapters`](https://github.com/dal-go/dalgo-http-adapters) qualifies which HTTP data planes can preserve DALgo semantics and which must fail closed. `@dalgo/firestore` is the reference adapter and is aimed at the browser, because Firebase Auth and Security Rules are built for public clients. The package README is explicit that a long-lived database credential does not belong in a browser, and that several products in the matrix are HTTP-capable only from a trusted runtime. Older standalone JavaScript adapter repositories were archived as that catalog took over.

## Where this is already the architecture

These are public repositories, read in October 2026. They are not a customer list, and they are not independent benchmarks. They are the projects that publish how they sit on the interface.

**Sneat.** [`sneat-go-core`](https://github.com/sneat-co/sneat-go-core) exposes `facade.GetSneatDB(ctx) (dal.DB, error)`. Since v0.60.3 that function is not a reassignable package variable. Tests and request-scoped code inject a database with `facade.WithSneatDB` or `facade.WithSneatDBProvider`, which is safe under `go test` parallelism. Production wiring sets a default provider at startup. `ProtectSneatDB` then wraps Firestore handles with the reviewed collection registry and leaves every other adapter alone.

The Sneat CLI uses that seam in a concrete way. Its convo sandbox comment says the facades stay storage-agnostic and always go through `facade.GetSneatDB`; only the wiring picks the driver. `SNEAT_STORAGE` selects `dalgo2memory` (the default, constructed with a Firestore profile so the stand-in follows the production backend) or `dalgo2openvaultdb` pointed at `ovdb serve`. The same CLI also opens user Firestore through `dalgo2firestore` for read paths, and that package deliberately does not hand callers a full `dal.DB`. It keeps a read-only transaction runner, because a read-write handle would be a wider escape hatch than those callers need. Both facts belong in the picture: the interface is what makes the swap possible, and teams still narrow it at the edge.

**OpenVaultDB.** [OpenVaultDB](https://github.com/openvaultdb/openvaultdb) is a user-controlled vault: schemas, narrow capabilities, and storage that the user can move. The Go library's README states the MVP goal in one diagram:

```text
sneat-cli → Sneat facades → DALgo → dalgo2openvaultdb → OpenVaultDB HTTP → SQLite | inGitDB
```

The server stores records in a SQLite file or an inGitDB tree and exposes one JSON HTTP API. The driver speaks that API with the standard library HTTP client. A Go program that already has a `dal.DB` can be pointed at it without a second data-access stack. The driver's README is also a capability table: point reads, batch writes inside a transaction, and a structured query subset are supported; cursors, offsets, `GROUP BY`, collection-group queries, and update preconditions return `dal.ErrNotSupported`. Direct field projections are applied in the client after the HTTP response, so they do not shrink the payload. That table is the practical meaning of "the business logic did not change."

**inGitDB.** [inGitDB](https://github.com/ingitdb/ingitdb) is a Git-backed database: collections as text files, history as commits, branches as branches. It is not DALgo. DALgo is one client interface over it. `ingitdb-cli` requires the core module plus `dalgo2ingitdb`, `dalgo2ingitdb4local`, and `dalgo2ingitdb4github`. The local adapter can enforce owner access policies from `.ingitdb/access/manifest.yaml`, using the portable `tugql.org/access/v1` format, and can publish an immutable policy generation as its own Git commit. `dalgo2git`, in the dal-go organization, is a separate and thinner driver: versioned storage in a Git repository. Treat them as different backends that happen to share a theme.

**DataTug.** [DataTug](https://github.com/datatug/datatug) is a context-aware exploration environment across operational sources, with project files stored as Git-native content. The DALgo README describes DALgo as the data-access seam in that development ecosystem, and the TypeScript README says DataTug's current DALgo work uses the Go implementation, with `@dalgo/core` remaining a separate codebase. Separately, the [`datatug-apps`](https://github.com/datatug/datatug-apps) workspace manifest depends on `@dalgo/core`, `@dalgo/indexeddb`, `@dalgo/ovdb`, `@dalgo/sqlite-sql`, and `@dalgo/sqlite-wasm`, pinned to git revisions. OpenVaultDB's own README describes DataTug session storage on OpenVaultDB as architecture still in progress. Taken together, DataTug is a consumer and a reason the query format (TugQL) and several adapters exist. It is not evidence that every DataTug screen runs through one adapter.

**Listus and bots.** The Listus backend module (`github.com/sneat-co/listus/backend`) requires `github.com/dal-go/dalgo`. The Go chatbot framework [`bots-fw`](https://github.com/bots-go-framework/bots-fw) no longer depends on DALgo in its core module. Persistence sits behind a small `StateStore` port. [`bots-fw-store-dalgo`](https://github.com/bots-go-framework/bots-fw-store-dalgo) is the optional implementation of that port: it keeps the historical keys (`botPlatforms/{platform}/botUsers/{user}`, and chats nested under a bot), writes partial field updates so different services do not wipe each other's fields on a shared platform-user document, and commits the application user, the platform link, and the chat in one adapter-owned transaction. The framework's `WebhookContext` has no `DB()` method. That is a mature way to use the layer. Domain code depends on a port sized to the use case. DALgo is the implementation of the port, present in the process that needs it.

## Why the TypeScript family is part of the same story

`@dalgo/core` does not open a connection. An application adds an adapter that implements the current core contracts. The Firestore Web SDK adapter is the one the repository points to first, and it runs in the browser. Collection paths use the same parent-key model as Go (`items` inside `spaces/{id}`), and collection-group queries are an explicit constructor rather than a side effect of naming a collection.

The two implementations are not drop-in ports of each other. The TypeScript README's adapter inventory says the generic JOIN executor scans each relation through `QueryExecutor.query`, and that several adapters, including current-core Firestore and IndexedDB, do not yet have JOIN integration tests. Adapters still importing the legacy `@dal-go/dalgo` package are a second module identity; mixing them with `@dalgo/core` installs two cores. DataTug's published note that its current DALgo work is on the Go side is consistent with that gap. Use the TypeScript stack where the program actually runs in JavaScript and the adapter you import documents the operations you call. Use the Go module where the service is Go.

## A bounded promise

DALgo is MIT-licensed. The core repository asks contributors to keep the public API stable under semantic versioning, and it still publishes v0 releases (the core README and downstream `go.mod` files in October 2026 pin versions in the v0.9x line, and not all on the same patch). Pin the module. Read the adapter README for the dialect and the error you will actually get.

If the code you are about to write will run against more than one of these backends, including a memory stand-in in tests, the interface is the thing you are buying: less driver boilerplate, one policy and validation pipeline, and a compile-time reminder that writes happen inside a transaction. If the code exists to use one engine's own language as far as it will go, read the next article before adding the dependency.

## Sources

Public default branches and repository metadata, read on 27 October 2026.

- [dal-go/dalgo](https://github.com/dal-go/dalgo) README, access-policy guide, hooks documentation, and `end2end` / `mocks` layout. License: MIT.
- [dal-go/dalgo-js](https://github.com/dal-go/dalgo-js) and [dal-go/dalgo-http-adapters](https://github.com/dal-go/dalgo-http-adapters).
- [dal-go/dalgo2sql](https://github.com/dal-go/dalgo2sql), [dalgo2postgres](https://github.com/dal-go/dalgo2postgres), [dalgo2sqlite](https://github.com/dal-go/dalgo2sqlite), [dalgo2firestore](https://github.com/dal-go/dalgo2firestore), [dalgo2openvaultdb](https://github.com/dal-go/dalgo2openvaultdb).
- [sneat-co/sneat-go-core](https://github.com/sneat-co/sneat-go-core) `facade/get_sneat_db.go` and `facade/root_policy.go`. [sneat-co/sneat-cli](https://github.com/sneat-co/sneat-cli) `cmd/sneat/commands/convo_storage.go` and `internal/firestoredb/firestoredb.go`.
- [openvaultdb/openvaultdb](https://github.com/openvaultdb/openvaultdb) and [openvaultdb/openvaultdb-go](https://github.com/openvaultdb/openvaultdb-go).
- [ingitdb/ingitdb](https://github.com/ingitdb/ingitdb), [ingitdb/ingitdb-cli](https://github.com/ingitdb/ingitdb-cli), [ingitdb/dalgo2ingitdb](https://github.com/ingitdb/dalgo2ingitdb).
- [datatug/datatug](https://github.com/datatug/datatug) and the `datatug-apps` workspace `package.json`.
- [sneat-co/listus](https://github.com/sneat-co/listus) `backend/go.mod`.
- [bots-go-framework/bots-fw](https://github.com/bots-go-framework/bots-fw) `PERSISTENCE.md` and [bots-fw-store-dalgo](https://github.com/bots-go-framework/bots-fw-store-dalgo).
