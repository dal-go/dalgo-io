---
title: DALgo vs GORM: a gorm alternative
slug: dalgo-vs-gorm
date: 2026-11-09
description: dalgo vs gorm: a gorm alternative and golang orm alternative for services that swap stores, and where GORM's relational model is the better fit.
summary: GORM is a full-featured object-relational mapper for the relational databases its guide names. DALgo is a database abstraction layer for the same record calls on SQL and on other stores, including memory and Firestore.
order: 3
schema: techarticle
---

[GORM](https://gorm.io/docs/) is an object-relational mapper for the [Go](https://go.dev/) programming language: a library that turns Go values into rows of a relational database and back. ORM is short for [object-relational mapper](https://en.wikipedia.org/wiki/Object%E2%80%93relational_mapping). [DALgo](/) is an [open-source](https://github.com/dal-go/dalgo) database abstraction layer for Go and TypeScript; the Go module is [`github.com/dal-go/dalgo`](https://github.com/dal-go/dalgo). DAL is short for database abstraction layer: a library that sits between application code and a database, so the program can store and load records without calling one vendor's client. [Database abstraction layer in Go](/articles/go-database-abstraction-layer/) is that definition for this project, and [Wikipedia](https://en.wikipedia.org/wiki/Database_abstraction_layer) uses the same name. [CRUD](https://en.wikipedia.org/wiki/Create,_read,_update_and_delete), short for create, read, update, and delete, names the four record operations both libraries expose. [SQL](https://en.wikipedia.org/wiki/SQL), short for Structured Query Language, is the language relational databases use for queries.

Readers comparing dalgo vs gorm are usually choosing a gorm alternative, or a golang orm alternative, for a Go service. Those phrases point at different jobs, and this page keeps them apart. [Database abstraction layer in Go: what it is and when you need one](/articles/go-database-abstraction-layer/) defines the layer and lines DALgo up with `database/sql`, sqlx, GORM, ent, and sqlc. [Repository pattern in Go with a swappable storage backend](/articles/go-repository-pattern/) puts a smaller interface in front of [`dal.DB`](https://pkg.go.dev/github.com/dal-go/dalgo/dal#DB). [Why use DALgo](/articles/why-use-dalgo/) is the project case, and [When to use DALgo, and when not to](/articles/when-to-use-dalgo/) is the limit list. The Go overview is [/go/](/go/), the handle is [/interfaces/](/interfaces/), typed collections are [/collections/](/collections/), and the support matrix is [/adapters/](/adapters/).

Nothing below is a benchmark. There is no timing, no download count, and no claim about which library is faster.

## What each project says it is

GORM's guide calls it ["The fantastic ORM library for Golang"](https://gorm.io/docs/index.html) and lists a full-featured ORM. The same page names associations (Has One, Has Many, Belongs To, Many To Many, polymorphism, single-table inheritance), hooks, eager loading with `Preload` and `Joins`, transactions including nested transactions and savepoints, a SQL builder, upsert, locking, auto migrations, a logger, and a generics API for type-safe queries from v1.30.0. The [quick start](https://gorm.io/docs/index.html) installs `gorm.io/gorm` and a driver. The sample driver is SQLite. The handle the sample keeps is `*gorm.DB`.

DALgo's README calls the project a database abstraction layer for Go applications: one API for records, queries, transactions, hooks, and schema-aware key mapping, with the storage backend left as an implementation choice. It is aimed at code that should stay independent of Firestore, SQL, or a test-only database. The same README says DALgo does not try to hide every database difference. An adapter returns `dal.ErrNotSupported` for a capability its backend cannot provide. The core module also contains a package named [`orm`](https://github.com/dal-go/dalgo/tree/main/orm). Its package comment says it maps collections and fields onto dal collection references and comparison conditions. That package is a mapping helper beside the `dal` API. The association model, auto migration, and `*gorm.DB` session in GORM's guides are a different product.

The TypeScript package [`@dalgo/core`](https://github.com/dal-go/dalgo-js) follows the same idea in a separate codebase, for a browser or Node program. GORM's guides describe a Go library. The samples on this page are Go.

## The same four operations, two call shapes

GORM's traditional quick start opens SQLite, runs `AutoMigrate`, and then creates, reads, updates, and deletes a `Product`. The block below is that sequence with one of the two reads the page shows. The guide also shows a generics form, `gorm.G[Product](db)`, for GORM v1.30.0 and later. This site did not execute the sample.

```go
package main

import (
	"gorm.io/driver/sqlite"
	"gorm.io/gorm"
)

type Product struct {
	gorm.Model
	Code  string
	Price uint
}

func main() {
	db, err := gorm.Open(sqlite.Open("test.db"), &gorm.Config{})
	if err != nil {
		panic("failed to connect database")
	}
	db.AutoMigrate(&Product{})
	db.Create(&Product{Code: "D42", Price: 100})
	var product Product
	db.First(&product, "code = ?", "D42")
	db.Model(&product).Update("Price", 200)
	db.Delete(&product, 1)
}
```

`gorm.Model`, [as the models guide defines it](https://gorm.io/docs/models.html), embeds `ID`, `CreatedAt`, `UpdatedAt`, and `DeletedAt`. The [delete guide](https://gorm.io/docs/delete.html) says a `gorm.DeletedAt` field turns `Delete` into a soft delete: the row stays, `DeletedAt` is set to the current time, and ordinary queries skip it. `db.Unscoped().Delete` is the permanent delete. The quick start's `db.Delete(&product, 1)` passes the primary key `1`.

DALgo's typed-collection sample in the core README is the matching create, read, update, and delete shape for one user record. `dal.CollectionOf` builds a session-less handle. `GetData` accepts a `dal.ReadSession`, and a `dal.DB` satisfies that. `SetByID` accepts a `dal.WriteSession`. A plain `dal.DB` is not a write session, so the write is a compile error unless it runs inside `RunReadwriteTransaction`. A missing record comes back as an error. The core README's sample comment names `dal.IsNotFound`. The companion article's tested listing calls `record.IsNotFound` from [`github.com/dal-go/record`](https://github.com/dal-go/record) at the versions it pinned. Use the helper the module version you import documents.

```go
package store

import (
	"context"

	"github.com/dal-go/dalgo/dal"
)

type User struct {
	Name  string
	Email string
}

func (User) CollectionName() string { return "users" }

var Users = dal.CollectionOf[string, User]()

func LoadUser(ctx context.Context, db dal.DB, id string) (User, error) {
	return Users.GetData(ctx, db, id)
}

func SaveUser(ctx context.Context, db dal.DB, id string, user User) error {
	return db.RunReadwriteTransaction(ctx, func(ctx context.Context, tx dal.ReadwriteTransaction) error {
		return Users.SetByID(ctx, tx, id, user)
	})
}
```

[Database abstraction layer in Go](/articles/go-database-abstraction-layer/) is the full listing, including memory, SQLite, Postgres, and Firestore openers. `go test` on that page, run on 7 November 2026, passed against `github.com/dal-go/dalgo` v0.101.4, `dalgo2sqlite` v0.6.1, `dalgo2sql` v0.32.2, and `record` v0.1.5, for the in-memory adapter and a temporary SQLite file. Postgres and Firestore constructors were compiled in that package and were not pointed at a live server. This page did not re-run that test. [pkg.go.dev](https://pkg.go.dev/github.com/dal-go/dalgo) listed v0.102.2 as the current module version on 9 November 2026. The path is still v0. Pin the version a service has actually run.

In that tested SQL listing, the recordset named the key column `id`, and the other columns were the exported field names `Name` and `Email`. GORM's [models guide](https://gorm.io/docs/models.html) uses a field named `ID` as the default primary key, pluralizes the struct name into a snake_case table name (`User` becomes `users`), and converts field names to snake_case column names.

## Where the documented designs diverge

| | [GORM](https://gorm.io/docs/index.html) | [DALgo](https://github.com/dal-go/dalgo) |
| --- | --- | --- |
| What it says it is | A full-featured ORM for Go. | A database abstraction layer for records, queries, transactions, hooks, and schema-aware keys. |
| Databases the docs name | [MySQL, PostgreSQL, GaussDB, SQLite, SQL Server, TiDB, Oracle Database, and ClickHouse](https://gorm.io/docs/connecting_to_the_database.html). Other databases need a driver. | In-memory and filesystem adapters in the core module, plus separate modules for SQL engines and for other stores, including [Cloud Firestore](https://github.com/dal-go/dalgo2firestore). The [adapter matrix](/adapters/) is the inventory. |
| Several databases | [DBResolver](https://gorm.io/docs/dbresolver.html) adds sources, replicas, read/write splitting, and load balancing. A transaction stays on the connection it started with. | One `dal.DB` is one adapter. A second store is a second handle, or a test that constructs a different adapter and passes it to the same function. |
| Associations | Has One, Has Many, Belongs To, Many To Many, polymorphism, and single-table inheritance, with `Preload` and `Joins`. | The README documents inner and left equi-joins on the structured query. It does not describe GORM's association mode. |
| Schema changes | [`AutoMigrate`](https://gorm.io/docs/migration.html) creates tables, missing foreign keys, constraints, columns, and indexes. It can change a column's type in the cases the guide lists. It will not delete unused columns. | The `ddl` package is the schema-modification API. The tested listing calls `ddl.CreateCollection` when the database implements `ddl.SchemaModifier`. |
| Hooks | Methods on the model, `func(*gorm.DB) error`, before and after create, save, update, delete, and find. An error stops the operation and rolls back the current transaction. | The README describes hooks for logging, validation, metrics, and other behavior. Validation and before-save hooks run in `dal.DB` before the adapter is entered. |
| Writes and transactions | Create, update, and delete [run inside a transaction by default](https://gorm.io/docs/transactions.html). `SkipDefaultTransaction` turns that off. `db.Transaction` is the callback. Nested transactions, `Begin` / `Commit` / `Rollback`, and `SavePoint` / `RollbackTo` are documented. | A write on a plain `dal.DB` is a compile error. `RunReadwriteTransaction` is the callback. The README says options can carry an isolation-level request and a message. |

Both libraries can sit on a SQL driver. GORM's connecting guide says GORM uses `database/sql` for the pool, and `db.DB()` returns that `*sql.DB`. It also shows `gorm.Open` wrapping an existing `*sql.DB`. DALgo's [`dalgo2sql`](https://github.com/dal-go/dalgo2sql) is the adapter for `database/sql`. The shared SQL driver is the floor. The API above it is the choice.

## Where GORM is the better fit

Stay with GORM when the service is a relational model and the features below are the ones the team will call.

**The database is one GORM documents, or several of them.** The connecting guide's list is MySQL, PostgreSQL, GaussDB, SQLite, SQL Server, TiDB, Oracle Database, and ClickHouse. TiDB is reached through the MySQL driver. The page says other databases need a driver you write. [DBResolver](https://gorm.io/docs/dbresolver.html) is the documented way to add sources and replicas, switch by table or struct, and split reads and writes. That plugin still speaks GORM's dialectors. It is the right tool when every database in the process is one of those engines, including a read replica.

**The model is associations, not a single collection.** The [associations guide](https://gorm.io/docs/associations.html) saves associated rows on create, and Association Mode can find, append, replace, delete, clear, and count relations. Eager loading is `Preload` and `Joins`. DALgo's README documents inner and left equi-joins in the structured query, and an adapter that cannot run a join returns `dal.ErrNotSupported`. A `User` with credit cards, languages, and a billing address, saved and loaded as associations, is the model GORM's guide is written for.

**Schema updates should follow the struct.** [`AutoMigrate`](https://gorm.io/docs/migration.html) creates missing tables, foreign keys, constraints, columns, and indexes, and it refuses to drop unused columns. The migrator interface covers tables, columns, views, constraints, and indexes, with notes for engines that lack an `ALTER` (SQLite gets a copy-and-rename; some MySQL versions get a different rename). DALgo's tested `ddl.CreateCollection` helper creates the collection the listing names. It is the wrong stand-in for that migrator.

**You want the conventions and the soft delete.** `ID`, snake_case plural table names, snake_case columns, and `CreatedAt` / `UpdatedAt` are GORM's defaults, overridable with tags. A `DeletedAt` field, included in `gorm.Model`, makes `Delete` a soft delete. DALgo's README lists `DeleteByID` and `DeleteByKey` among collection writes and does not describe a `DeletedAt` field.

**The SQL you need is on GORM's feature list.** The overview names a SQL builder, upsert, locking, optimizer and index hints, named arguments, and subqueries. The transaction guide adds nested transactions and savepoints. A reporting query that depends on those calls belongs on `*gorm.DB`. DALgo's own limit, stated in the core README and walked through in [When to use DALgo, and when not to](/articles/when-to-use-dalgo/), is that a window function, a recursive common-table expression, or any other engine feature the adapter does not implement is a reason to call the driver.

Use GORM for that service. Wrapping `*gorm.DB` in a small repository is still reasonable. The [repository article](/articles/go-repository-pattern/) says so: `Get` and `Save` can be implemented with GORM when every deployment is one SQL database.

## Where DALgo is the better fit

Use DALgo when the same Go functions must run against more than one store, and a test double counts.

The core README states the case directly: keep application logic independent of a concrete database client, use the same record, query, and transaction shape across supported adapters, and test with the built-in in-memory adapter. The standard-library comparison on that README says the typed-collection function runs on Firestore, SQL, the filesystem, or the in-memory adapter. [`dalgo2memory`](https://github.com/dal-go/dalgo/tree/main/adapters/dalgo2memory) ships in the core module for tests, examples, and local development. [`dalgo2firestore`](https://github.com/dal-go/dalgo2firestore) is the Firestore adapter. [`dalgo2sqlite`](https://github.com/dal-go/dalgo2sqlite) and [`dalgo2postgres`](https://github.com/dal-go/dalgo2postgres) are the SQL engine modules the companion listing opens. The [adapter matrix](/adapters/) is the list of what each backend implements. A module's presence in the README is not a promise that it runs every query.

That swap is the part this comparison hangs on. DBResolver's guide shows sources and replicas opened with GORM dialectors, and the sample uses MySQL. DALgo's README says the same typed-collection function runs on Firestore, SQL, the filesystem, or the in-memory adapter. A program that will only ever speak one engine's SQL can keep GORM's associations and `AutoMigrate`, which are the features that service would be using.

DALgo's write rule is the other concrete difference. Because `SetByID` requires a `dal.WriteSession`, a write cannot be handed a plain `dal.DB`. GORM's default is also transactional: the transaction guide says create, update, and delete run inside a transaction, and `SkipDefaultTransaction` disables that. The difference a reviewer can see in DALgo is that the write session is a different type, so the mistake is a compile error. GORM's guide makes the same protection the default behavior of `*gorm.DB`, and documents the switch that turns it off.

`dal.ErrNotSupported` is how an adapter declines a call. The core README prefers that to hiding the difference. A structured query the memory adapter runs can still return that error on another backend. Code that must run on two adapters has to stay inside the intersection, or handle the error on purpose. [Queries](/queries/) and [TugQL](/tugql/) are the structured form when a call needs more than a point read.

The Go module is [MIT-licensed](https://github.com/dal-go/dalgo/blob/main/LICENSE). GORM's README says the project is released under the [MIT License](https://github.com/go-gorm/gorm/blob/master/LICENSE). Both are public repositories: [dal-go/dalgo](https://github.com/dal-go/dalgo) and [go-gorm/gorm](https://github.com/go-gorm/gorm).

## FAQ

### Is DALgo a gorm alternative?

DALgo is a gorm alternative when the requirement is one Go API for create, read, update, and delete across more than one store, including a store that is not a relational database. GORM remains the better fit when the requirement is its association model, `AutoMigrate`, soft delete, or the SQL databases its connecting guide lists.

### What does dalgo vs gorm compare?

It compares two Go libraries that store and load records. GORM's guides describe an object-relational mapper and a `*gorm.DB` opened through a driver. DALgo's README describes a database abstraction layer: application code accepts `dal.DB`, and an adapter supplies the database. The [abstraction-layer article](/articles/go-database-abstraction-layer/) is the longer definition.

### Is a golang orm alternative the same request?

A golang orm alternative, meaning another object-relational mapper, is the request GORM and ent document. DALgo's README calls the project a database abstraction layer. The `orm` package in the core module maps collections and fields onto collection references and comparison conditions. The Has One, Has Many, Belongs To, and Many To Many model lives in GORM's associations guide.

### When should a service stay on GORM?

Stay when every deployment is a relational database GORM documents, including a replica reached through DBResolver, and the code uses associations, eager loading, auto migration, model conventions, or soft delete. A small repository can still hide `*gorm.DB` from HTTP handlers. The handlers then depend on `Get` and `Save`, and the package that calls `gorm.Open` depends on the driver.

### Can the same DALgo functions use memory, SQLite, and Firestore?

`LoadUser` and `SaveUser` above take `dal.DB`. The companion article ran that shape on `dalgo2memory` and on `dalgo2sqlite` after creating the table, and compiled an opener for `dalgo2firestore`. Firestore still has its own client lifecycle, and SQL still needs the table. A call the adapter cannot run returns `dal.ErrNotSupported`. The [adapter matrix](/adapters/) is the checklist before promising a method on a backend.

## Sources

GORM's public guides and DALgo's public module docs, read on 9 November 2026. The DALgo `go test` date and versions are the ones reported in the companion article of 7 November 2026. This page did not re-run that test and did not execute the GORM sample.

- [GORM guides](https://gorm.io/docs/index.html), including the quick start, the [connecting guide](https://gorm.io/docs/connecting_to_the_database.html), [models](https://gorm.io/docs/models.html), [associations](https://gorm.io/docs/associations.html), [hooks](https://gorm.io/docs/hooks.html), [transactions](https://gorm.io/docs/transactions.html), [migration](https://gorm.io/docs/migration.html), [delete](https://gorm.io/docs/delete.html), and [DBResolver](https://gorm.io/docs/dbresolver.html).
- [go-gorm/gorm](https://github.com/go-gorm/gorm) README, which states the [MIT License](https://github.com/go-gorm/gorm/blob/master/LICENSE).
- [dal-go/dalgo](https://github.com/dal-go/dalgo) README, including typed collections, `RunReadwriteTransaction`, `dal.ErrNotSupported`, and the `orm` package comment. License: [MIT](https://github.com/dal-go/dalgo/blob/main/LICENSE). pkg.go.dev showed v0.102.2 on 9 November 2026.
- [dal-go/dalgo2sql](https://github.com/dal-go/dalgo2sql), [dalgo2sqlite](https://github.com/dal-go/dalgo2sqlite), [dalgo2postgres](https://github.com/dal-go/dalgo2postgres), [dalgo2firestore](https://github.com/dal-go/dalgo2firestore).
- [Database abstraction layer in Go](/articles/go-database-abstraction-layer/) and [Repository pattern in Go](/articles/go-repository-pattern/).
