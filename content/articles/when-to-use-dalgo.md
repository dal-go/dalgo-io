---
title: When to use DALgo, and when not to
slug: when-to-use-dalgo
date: 2026-10-27
description: An honest guide to the situations where DALgo is a good fit, and the situations where a database driver, SQL, or another tool should stay in charge.
summary: DALgo earns its place when the same domain code must run against more than one store, including a test double. It is the wrong tool when the engine's own language is the product.
order: 2
---

[Why use DALgo](/articles/why-use-dalgo/) describes the interface. This article is about the decision to take the dependency. The useful version of that decision is specific. DALgo is a shared path for records, queries, transactions, hooks, and policy. It is a poor substitute for a query planner, a warehouse, a search engine, or a driver API you intend to use in full.

Nothing below is a benchmark. Where a limit is named, it is named because an adapter README or a call site documents it.

## Use DALgo when the code has more than one backend

The clearest fit is a service whose domain already says `dal.DB`, and whose process is allowed to be pointed at a different adapter.

Sneat's CLI convo sandbox is a working example, and its scope is the sandbox, not every Sneat command. Facades call `facade.GetSneatDB`. `SNEAT_STORAGE=memory` (the default) builds `dalgo2memory` with a Firestore profile. `SNEAT_STORAGE=openvaultdb` builds `dalgo2openvaultdb` against `ovdb serve`, by default at `http://127.0.0.1:6832` and database id `sneat-dev`. The OpenVaultDB Go README draws the intended stack as `sneat-cli → Sneat facades → DALgo → dalgo2openvaultdb → OpenVaultDB HTTP → SQLite | inGitDB`, and describes the MVP as a proof that Sneat business logic can change storage backend without a rewrite. That is the job the abstraction is for: the facade stays put, the wiring changes.

The same shape fits a Go test. `dalgo2memory` lives in the core module and is documented as able to run a large part of the structured-query surface, so a test can exercise filters, order, and limits without a network. Sneat's core library stopped letting tests overwrite a package-level `GetSneatDB` variable. A test now puts a `dal.DB` on the context with `facade.WithSneatDB`. That is the pattern to copy: construct the adapter in the test or in `main`, inject the interface, and keep the domain ignorant of which one it received.

Use it, too, when several programs must share a record model. Listus's Go backend depends on the core module. The optional `bots-fw-store-dalgo` adapter maps a chatbot's platform users and chats onto DALgo keys and field updates, while the framework core depends only on a `StateStore` interface. inGitDB's CLI depends on three DALgo adapters — a local inGitDB project, a filesystem variant, and a GitHub API variant — so the same record operations can target whichever copy of the database the operator has. OpenVaultDB's driver exists so a program that already speaks DALgo can talk to a user-owned HTTP database without a second client stack.

A last positive case is cross-cutting behavior you want exactly once. Validation (`ValidatableRecord`) and before-save hooks run inside `dal.DB` before the adapter. Access policies are a wrapper that denies by default and can be loaded from YAML. If every new storage client would otherwise grow its own allow-list, audit log, and "is this write well-formed?" check, the wrapper is the feature.

## Use the driver when the engine is the product

Stay on `database/sql`, `pgx`, the Firestore SDK, or the warehouse's own client when the reason you picked that engine is a behavior DALgo will not represent.

**Hand-written SQL, explain plans, and engine features.** Structured DALgo queries cover filters, ordering, limits, projection, grouping, a set of aggregates, and inner and left equi-joins. They are not a host for window functions, recursive CTEs, full-text search, geospatial operators, or a hint you attach because you have read this table's plan. `dalgo2sql` can still be given SQL — the legacy path and the dialect compilers are for the structured builder — but a query that exists as SQL text the team reviews in `psql` does not become better by being rebuilt through a portable AST. Ship that query with the driver. The core README's own comparison is the right size of example for DALgo: get a user by id, ban a user inside one transaction. A reporting query with three vendor-specific functions is the wrong size.

**Untrusted input and the legacy SQL emitter.** If a `dalgo2sql` handle has no structured-query dialect and no native compiler, values are written into the SQL text. The core and `dalgo2sql` READMEs both say not to pass untrusted values through that emitter. `dalgo2postgres` refuses to be that handle: its constructors force the `postgres` dialect, and they error if the caller tries to replace the compiler. Prefer the engine module (`dalgo2postgres`, `dalgo2sqlite`, and the MySQL, SQL Server, and Oracle modules) over a raw `dalgo2sql` database left on the empty dialect. The core `docs/adapters.md` table still says MySQL, SQL Server, and Oracle have no compiler. The `dalgo2sql` tree does contain `dialect_mysql.go`, `dialect_oracle.go`, `dialect_sqlserver.go`, and golden files for each, and the adapter README documents those typed compilers. When the two documents disagree, trust the module you import, and treat a lagging core doc as a reason to read the adapter before promising a capability in a design review.

**Aggregates the planner refuses.** `dalgo2sql` documents that `FIRST` and `LAST` are not advertised for SQLite or PostgreSQL. Those dialects do not promise a stable row order inside a group, and the planner fails the query rather than executing an unspecified order. `SUM` and `AVG` on the SQLite structured path normalize to `REAL`, in line with DALgo's generic `float64` fallback. Exact decimal arithmetic is opt-in (`MoneyConfig` for federated queries, and `RegisterSQLiteDecimalFunctions` for SQL you issue yourself). If the business rule is "this total must be decimal text with a defined rounding mode," turn that mode on and test it. If you assume every `SUM` is a decimal, you have assumed past the default.

**Firestore features that are the SDK's.** `dalgo2firestore` is a bridge onto the Firestore API, including transaction-scoped query readers that use the transaction's snapshot. Realtime listeners, Security Rules as an authoring environment, and bundled mobile offline persistence are Firestore product features. Putting domain types behind `dal.DB` does not move those features into SQLite. Sneat's CLI shows the complementary discipline on the read path: `internal/firestoredb` wraps `dalgo2firestore.NewDatabase` and exposes `RunReadonlyTransaction` instead of the full `dal.DB`, because callers outside that package do not need a read-write escape hatch. Reach for the SDK, or for a narrow interface, when the full `dal.DB` is more power than the caller should have.

**Analytics warehouses.** `dalgo2bigquery` describes itself as bounded analytical reads: a compile step, a preview, an operator approval bound to cost and identity, then paged results. The TypeScript catalog classifies BigQuery the same way — an analytical adapter, not OLTP parity. GoogleSQL jobs, slot reservations, and load jobs are not something to hide behind `Get` and `Set`. Use the BigQuery client, or this bounded adapter, for what each one actually checks. Do not point a CRUD service at it and expect transaction semantics from a warehouse.

**Search, graph, time series, vectors, and Redis.** The TypeScript qualification matrix is unusually frank. Redis is marked not applicable: the management REST API is not the RESP data plane, and the catalog says not to confuse the two. MongoDB's browser Data API is retired, so there is no adapter for it. Elasticsearch, OpenSearch, Solr, Neo4j, InfluxDB, Pinecone, and Qdrant appear as HTTP-capable products with product-specific semantics, and the repository classifies most of them as private workspace packages rather than the public `@dalgo/firestore` / `@dalgo/indexeddb` / `@dalgo/bigquery` set. A Go module named `dalgo2redis` or `dalgo2spanner` was not in the dal-go organization at the time of writing. There is an App Engine memcache wrapper for DALgo transaction operations (`dalgo-memcache-appengine`); that is a cache beside a transaction, not a Redis-compatible database. If the data model is a graph traversal, a vector neighbor, or a key expiry, use the product that has that model.

**OpenVaultDB, past the supported table.** The `dalgo2openvaultdb` README is the right template for every adapter review. Supported: `Get`, `Exists`, `GetMulti`, transactions, `Set` / `Insert` / `Delete` / field `Update` inside a transaction, multi-writes, incomplete-key insert, and structured queries with a documented operator set. Unsupported, each with `dal.ErrNotSupported` or an explicit omission: update preconditions, recordset readers, cursors, `StartFrom`, `Offset`, expression and aggregate projections, `GROUP BY` / `HAVING`, collection-group queries, and cross-transaction isolation. Read-your-writes for `Update` inside the same transaction is resolved by the server in batch order, not by the client buffer that covers `Set` and `Insert`. A guarded-read mode for an operator-held bearer token goes further: only structured queries run, and only for a matching principal; `Get` and transactions return `dal.ErrNotSupported`. Build on this driver for the supported table. The moment the feature is a cursor or a cross-request transaction, the HTTP API of OpenVaultDB — or a different store — is the tool, and pretending the portable interface will grow the feature is how a demo becomes a production incident.

**Read-only adapters as a system of record.** `dalgo2d1`, `dalgo2http`, and `dalgo2logs` are described by their repositories as read-only. They are how a DALgo caller can query Cloudflare D1, a declarative HTTP/JSON source, or a bounded set of local log files. They will not take an `Insert`. Namecheap's adapter exposes domains and DNS host records as collections; that is a vendor API with a record-shaped view, and its module is several DALgo minor versions behind the current core. Check the `go.mod` before you assume a new core API exists there.

## Capability-based code is the price of portability

Portable code is code that stays inside the intersection of the adapters it will actually meet, or that handles `dal.ErrNotSupported` on purpose. There is no third option where every adapter silently grows Postgres.

A few consequences follow.

A shared test that runs a join, a `GROUP BY`, and a decimal `SUM` against `dalgo2memory` has not shown that OpenVaultDB or Firestore will run that query. The memory adapter is allowed to be ahead of a given production adapter. The end-to-end scenarios in the core repo are how adapter authors pin behavior; application authors still read the adapter they deploy.

Generic execution is a fallback with its own holes. The core README notes that generic joins, recursive execution, and local aggregation cannot preflight source-rights metadata, and they refuse annotated inputs with `dal.ErrNotSupported` instead of dropping that metadata. If your requirement is "every read returns a complete inventory of source terms," you need a provider that supplies `dal.QueryMetadataProvider` on the native path, and you need to avoid the generic fallback. That is a narrower audience than CRUD. It matters as soon as you are mixing licensed or user-owned sources, which is the direction OpenVaultDB and the rights metadata are written for.

Client-side features can look like server features. OpenVaultDB projections are trimmed after the response arrives. A `SelectColumns` call there does not reduce bandwidth or bypass a field the server decided the caller could see. Authorization stays on the server. The portable call is still worth making, and it is worth knowing what it costs.

SQL identifier case is a similar trap. `dalgo2sql`'s PostgreSQL path has `IdentifierCaseExact` and `IdentifierCaseFoldLower`. A query that the compiler runs will accept either spelling the query uses; a query that falls into DALgo's own engine does not fold names for you. A portable query copied onto a fold-lower mount must spell columns the way the catalog stores them, unless it stays on the compiled path. This is the sort of defect that appears only after the second database, which is an argument for the abstraction and a reminder that the second database has to be in the test plan.

Transactions differ underneath the callback. The callback style lets Firestore use its transaction and lets `dalgo2openvaultdb` buffer a batch and `POST` it. Isolation levels can be requested as options; an adapter that cannot honor one should fail, not approximate. SQLite's driver advertises single-writer concurrency. Postgres advertises concurrent connections. Code that opens a pile of parallel read-write transactions and assumes both will behave like Postgres will misbehave on the SQLite adapter even though both values are `dal.DB`. `dal.ConcurrencyAware` is there so the application can branch. Call it.

Typed collections have a real boundary, documented by the bots framework when it evaluated them. `Collection[K, T].GetData` allocates `T`. That fits a concrete struct. It does not fit a framework that is generic over an interface plus a caller-supplied factory: `new(SomeInterface)` is not a value an adapter can decode into. DALgo added `dal.GetRecordWithIDIntoData` and `dal.InsertRecordWithDataAndID` for that case. `bots-fw` then kept DALgo out of the core module anyway, behind `StateStore`. If your models are interfaces created by factories, start from those free functions, or stay on `dal.Record` and keys. If your framework should not mention a database at all, follow bots-fw and put DALgo in an optional adapter.

## The TypeScript stack is younger than the Go module

Choose `@dalgo/core` for a browser or a Node program that can consume an adapter written against that package. Do not choose it as a way to share a Go service's database code with the frontend. There is no shared runtime.

Practical limits, from the `dalgo-js` and `dalgo-http-adapters` READMEs:

- The core package cannot run a query by itself. The in-repo memory executor is a test executor.
- Firestore and IndexedDB on the current core still need their own JOIN resolver tests before generic JOIN is a claim they can make. Legacy packages that import `@dal-go/dalgo` do not gain that support by sitting next to the new core.
- Decimal and timestamp parameter types can be authored in TugQL and are rejected at resolution, because the current query engine will not promise their comparison semantics.
- "Browser-ready" in the qualification matrix means a public-client auth model and CORS. It does not mean an account key may ship to the browser. Snowflake, Databricks, ClickHouse, and similar entries are HTTP-capable from a trusted runtime or a proxy.
- Many matrix rows are workspace packages under `@dal-go/*`, not published `@dalgo/*` libraries. A row in the matrix is a qualification decision. Confirm the package you can actually import. Archived repositories such as `dalgo2ovdb-js` and `dalgo2firestore-js` are the previous packaging, not the current catalog.

The `datatug-apps` manifest pins `@dalgo/core` and several adapters to git revisions. That shows the web workspace is integrating the TypeScript stack. It does not, by itself, say which screens call which adapter in production. The Go module remains the implementation the DALgo project points DataTug's current server-side work at.

## A short decision

Ask three questions before adding the module.

1. Will this code run, on purpose, against more than one store — production plus a test double counts?
2. Are the operations inside the capability table of each adapter on that list, including the errors you are willing to handle?
3. Is it acceptable that engine-specific SQL, listeners, and warehouse controls live outside this code?

Three yes answers: use DALgo, inject `dal.DB` or a narrower session, and put adapter construction in `main` or in the test. A no on the second question: use DALgo for the portable operations and the native driver for the one query or stream that needs it. Sneat's Firestore helper and the bots framework both do a version of this. They keep the wide interface away from callers who do not need it. A no on the first question, with a yes on a single engine's special features: use the driver. You will write less translation code, and you will not discover `ErrNotSupported` in production.

The layer is MIT-licensed and still on a v0 module path. Downstream modules in the same week pin different v0.9x releases. Pin yours. When an adapter's README and a diagram disagree, believe the README.

## Sources

Public default branches and repository metadata, read on 27 October 2026.

- [dal-go/dalgo](https://github.com/dal-go/dalgo) README, `docs/adapters.md`, `docs/hooks.md`, `docs/access-policies.md`.
- [dal-go/dalgo2sql](https://github.com/dal-go/dalgo2sql) README and dialect sources (`dialect_mysql.go`, `dialect_oracle.go`, `dialect_sqlserver.go`, `dialect_postgres.go`).
- [dal-go/dalgo2postgres](https://github.com/dal-go/dalgo2postgres), [dalgo2sqlite](https://github.com/dal-go/dalgo2sqlite), [dalgo2firestore](https://github.com/dal-go/dalgo2firestore), [dalgo2openvaultdb](https://github.com/dal-go/dalgo2openvaultdb), [dalgo2bigquery](https://github.com/dal-go/dalgo2bigquery).
- [dal-go/dalgo-js](https://github.com/dal-go/dalgo-js) and [dal-go/dalgo-http-adapters](https://github.com/dal-go/dalgo-http-adapters), including the qualification matrix.
- [sneat-co/sneat-cli](https://github.com/sneat-co/sneat-cli) `convo_storage.go` and `internal/firestoredb/firestoredb.go`. [sneat-co/sneat-go-core](https://github.com/sneat-co/sneat-go-core) facade.
- [openvaultdb/openvaultdb-go](https://github.com/openvaultdb/openvaultdb-go) README.
- [bots-go-framework/bots-fw](https://github.com/bots-go-framework/bots-fw) `PERSISTENCE.md` and `DALGO-TYPED-COLLECTION.md`. [bots-fw-store-dalgo](https://github.com/bots-go-framework/bots-fw-store-dalgo).
- Repository descriptions for `dalgo2d1`, `dalgo2http`, `dalgo2logs`, `dalgo2namecheap`, `dalgo-memcache-appengine`. No `dalgo2redis` or `dalgo2spanner` repository was listed under the dal-go organization.
