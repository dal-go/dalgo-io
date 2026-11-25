---
title: SQLite in Go with DALgo: the dalgo2sqlite adapter
slug: dalgo2sqlite
date: 2026-11-25
description: "Golang SQLite with DALgo: the dalgo2sqlite adapter opens a SQLite file or memory DB in Go, and gives records, queries, transactions, and schema through dal.DB."
summary: dalgo2sqlite is the SQLite-specific DALgo driver for Go. It opens a file or an in-memory database with the pure-Go modernc.org/sqlite driver, wraps dalgo2sql to provide dal.DB, and adds SQLite schema introspection, DDL, and a single-writer concurrency hint.
order: 1
schema: techarticle
repo: https://github.com/dal-go/dalgo2sqlite
matrix: sqlite
---

[DALgo](/) is an [open-source](https://github.com/dal-go/dalgo) database abstraction layer for [Go](https://go.dev/) and TypeScript; the Go module is [`github.com/dal-go/dalgo`](https://github.com/dal-go/dalgo). A DAL, short for [database abstraction layer](/articles/go-database-abstraction-layer/), is a library that sits between application code and a database so the program can store and load records without calling one vendor's client; [Wikipedia](https://en.wikipedia.org/wiki/Database_abstraction_layer) uses the same name. An adapter, or driver in this module's own wording, is the package that implements that interface for one kind of store. [SQLite](https://sqlite.org/docs.html) is a small, file-based [SQL](https://en.wikipedia.org/wiki/SQL) database engine — SQL is short for Structured Query Language, the language relational databases use for queries — that commonly lives in a single file or in memory. [`dalgo2sqlite`](https://github.com/dal-go/dalgo2sqlite) is the [MIT-licensed](https://github.com/dal-go/dalgo2sqlite/blob/main/LICENSE) SQLite adapter for DALgo: it opens that engine and returns a [`dal.DB`](https://pkg.go.dev/github.com/dal-go/dalgo/dal#DB). [CRUD](https://en.wikipedia.org/wiki/Create,_read,_update_and_delete), short for create, read, update, and delete, names the four record operations on that handle. [DDL](https://en.wikipedia.org/wiki/Data_definition_language), short for data definition language, is the SQL that creates, alters, and drops tables and indexes. [CGo](https://pkg.go.dev/cmd/cgo) is the Go toolchain's way of calling C code; this adapter's SQLite driver does not need it.

This page is the reference for the Go module [`github.com/dal-go/dalgo2sqlite`](https://github.com/dal-go/dalgo2sqlite). The [adapter matrix](/adapters/) lists what the SQLite row implements. A broader survey of Go data-access libraries is in [Go ORM and data-access libraries compared (2026)](/articles/go-orm-comparison-2026/); ORM is short for [object-relational mapping](https://en.wikipedia.org/wiki/Object%E2%80%93relational_mapping). [Repository pattern in Go](/articles/go-repository-pattern/) puts a smaller interface in front of `dal.DB`. [Switching between PostgreSQL and Firestore in Go](/articles/switch-postgres-to-firestore/) is a walkthrough of the same record calls on two other stores. [DALgo vs GORM](/articles/dalgo-vs-gorm/) is the head-to-head with GORM. The [quickstart](/quickstart/) and the [FAQ](/faq/) are the shorter product pages.

## What dalgo2sqlite is

The module README calls dalgo2sqlite a SQLite-specific DALgo driver. It wraps [`github.com/dal-go/dalgo2sql`](https://github.com/dal-go/dalgo2sql) to provide the `dal.DB` surface — transactions, a recordset reader, and Get, Set, Insert, and Delete — and adds SQLite-native implementations of:

- [`dbschema.SchemaReader`](https://pkg.go.dev/github.com/dal-go/dalgo/dbschema) — schema introspection through `sqlite_master` and `PRAGMA` queries such as `pragma_table_info`
- [`ddl.SchemaModifier`](https://pkg.go.dev/github.com/dal-go/dalgo/ddl) and [`ddl.Applier`](https://pkg.go.dev/github.com/dal-go/dalgo/ddl) — SQLite-flavored `CREATE TABLE`, `CREATE INDEX`, `DROP TABLE`, and related statements
- `ddl.TransactionalDDL` — `SupportsTransactionalDDL()` returns true, because SQLite can run DDL inside a transaction
- [`dal.ConcurrencyAware`](https://pkg.go.dev/github.com/dal-go/dalgo/dal) — `SupportsConcurrentConnections()` returns false; SQLite serializes writers. The `Database` type embeds `dal.NoConcurrency`. The README describes the same fact as advertising `Concurrency() = 1` for write paths.

`*Database` itself satisfies `dal.DB`. Construct it with `NewDatabase` or `NewDatabaseWithOptions`, and close it when you are finished.

The facts on this page were checked against [dalgo2sqlite v0.6.5](https://github.com/dal-go/dalgo2sqlite/tree/v0.6.5) (commit `64d9e69adc5ab68ad0272b1c402ffb796aee320e` on `main`), which depends on [dalgo v0.102.6](https://github.com/dal-go/dalgo/tree/v0.102.6), [dalgo2sql v0.32.0](https://github.com/dal-go/dalgo2sql), [record v0.1.5](https://github.com/dal-go/record), and [modernc.org/sqlite v1.63.0](https://pkg.go.dev/modernc.org/sqlite@v1.63.0). A short create, read, update, and delete program compiled and ran with `CGO_ENABLED=0` against those versions on 25 November 2026, on a temporary SQLite file, on `:memory:`, and on `file:memdb1?mode=memory&cache=shared`.

## The SQLite driver: modernc.org/sqlite, pure Go

dalgo2sqlite registers [`modernc.org/sqlite`](https://pkg.go.dev/modernc.org/sqlite), a [pure-Go transpilation](https://pkg.go.dev/modernc.org/sqlite#section-readme) of the SQLite C library, and opens the database with `sql.Open("sqlite", dbPath)`. The driver name is `"sqlite"`, not `"sqlite3"`. The package comment and the README both state that this build uses `CGO_ENABLED=0`.

The README records the earlier driver: the module previously used the [cgo](https://pkg.go.dev/cmd/cgo) binding [`github.com/mattn/go-sqlite3`](https://github.com/mattn/go-sqlite3). The current module does not import that package. Official SQLite documentation is at [sqlite.org/docs.html](https://sqlite.org/docs.html).

## Install and constructors

```text
go get github.com/dal-go/dalgo2sqlite
```

`NewDatabase(dbPath)` opens or creates the SQLite file at `dbPath`, pings the connection so a malformed file fails at construction time, wraps the `*sql.DB` with `dalgo2sql.NewDatabase`, and returns a `*Database`. `NewDatabaseWithOptions(dbPath, schema, opts)` is the same path with a `dal.Schema` and `dalgo2sql.DbOptions`. Use the options form when you need per-collection primary-key metadata, which the constructor documentation says is required for Insert, Get, and Delete with `map[string]any` data. If `opts.IsAlreadyExists` is nil, it defaults to this package's `IsAlreadyExists`.

`NewDatabase` passes `dbPath` straight to `sql.Open("sqlite", dbPath)`, so a path the [modernc.org/sqlite](https://pkg.go.dev/modernc.org/sqlite) driver accepts is a path this constructor accepts. The program checked for this page opened a regular file, the in-memory name `:memory:`, and the URI `file:memdb1?mode=memory&cache=shared`. Close the `*Database` when the work is finished; `Close` closes the underlying `*sql.DB`.

The [database abstraction layer](/articles/go-database-abstraction-layer/) and [repository pattern](/articles/go-repository-pattern/) articles show an `OpenSQLite` helper that uses `NewDatabaseWithOptions` and a `users` recordset. Those listings register the primary-key column and do not set `StructuredQueryDialect`. The example below sets `StructuredQueryDialect: "sqlite"` when you want dalgo2sql's SQLite structured-query compiler, which is described next.

## How structured queries are compiled

Structured queries are compiled by [dalgo2sql](https://github.com/dal-go/dalgo2sql), not by a second query engine inside dalgo2sqlite. The dalgo2sql README describes four paths, chosen when the database is opened:

1. A native compiler, if `DbOptions.NativeStructuredQueryCompiler` is set, writes the whole statement.
2. `DbOptions.StructuredQueryDialect: "sqlite"` uses dalgo2sql's SQLite structured emitter, `compileStructuredSQL`. Identifiers are quoted with backticks, with a backtick in a name doubled, and values are passed as bound arguments with the `?` placeholder. That path is built around SQLite's dynamic typing. When the dialect is `"sqlite"`, `dalgo2sql.NewDatabase` also returns its SQLite protected read/write profile; the README says that profile exists for SQLite only.
3. `"postgres"`, `"mysql"`, `"oracle"`, or `"sqlserver"` use the typed SQL compiler for those engines.
4. No dialect and no native compiler uses the legacy text emitter.

`dalgo2sqlite.NewDatabase` and `NewDatabaseWithOptions` do not set `StructuredQueryDialect` themselves. An empty options value therefore takes path 4 unless you set the dialect or a native compiler in `DbOptions`. To use the SQLite emitter and the protected profile, pass `StructuredQueryDialect: "sqlite"`.

## Schema, DDL, and transactions

`*Database` implements `dbschema.SchemaReader`. `ListCollections`, `DescribeCollection`, and `ListIndexes` read `sqlite_master` and PRAGMA helpers such as `pragma_table_info`, `pragma_index_list`, and `pragma_index_info`. `ListViews` and `ListSourceViews` list view definitions. `ListConstraints` and `ListReferrers` cover primary keys, unique constraints, and foreign keys that SQLite records. `ListConstraints` does not enumerate CHECK clauses (the implementation notes that SQLite does not expose CHECK source portably). `CheckSourceConstraints` asks SQLite to verify table, index, and CHECK constraints. `OpenSourceRows` streams native table rows. `NewSchemaReader` and `NewLenientSchemaReader` build a read-only `SchemaReader` on an existing `*sql.DB` you already opened. `LenientSchema()` returns a second `*Database` over the same connection whose schema reads describe a file the way SQLite lists it, including some shapes a lossless export would refuse; closing either value closes the shared pool, so close the owner.

`*Database` also implements `ddl.SchemaModifier`. `CreateCollection` issues SQLite `CREATE TABLE` and any `CREATE INDEX` from the collection definition. `DropCollection` drops a table. `AlterCollection` applies add, drop, and modify operations, including `CREATE INDEX` and `DROP INDEX`, inside one transaction. A column type change uses SQLite's table-rewrite sequence (create a new table, copy rows, drop the original, rename); the code documents that secondary indexes on the rewritten table are not recreated automatically. `SupportsTransactionalDDL()` is true. Application code can call [`ddl.CreateCollection`](https://pkg.go.dev/github.com/dal-go/dalgo/ddl) with a `dal.DB` that implements `SchemaModifier`, which is how the articles' `EnsureUsersTable` helper works.

Transactions use the same callback workers as the rest of DALgo, delegated to dalgo2sql: `RunReadonlyTransaction` and `RunReadwriteTransaction` on `dal.DB`. Writes that should run through the validating write pipeline belong in the read-write callback. `Get` is available on `dal.DB` itself. `Set`, `Insert`, `Upsert`, `Delete`, and `Update` also exist on `*Database`, but `UpdateRecord` at the database level returns `dal.ErrNotImplementedYet`; the package comment says to use `Update` with an explicit key, or `UpdateRecord` inside `RunReadwriteTransaction`, where the transaction object supports it. A short Firestore-shaped walkthrough of the same create, read, update, and delete calls is in [Firestore in Go: CRUD and transactions with DALgo](/articles/go-firestore-tutorial/).

An optional API, `OpenTableRead`, returns a read-only `TableReadSpan` over one existing SQLite file for a bounded, single-table read. The [dalgo2sqlite README](https://github.com/dal-go/dalgo2sqlite) states the limits of that profile and says `NewDatabase` behavior is unchanged.

## A short CRUD example

The listing below opens SQLite through `NewDatabaseWithOptions`, creates a `users` table, and runs insert, get, set, update, and delete inside one read-write transaction. It compiled and ran with `CGO_ENABLED=0` against dalgo2sqlite v0.6.5.

```go
package store

import (
	"context"

	"github.com/dal-go/dalgo/dal"
	"github.com/dal-go/dalgo/dbschema"
	"github.com/dal-go/dalgo/ddl"
	"github.com/dal-go/dalgo2sql"
	"github.com/dal-go/dalgo2sqlite"
	"github.com/dal-go/record"
	"github.com/dal-go/record/update"
)

// User is stored in the users table. SQL adapters write the exported field names as column names.
// The id is the record key, not a field of User.
type User struct {
	Name  string
	Email string
}

func (User) CollectionName() string { return "users" }

var Users = dal.CollectionOf[string, User]()

// OpenSQLite opens a SQLite file, or an in-memory database such as ":memory:".
// The recordset tells dalgo2sql that the key is the id column.
// StructuredQueryDialect selects dalgo2sql's SQLite query compiler.
// The caller closes the returned database.
func OpenSQLite(path string) (*dalgo2sqlite.Database, error) {
	return dalgo2sqlite.NewDatabaseWithOptions(path, dal.NewSchema(nil, nil), dalgo2sql.DbOptions{
		StructuredQueryDialect: "sqlite",
		Recordsets: map[string]*dalgo2sql.Recordset{
			"users": dalgo2sql.NewRecordset("users", dalgo2sql.Table, []dal.FieldRef{dal.Field("id")}),
		},
	})
}

func EnsureUsersTable(ctx context.Context, db dal.DB) error {
	return ddl.CreateCollection(ctx, db, dbschema.CollectionDef{
		Name: "users",
		Fields: []dbschema.FieldDef{
			{Name: "id", Type: dbschema.String, Nullable: false},
			{Name: "Name", Type: dbschema.String, Nullable: false},
			{Name: "Email", Type: dbschema.String, Nullable: false},
		},
		PrimaryKey: []dal.FieldName{"id"},
	})
}

func CreateUser(ctx context.Context, db dal.DB, id string, user User) error {
	return db.RunReadwriteTransaction(ctx, func(ctx context.Context, tx dal.ReadwriteTransaction) error {
		_, err := Users.InsertWithID(ctx, tx, id, user)
		return err
	})
}

func LoadUser(ctx context.Context, db dal.DB, id string) (User, error) {
	return Users.GetData(ctx, db, id)
}

func SaveUser(ctx context.Context, db dal.DB, id string, user User) error {
	return db.RunReadwriteTransaction(ctx, func(ctx context.Context, tx dal.ReadwriteTransaction) error {
		return Users.SetByID(ctx, tx, id, user)
	})
}

func RenameUser(ctx context.Context, db dal.DB, id, name string) error {
	return db.RunReadwriteTransaction(ctx, func(ctx context.Context, tx dal.ReadwriteTransaction) error {
		return Users.UpdateByID(ctx, tx, id, []update.Update{update.ByFieldName("Name", name)})
	})
}

func RemoveUser(ctx context.Context, db dal.DB, id string) error {
	return db.RunReadwriteTransaction(ctx, func(ctx context.Context, tx dal.ReadwriteTransaction) error {
		return Users.DeleteByID(ctx, tx, id)
	})
}

func Missing(err error) bool {
	return record.IsNotFound(err)
}
```

A plain `dal.DB` is a read session, so `GetData` can take it directly. Writes take a `dal.WriteSession`, which a plain `dal.DB` is not, so `InsertWithID`, `SetByID`, `UpdateByID`, and `DeleteByID` run inside `RunReadwriteTransaction`.

## When to choose SQLite

Choose SQLite when the database should live in-process: a local application, a desktop or CLI tool, an embedded store, or a test that wants a real SQL engine in a temporary file or in memory. The [in-memory adapter](https://github.com/dal-go/dalgo/tree/main/adapters/dalgo2memory) in the core module is the lighter test double when you do not need SQL itself; `SingleWriterProfile()` is the profile that copies a single-writer store such as SQLite.

Choose [dalgo2postgres](https://github.com/dal-go/dalgo2postgres) when the service needs a networked PostgreSQL server, concurrent writers, or PostgreSQL-specific SQL. [Switching between PostgreSQL and Firestore in Go](/articles/switch-postgres-to-firestore/) shows that constructor and what still differs when the same records move to Firestore. Choose [dalgo2firestore](https://github.com/dal-go/dalgo2firestore) when the product is a Cloud Firestore document store; [Firestore in Go: CRUD and transactions with DALgo](/articles/go-firestore-tutorial/) is that walkthrough.

DALgo does not hide every engine difference. A refused schema description comes back as a `*dbschema.NotSupportedError`, for example when a table has a generated or hidden column, an empty name, or an unrecognized SQLite type. Database-level `UpdateRecord` returns `dal.ErrNotImplementedYet`. Some refusals from the underlying dalgo2sql layer wrap `dal.ErrNotSupported`. [When to use DALgo, and when not to](/articles/when-to-use-dalgo/) is the limit list.

## Capability summary

The [adapter matrix](/adapters/#adapter-sqlite) is the inventory. For the Go module it lists these capabilities as implemented: point-read, structured-query, native-sql, crud, transactions, and schema, with the limit "Backend/dialect restrictions apply." This page does not add capabilities to that row. The same matrix has a TypeScript row for a different package, `@dalgo/sqlite-wasm`; that is not this Go module.

## FAQ

### What is dalgo2sqlite?

dalgo2sqlite is the SQLite-specific DALgo adapter for Go. It opens a SQLite file or an in-memory database with `modernc.org/sqlite`, wraps dalgo2sql to implement `dal.DB`, and adds SQLite schema introspection, DDL, and a single-writer concurrency hint. The module is [`github.com/dal-go/dalgo2sqlite`](https://github.com/dal-go/dalgo2sqlite).

### Does dalgo2sqlite use CGo?

No. The current module registers `modernc.org/sqlite`, a pure-Go port of SQLite, and opens it with the `"sqlite"` driver name. The README and package comment state that this path uses `CGO_ENABLED=0`. The earlier cgo binding `github.com/mattn/go-sqlite3` is not a dependency of the current module.

### Can I use an in-memory SQLite database with DALgo?

Yes. `NewDatabase` and `NewDatabaseWithOptions` pass the path to `sql.Open("sqlite", dbPath)`. The program checked for this page opened `:memory:` and `file:memdb1?mode=memory&cache=shared` as well as a regular file. Use a file in the same way when you want the data to outlive the process.

### When should I use SQLite instead of PostgreSQL or Firestore?

Use SQLite when the store should be in-process: a local app, an embedded tool, or a test that wants a real SQL engine. Use dalgo2postgres when you need a PostgreSQL server, and dalgo2firestore when the product is Cloud Firestore. The same domain functions can sit on `dal.DB` in each case, with table DDL on the SQL adapters and a Firestore client lifecycle on Firestore.

## Sources

Public module documentation and source, checked on 25 November 2026.

- [dal-go/dalgo2sqlite](https://github.com/dal-go/dalgo2sqlite) v0.6.5, commit `64d9e69adc5ab68ad0272b1c402ffb796aee320e`, including `NewDatabase`, `NewDatabaseWithOptions`, `RunReadonlyTransaction`, `RunReadwriteTransaction`, schema and DDL types, and the `modernc.org/sqlite` driver registration (`sql.Open("sqlite", dbPath)`, `CGO_ENABLED=0`). License: [MIT](https://github.com/dal-go/dalgo2sqlite/blob/main/LICENSE).
- [dal-go/dalgo](https://github.com/dal-go/dalgo) v0.102.6, [dal-go/dalgo2sql](https://github.com/dal-go/dalgo2sql) v0.32.0 (the version dalgo2sqlite v0.6.5 requires), [dal-go/record](https://github.com/dal-go/record) v0.1.5. DALgo license: [MIT](https://github.com/dal-go/dalgo/blob/main/LICENSE).
- [modernc.org/sqlite](https://pkg.go.dev/modernc.org/sqlite@v1.63.0) v1.63.0, the driver dalgo2sqlite v0.6.5 imports. The earlier cgo driver is documented in the dalgo2sqlite README as [`github.com/mattn/go-sqlite3`](https://github.com/mattn/go-sqlite3).
- [SQLite documentation](https://sqlite.org/docs.html).
- [Adapter matrix](/adapters/) SQLite row, and the dalgo2sql README on `StructuredQueryDialect: "sqlite"`, `compileStructuredSQL`, identifier quoting, and the `?` placeholder.
