---
title: Go ORM and data-access libraries compared (2026)
slug: go-orm-comparison-2026
date: 2026-11-24
description: A 2026 golang ORM comparison of GORM, ent, bun, sqlc, sqlx, database/sql, and DALgo: what each is, how it works, and when to choose it.
summary: A side-by-side of the main Go data-access libraries in 2026: full ORMs, SQL-first tools, and a database abstraction layer that also spans non-SQL stores. Facts come from each project's official docs; there are no benchmarks.
order: 1
schema: techarticle
---

An [ORM](https://en.wikipedia.org/wiki/Object%E2%80%93relational_mapping), short for object-relational mapping, is a library that turns program objects into rows of a relational database and back. A data-access layer is the part of a program that talks to a database on behalf of the rest of the application. A [DAO](https://en.wikipedia.org/wiki/Data_access_object), short for data access object, is an object that hides how one kind of record is stored, often behind a small interface with methods such as Get and Save; the [repository pattern in Go](/articles/go-repository-pattern/) is one way to write that interface. A [database abstraction layer](/articles/go-database-abstraction-layer/), or DAL, is a library that sits between application code and a database so the program can store and load records without calling one vendor's client; [Wikipedia](https://en.wikipedia.org/wiki/Database_abstraction_layer) uses the same name. [SQL](https://en.wikipedia.org/wiki/SQL), short for Structured Query Language, is the language relational databases use for queries. [CRUD](https://en.wikipedia.org/wiki/Create,_read,_update_and_delete), short for create, read, update, and delete, names the four record operations most of these libraries expose. [DALgo](/) is an [open-source](https://github.com/dal-go/dalgo) database abstraction layer for Go and TypeScript; the Go module is [`github.com/dal-go/dalgo`](https://github.com/dal-go/dalgo).

This page is a broad, neutral overview for someone choosing a Go data layer in 2026. It is not a benchmark, and it does not rank the libraries by speed, popularity, or stars. [DALgo vs GORM: a gorm alternative](/articles/dalgo-vs-gorm/) is the head-to-head with GORM; use that page for depth on that pair rather than this one. [Database abstraction layer in Go](/articles/go-database-abstraction-layer/) defines the layer and lines DALgo up with `database/sql`, sqlx, GORM, ent, and sqlc. [When to use DALgo, and when not to](/articles/when-to-use-dalgo/) and [Why use DALgo](/articles/why-use-dalgo/) are the project case and its limits. Every competitor fact below is taken from that project's official documentation or repository, linked inline.

## How to read the comparison

The libraries fall into three groups that answer different questions.

- Full ORMs — [GORM](https://gorm.io/docs/), [ent](https://entgo.io/docs/getting-started), and [Bun](https://bun.uptrace.dev/) — map Go types onto a relational schema and help with associations, migrations, or a query builder over SQL.
- SQL-first tools — the standard library's [`database/sql`](https://pkg.go.dev/database/sql), [sqlx](https://github.com/jmoiron/sqlx), [sqlc](https://sqlc.dev/), and [Squirrel](https://github.com/Masterminds/squirrel) — keep SQL, or a generator that starts from SQL, in charge of the query.
- Database abstraction layers that span SQL and non-SQL stores — DALgo is the one in this comparison. The same record, query, and transaction calls can run on a SQL adapter, on Cloud Firestore, or on an in-memory stand-in.

No row in the table is a claim that one library "wins". Choose the tool whose job matches the service.

| Library | What its docs say it is | Approach | Documented databases | Choose it when |
| --- | --- | --- | --- | --- |
| [GORM](https://gorm.io/docs/) | "The fantastic ORM library for Golang", described in its guide as a full-featured ORM. | Schema and queries are expressed as Go on a `*gorm.DB`. | The [connecting guide](https://gorm.io/docs/connecting_to_the_database.html) officially supports MySQL, PostgreSQL, GaussDB, SQLite, SQL Server, TiDB, and Oracle Database. | The product is an object model over a relational schema, including the associations, hooks, and auto migration that GORM documents. |
| [ent](https://entgo.io/docs/getting-started) | An entity framework for Go. | Schema as Go code; a generated, statically typed client and graph edges. | The getting-started page shows SQLite, PostgreSQL, and MySQL (MariaDB). | You want a generated entity graph and are staying on the relational databases that guide demonstrates. |
| [Bun](https://bun.uptrace.dev/) | "The SQL-first Golang ORM." | A type-safe query builder on top of `database/sql`, with struct models and SQL-shaped helpers. | The homepage lists PostgreSQL, MySQL 5.7+ (the MySQL sample also names MariaDB), Microsoft SQL Server, and SQLite. | You want an ORM that still looks like SQL, on those engines, without leaving `database/sql`. |
| [`database/sql`](https://pkg.go.dev/database/sql) | A generic interface around SQL (or SQL-like) databases. | You write the SQL text, call `QueryRowContext`, and `Scan` into fields, together with a driver. | Any database for which a [Go SQL driver](https://golang.org/s/sqldrivers) exists. | The program is one SQL database and the team wants the statements in source control as SQL, with no extra mapper. |
| [sqlx](https://github.com/jmoiron/sqlx) | A set of extensions on `database/sql`. The README says the sqlx types leave the underlying interfaces untouched, so they are a superset. | You still write SQL. `StructScan`, `Get`, `Select`, and named queries sit on top of `*sql.DB`. | The same driver list as `database/sql`. The README example opens PostgreSQL. | You want `database/sql` plus struct scanning and named parameters, still with SQL in the call. |
| [sqlc](https://sqlc.dev/) | A command-line tool that generates type-safe code from SQL. | Schema-first: you write SQL schema and queries; `sqlc generate` emits Go. | The [language-support table](https://docs.sqlc.dev/en/latest/reference/language-support.html) lists MySQL and PostgreSQL as stable for the built-in Go generator. | The SQL should be the source of truth and should also produce the Go call sites. |
| [Squirrel](https://github.com/Masterminds/squirrel) | A fluent SQL generator. Its README states it is not an ORM. | Composable builders that return SQL and arguments via `ToSql`, or run them with `RunWith` on a `database/sql` handle. | Any engine `database/sql` can open. PostgreSQL-style placeholders use `PlaceholderFormat(Dollar)`. | You want to build SQL from parts in Go, then run it yourself, without an object mapper. |
| [DALgo](https://github.com/dal-go/dalgo) | A database abstraction layer for Go, with a TypeScript package [`@dalgo/core`](https://github.com/dal-go/dalgo-js). | One record, query, and transaction API; adapters supply the backend. | SQL engines through [dalgo2sql](https://github.com/dal-go/dalgo2sql) and engine modules such as [dalgo2postgres](https://github.com/dal-go/dalgo2postgres), [dalgo2sqlite](https://github.com/dal-go/dalgo2sqlite), and [dalgo2mysql](https://github.com/dal-go/dalgo2mysql) (see [SQLite in Go with DALgo: the dalgo2sqlite adapter](/adapters/dalgo2sqlite/)); [Cloud Firestore](https://github.com/dal-go/dalgo2firestore); the built-in [in-memory adapter](https://github.com/dal-go/dalgo/tree/main/adapters/dalgo2memory); and the others on the [adapter matrix](/adapters/). A read-only MongoDB adapter is documented at [MongoDB in Go with DALgo: the dalgo2mongodb adapter](/adapters/dalgo2mongodb/). | The same Go functions must run against more than one store, and a test double counts. |

## Full ORMs: GORM, ent, and Bun

### GORM

[GORM](https://gorm.io/docs/) is a full-featured ORM for Go. Its [guide](https://gorm.io/docs/index.html) lists associations, hooks, eager loading, auto migration, a SQL builder, and transactions, including nested transactions, save points, and rollback to a saved point. The [quick start](https://gorm.io/docs/index.html) opens a database through a driver; the sample uses SQLite.

**Approach.** Code-first: you describe models as Go structs and talk to a `*gorm.DB`. Schema changes can go through the auto-migration API the guide documents.

**Databases.** The [connecting-to-a-database](https://gorm.io/docs/connecting_to_the_database.html) guide officially supports MySQL, PostgreSQL, GaussDB, SQLite, SQL Server, TiDB, and Oracle Database. TiDB is used through the MySQL connection path. A [ClickHouse driver](https://github.com/go-gorm/clickhouse) is linked from that page; it is a separate repository.

**Transactions.** [GORM's transaction guide](https://gorm.io/docs/transactions.html) documents `db.Transaction`: return an error to roll back, return nil to commit. You can also call `Begin`, `Commit`, and `Rollback` yourself, and use `SavePoint` and `RollbackTo`. Nested transactions are supported.

**Testing.** The [session guide](https://gorm.io/docs/session.html) documents DryRun mode, which generates SQL without executing it, for preparing or testing the statement. The connecting guide shows SQLite, including a temporary database, which teams often use as a test engine. GORM does not ship a separate non-SQL test double.

**Choose it when** the service is a relational application and you want GORM's object model, associations, and migrations. [DALgo vs GORM](/articles/dalgo-vs-gorm/) spells out where that model is the better fit, and where a database abstraction layer is.

### ent

[ent](https://entgo.io/docs/getting-started) is an entity framework for Go. The getting-started page states its principles: model the schema as a graph, define that schema as programmatic Go code, get static typing from code generation, and write queries and graph traversals against the generated client.

**Approach.** Schema-first as Go: you declare fields and edges in `ent/schema`, run `go generate`, and call builders such as `client.User.Create()`. The model is the generated graph, not a hand-written SQL string and not a swappable document API.

**Databases.** The getting-started page shows opening SQLite, PostgreSQL, and MySQL (MariaDB), and running `client.Schema.Create` for automatic migrations. That page also documents versioned migrations with Atlas.

**Transactions.** The [transactions guide](https://entgo.io/docs/transactions) starts a transaction with `client.Tx(ctx)`, works on `tx.User` (and the other entity clients), and commits or rolls back. You can take a transactional `*ent.Client` from `tx.Client()`, and some drivers accept an isolation level through `BeginTx`.

**Testing.** The official [tutorial setup](https://entgo.io/docs/tutorial-setup) creates an `ent.Client` on an in-memory SQLite database (`file:ent?mode=memory&cache=shared&_fk=1`) and runs `client.Schema.Create` in a test. That is a real SQL engine in memory, not a generic non-SQL stand-in.

**Choose it when** you want a generated, typed entity graph on the relational databases that guide demonstrates, including edges and the migration story ent documents.

### Bun

[Bun](https://bun.uptrace.dev/) calls itself "the SQL-first Golang ORM." The homepage says it is built on `database/sql`, that you write SQL-shaped queries with type safety, and that one codebase can target several SQL databases.

**Approach.** You define struct models with `bun` tags and build queries with helpers such as `db.NewSelect()`, `ColumnExpr`, and `TableExpr`. The homepage shows those builders producing ordinary SQL, including common table expressions.

**Databases.** The homepage lists PostgreSQL, MySQL 5.7+ (the MySQL sample comment also names MariaDB), Microsoft SQL Server, and SQLite, each with a dialect package.

**Transactions.** The [transactions guide](https://bun.uptrace.dev/guide/transactions.html) describes `bun.Tx` as a thin wrapper around `sql.Tx`. You can call `BeginTx`, `Commit`, and `Rollback`, or use `RunInTx`, which rolls back if the callback returns an error and commits otherwise. The same methods can take `bun.IDB`, which works with `*bun.DB`, `bun.Tx`, and `bun.Conn`.

**Testing.** The homepage uses in-memory SQLite as the development and testing sample. The [fixtures guide](https://bun.uptrace.dev/guide/fixtures.html) loads YAML fixtures into a database for testing or demonstration, including options that recreate or truncate tables.

**Choose it when** you want an ORM that stays close to SQL, on the engines Bun documents, and you are happy to stay inside `database/sql`.

## SQL-first tools: database/sql, sqlx, sqlc, and Squirrel

### database/sql

The standard library package [`database/sql`](https://pkg.go.dev/database/sql) "provides a generic interface around SQL (or SQL-like) databases." It must be used with a [database driver](https://golang.org/s/sqldrivers).

**Approach.** You write SQL, execute it with `QueryContext`, `QueryRowContext`, or `ExecContext`, and `Scan` the result into variables. There is no object mapper and no code generator.

**Databases.** Whatever a compatible driver opens. The package itself does not name a vendor list.

**Transactions.** `DB.Begin` and `DB.BeginTx` return a `*sql.Tx`. `TxOptions` can set an isolation level and a read-only flag. You `Commit` or `Rollback` that transaction.

**Testing.** Tests use a real driver. Many suites open a test database, often SQLite, or wrap `database/sql` behind a small interface and supply a fake in unit tests. The package does not include an in-memory database of its own.

**Choose it when** the team wants SQL in the repository, one relational engine, and the standard library alone.

### sqlx

[sqlx](https://github.com/jmoiron/sqlx) is a set of extensions on `database/sql`. Its README says the sqlx versions of `sql.DB`, `sql.Tx`, and `sql.Stmt` leave the underlying interfaces untouched, so they are a superset, which makes it relatively painless to integrate existing `database/sql` code.

**Approach.** You still write SQL. The additional concepts the README names are marshaling rows into structs, maps, and slices, named parameter support, and `Get` and `Select` to go quickly from a query to a struct or a slice. `StructScan` is the row-level form of that mapping.

**Databases.** The same drivers as `database/sql`. The README example uses the `postgres` driver.

**Transactions.** The README starts a transaction with `db.MustBegin()`, runs `tx.MustExec` and `tx.NamedExec`, and calls `tx.Commit()`. That is the standard-library transaction, with sqlx's helpers on the `*sqlx.Tx`.

**Testing.** There is no separate in-memory adapter. Tests use a SQL database the way `database/sql` tests do; the repository's own tests are in `sqlx_test.go`.

**Choose it when** you want to keep writing SQL and also scan into structs and use named parameters, without adopting an ORM.

### sqlc

[sqlc](https://sqlc.dev/) "generates fully type-safe idiomatic code from SQL." The site's three steps are: you write SQL queries, you run sqlc to generate code, and you write application code that calls the generated methods.

**Approach.** Schema-first, generated code. The [PostgreSQL tutorial](https://docs.sqlc.dev/en/latest/tutorials/getting-started-postgresql.html) keeps `schema.sql` and `query.sql` in the repository and emits a Go package; that tutorial uses `pgx`.

**Databases.** The official [database and language support](https://docs.sqlc.dev/en/latest/reference/language-support.html) table lists MySQL and PostgreSQL as stable for the built-in Go generator. Other engines appear on the same table; read that page for the current status of each one.

**Transactions.** The [transactions guide](https://docs.sqlc.dev/en/latest/howto/transactions.html) shows `Queries.WithTx(tx)`, which returns a `Queries` instance bound to a `*sql.Tx` (or the `pgx` transaction type when that driver is used). You begin the transaction on the driver, run the generated methods on `qtx`, then commit or roll back.

**Testing.** sqlc generates ordinary Go against `database/sql` or `pgx`. Tests run that generated package against a database of the engine you targeted. sqlc does not provide a non-SQL in-memory store.

**Choose it when** SQL should remain the source of truth and you want the compiler to check the Go that calls those statements.

### Squirrel

[Squirrel](https://github.com/Masterminds/squirrel) is a fluent SQL generator for Go. Its README says, in those words, "Squirrel is not an ORM."

**Approach.** You compose `Select`, `Insert`, `Where`, and similar builders from parts, then call `ToSql` for the statement and arguments, or `RunWith(db).Query()` to execute them on a `database/sql` handle. Conditional clauses are ordinary Go `if` statements that add another `Where`.

**Databases.** Squirrel does not ship drivers. It produces SQL for whatever `database/sql` can run. The README documents `PlaceholderFormat` for PostgreSQL-style `$1` placeholders.

**Transactions.** Squirrel does not begin transactions itself. A `*sql.Tx` implements the runner interfaces the package uses, so you pass the transaction to `RunWith` and commit or roll back with `database/sql`.

**Testing.** Because `ToSql` returns the statement and arguments, tests can assert on the generated SQL without opening a database. Execution tests use a real driver, the same as `database/sql`. The README also says the project's tests should be treated as part of the documentation.

**Choose it when** you want composable SQL in Go and will manage the driver and the transaction yourself.

## DALgo: a database abstraction layer across SQL and NoSQL

DALgo is not an ORM in the sense GORM and ent document. It is a database abstraction layer: application code talks to records, queries, and transactions, and an adapter talks to the store. The [core README](https://github.com/dal-go/dalgo) states the point: keep application logic independent of a concrete database client, use the same record, query, and transaction shape across supported adapters, and test business logic with the built-in in-memory adapter. It also states the matching limit: DALgo does not try to hide every database difference. Adapters can return `dal.ErrNotSupported` for capabilities their backend cannot provide.

**Approach.** You write functions against [`dal.DB`](https://pkg.go.dev/github.com/dal-go/dalgo/dal#DB). Construction of the adapter belongs in `main` or in a test. SQL adapters map a key and exported struct fields onto columns; they are still DALgo adapters, not a general ORM of associations and migrations. A [repository](/articles/go-repository-pattern/) can hide `dal.DB` from callers.

**Databases.** Built-in adapters in the core module include [`dalgo2memory`](https://github.com/dal-go/dalgo/tree/main/adapters/dalgo2memory) for tests and local checks, and [`dalgo2fs`](https://github.com/dal-go/dalgo/tree/main/adapters/dalgo2fs) for a filesystem tree. Separate modules include [`dalgo2sql`](https://github.com/dal-go/dalgo2sql) and the engine packages [`dalgo2postgres`](https://github.com/dal-go/dalgo2postgres), [`dalgo2sqlite`](https://github.com/dal-go/dalgo2sqlite), and [`dalgo2mysql`](https://github.com/dal-go/dalgo2mysql), plus [`dalgo2firestore`](https://github.com/dal-go/dalgo2firestore) for [Cloud Firestore](https://cloud.google.com/firestore/docs). The [adapter matrix](/adapters/) is the list of what each backend implements. A module's presence in the README is not a promise that it runs every query.

**Transactions.** Transactions use callback-style workers, documented in the core README: `RunReadwriteTransaction` and `RunReadonlyTransaction`. That keeps transaction lifetime scoped and lets adapters implement retries or backend-specific behavior. Options can carry isolation-level requests and a human-readable message. [Firestore in Go: CRUD and transactions with DALgo](/articles/go-firestore-tutorial/) walks the read-write path on Firestore. [Switching between PostgreSQL and Firestore in Go](/articles/switch-postgres-to-firestore/) shows what those calls share, and what still differs, when the same repository is opened on both stores.

**Testing.** The in-memory adapter lives in the core module. The current constructor is `dalgo2memory.New(profile)`. A profile is required: `FirestoreProfile()` follows Cloud Firestore transaction rules, including a rejection of a read that follows a write inside the transaction; `SingleWriterProfile()` follows a store that serializes writers, which is the shape SQLite has. `NewDB` still exists and calls `New(FirestoreProfile())`; the package marks `NewDB` as deprecated and documents `New` with the profile written at the call site as the current API.

**TypeScript.** A separate package, [`@dalgo/core`](https://github.com/dal-go/dalgo-js), carries hierarchical keys, typed collections, structured queries, and transaction-scoped writes into browser and Node code, with no database SDK of its own. It does not execute the Go functions on this page. The Go module is [MIT-licensed](https://github.com/dal-go/dalgo/blob/main/LICENSE); `@dalgo/core` is published from the same organization's [dalgo-js](https://github.com/dal-go/dalgo-js) repository ([MIT license](https://github.com/dal-go/dalgo-js/blob/main/LICENSE)).

**Choose it when** the same Go functions must run against more than one store, and a test double counts. The in-memory adapter plus SQLite, Postgres, or Firestore is that situation.

## When another tool is the better choice

DALgo is the wrong default when the engine's own language is the product.

- Use [`database/sql`](https://pkg.go.dev/database/sql), [sqlx](https://github.com/jmoiron/sqlx), or [Squirrel](https://github.com/Masterminds/squirrel) when the program is one SQL database and the team wants the statements, or a SQL builder, in source control as SQL.
- Use [sqlc](https://sqlc.dev/) when those statements should also produce the Go call sites.
- Use [GORM](https://gorm.io/docs/) or [ent](https://entgo.io/docs/getting-started) when the product is an object or entity model over a relational schema, including associations, graph edges, and the migrations those projects document. [DALgo vs GORM](/articles/dalgo-vs-gorm/) is that GORM choice in more detail.
- Use [Bun](https://bun.uptrace.dev/) when you want a SQL-first ORM on `database/sql` for the engines it documents, and you do not need a non-SQL adapter.
- Use the native driver directly for a window function, a recursive common-table expression, a Firestore realtime listener, or any other feature an adapter would refuse with `dal.ErrNotSupported`. [When to use DALgo, and when not to](/articles/when-to-use-dalgo/) walks those cases.

The [Go overview](/go/), the [`dal.DB` handle](/interfaces/), typed [collections](/collections/), and the [adapter matrix](/adapters/) are the product pages that sit behind this comparison.

## FAQ

### What is the best ORM for Go?

There is no single best Go ORM. If you want a full object-relational mapper on a relational database, GORM and ent are the tools whose docs describe that job, and Bun describes itself as a SQL-first ORM on `database/sql`. If you want SQL itself to stay in charge, start with `database/sql`, sqlx, sqlc, or Squirrel, not with an ORM. If the same functions must run on SQL and on a non-SQL store, including an in-memory test double, a database abstraction layer such as DALgo is the closer match. This page does not rank them by performance or popularity.

### Is an ORM needed in Go?

No. Go services often use `database/sql` or sqlc with no ORM at all. An ORM is useful when you want an object or entity model, associations, and the migration helpers those libraries document. It is optional when the team is happy to write SQL, and it is the wrong category when you need one record API across SQL and non-SQL stores.

### What is a DAO in Go?

A DAO, short for data access object, is an object that hides how one kind of record is stored. In Go that is usually a small interface — for example `Get` and `Save` on a `UserRepository` — with a concrete type that calls `database/sql`, sqlc, GORM, ent, Bun, or DALgo. The [repository pattern in Go](/articles/go-repository-pattern/) is that interface, including a swappable backend when DALgo sits behind it.

### Where does DALgo fit among Go data-access libraries?

DALgo is a database abstraction layer, not a full ORM. It fits when domain code should call `dal.DB` and the storage backend should stay replaceable: Postgres or SQLite in one deployment, Firestore in another, and `dalgo2memory.New` with an explicit profile in tests. It does not replace GORM's or ent's relational object model, and it does not replace SQL-first tools when a single SQL engine is the product.

### When should I choose sqlc or database/sql instead of DALgo?

Choose `database/sql` (or sqlx or Squirrel) when the program is one SQL database and the statements should stay in the source as SQL. Choose sqlc when those statements should also generate the Go methods. Choose DALgo when the same functions will run, on purpose, against more than one store, including a test double.

## Sources

Public project documentation and repository source, checked on 24 November 2026. This page is not a benchmark, and it does not report download counts, GitHub stars, or timings.

- [dal-go/dalgo](https://github.com/dal-go/dalgo) v0.102.6, including the core README, `RunReadwriteTransaction`, `RunReadonlyTransaction`, `dal.ErrNotSupported`, and `dalgo2memory.New` with `FirestoreProfile` and `SingleWriterProfile` (`NewDB` is deprecated). License: [MIT](https://github.com/dal-go/dalgo/blob/main/LICENSE).
- [`@dalgo/core`](https://github.com/dal-go/dalgo-js) from [dal-go/dalgo-js](https://github.com/dal-go/dalgo-js). License: [MIT](https://github.com/dal-go/dalgo-js/blob/main/LICENSE).
- [dalgo2sql](https://github.com/dal-go/dalgo2sql), [dalgo2postgres](https://github.com/dal-go/dalgo2postgres), [dalgo2sqlite](https://github.com/dal-go/dalgo2sqlite), [dalgo2mysql](https://github.com/dal-go/dalgo2mysql), [dalgo2firestore](https://github.com/dal-go/dalgo2firestore).
- [`database/sql`](https://pkg.go.dev/database/sql), [jmoiron/sqlx](https://github.com/jmoiron/sqlx), [Masterminds/squirrel](https://github.com/Masterminds/squirrel).
- [GORM guides](https://gorm.io/docs/index.html), [connecting to a database](https://gorm.io/docs/connecting_to_the_database.html), [transactions](https://gorm.io/docs/transactions.html), [session / DryRun](https://gorm.io/docs/session.html).
- [ent getting started](https://entgo.io/docs/getting-started), [ent transactions](https://entgo.io/docs/transactions), [ent tutorial setup](https://entgo.io/docs/tutorial-setup).
- [Bun](https://bun.uptrace.dev/), [Bun transactions](https://bun.uptrace.dev/guide/transactions.html), [Bun fixtures](https://bun.uptrace.dev/guide/fixtures.html).
- [sqlc](https://sqlc.dev/), [sqlc PostgreSQL tutorial](https://docs.sqlc.dev/en/latest/tutorials/getting-started-postgresql.html), [sqlc language support](https://docs.sqlc.dev/en/latest/reference/language-support.html), [sqlc transactions](https://docs.sqlc.dev/en/latest/howto/transactions.html).
- [Wikipedia: object-relational mapping](https://en.wikipedia.org/wiki/Object%E2%80%93relational_mapping), [database abstraction layer](https://en.wikipedia.org/wiki/Database_abstraction_layer), [data access object](https://en.wikipedia.org/wiki/Data_access_object), [SQL](https://en.wikipedia.org/wiki/SQL), [CRUD](https://en.wikipedia.org/wiki/Create,_read,_update_and_delete).
