---
title: Database abstraction layer in Go: what it is and when you need one
slug: go-database-abstraction-layer
date: 2026-11-07
description: A Go database abstraction for services that swap stores, and how DALgo compares with database/sql, sqlx, GORM, ent, and sqlc.
summary: A database abstraction layer lets Go domain code talk to records, queries, and transactions while the storage backend stays replaceable. This is the definition, a compilable DALgo example, and a fair look at the usual alternatives.
order: 1
schema: techarticle
---

A [database abstraction layer](https://en.wikipedia.org/wiki/Database_abstraction_layer) is a library that sits between application code and a database, so the program can store and load records without calling one vendor's client. DAL is the usual shortening of "database abstraction layer". [CRUD](https://en.wikipedia.org/wiki/Create,_read,_update_and_delete) is the name for the four record operations: create, read, update, and delete. [DALgo](/) is an [open-source](https://github.com/dal-go/dalgo) database abstraction layer for the [Go](https://go.dev/) programming language and for TypeScript: the Go module production services import is [`github.com/dal-go/dalgo`](https://github.com/dal-go/dalgo), and the TypeScript package is [`@dalgo/core`](https://github.com/dal-go/dalgo-js). [SQL](https://en.wikipedia.org/wiki/SQL), short for Structured Query Language, is the language relational databases use for queries. An [ORM](https://en.wikipedia.org/wiki/Object%E2%80%93relational_mapping), short for object-relational mapper, is a library that turns language objects into rows of a relational database and back. An API, short for application programming interface, is the set of types and functions a program calls; in DALgo that set is the [`dal`](https://pkg.go.dev/github.com/dal-go/dalgo/dal) package.

The rest of this page is that API in compilable Go, the adapters that can sit behind it, and a comparison with [`database/sql`](https://pkg.go.dev/database/sql), [sqlx](https://github.com/jmoiron/sqlx), [GORM](https://gorm.io/docs/), [ent](https://entgo.io/docs/getting-started), and [sqlc](https://docs.sqlc.dev/). [DALgo vs GORM: a gorm alternative](/articles/dalgo-vs-gorm/) stays on that pair. The companion piece, [Repository pattern in Go with a swappable storage backend](/articles/go-repository-pattern/), puts a smaller interface in front of the same handle. [Why use DALgo](/articles/why-use-dalgo/) is the project case, and [When to use DALgo, and when not to](/articles/when-to-use-dalgo/) is the limit list. The Go overview lives at [/go/](/go/), the handle itself at [/interfaces/](/interfaces/), typed collections at [/collections/](/collections/), and the support matrix at [/adapters/](/adapters/).

## The handle domain code accepts

A DALgo adapter implements [`dal.Backend`](https://pkg.go.dev/github.com/dal-go/dalgo/dal). Application code should accept [`dal.DB`](https://pkg.go.dev/github.com/dal-go/dalgo/dal#DB), which `dal.NewDB` builds around that backend. The wrapper owns the write pipeline, so validation and before-save hooks run before the adapter is entered. Reads are available on `dal.DB` because it includes `dal.ReadSession`. Writes are not: `dal.WriteSession` is reached from the transaction callback, `dal.ReadwriteTransaction`. Passing a plain `dal.DB` to a write is a compile error.

Day-to-day create, read, update, and delete can sit on `dal.Collection[K, T]`. The handle holds no connection. `CollectionOf` reads the collection name from a value-receiver `CollectionName` method. `GetData` takes a read session and returns `T`. `SetByID` takes a write session. A missing row comes back as an error that [`record.IsNotFound`](https://pkg.go.dev/github.com/dal-go/record) recognizes. That function lives in [`github.com/dal-go/record`](https://github.com/dal-go/record), which the current core imports; older README samples that call `dal.IsNotFound` describe an earlier packaging.

```go
package store

import (
	"context"

	"cloud.google.com/go/firestore"
	"github.com/dal-go/dalgo/adapters/dalgo2memory"
	"github.com/dal-go/dalgo/dal"
	"github.com/dal-go/dalgo/dbschema"
	"github.com/dal-go/dalgo/ddl"
	"github.com/dal-go/dalgo2firestore"
	"github.com/dal-go/dalgo2postgres"
	"github.com/dal-go/dalgo2sql"
	"github.com/dal-go/dalgo2sqlite"
	"github.com/dal-go/record"
)

// User is the record stored in the "users" collection.
// SQL adapters write the exported field names as column names.
// The id is the record key, not a field of User.
type User struct {
	Name  string
	Email string
}

func (User) CollectionName() string { return "users" }

// Users is a session-less handle. Reads take a dal.ReadSession.
// Writes take a dal.WriteSession, which a plain dal.DB is not.
var Users = dal.CollectionOf[string, User]()

// LoadUser reads one user. db is the database abstraction: memory, SQL, or Firestore.
func LoadUser(ctx context.Context, db dal.DB, id string) (User, error) {
	user, err := Users.GetData(ctx, db, id)
	if err != nil {
		return User{}, err
	}
	return user, nil
}

// SaveUser writes one user inside the adapter's transaction.
// A plain dal.DB is not a WriteSession, so SetByID is only reachable on tx.
func SaveUser(ctx context.Context, db dal.DB, id string, user User) error {
	return db.RunReadwriteTransaction(ctx, func(ctx context.Context, tx dal.ReadwriteTransaction) error {
		return Users.SetByID(ctx, tx, id, user)
	})
}

// Missing reports a not-found read. The sentinel lives in github.com/dal-go/record.
func Missing(err error) bool {
	return record.IsNotFound(err)
}

// OpenMemoryForTests builds the in-memory adapter.
// The profile names the backend the stand-in copies.
// FirestoreProfile follows Firestore transaction rules.
// SingleWriterProfile follows a single-writer store such as SQLite.
func OpenMemoryForTests(profile dalgo2memory.Profile) dal.DB {
	return dalgo2memory.New(profile)
}

// OpenSQLite opens a SQLite file through dalgo2sqlite.
// The recordset tells dalgo2sql that the key id is the "id" column.
// The caller closes the returned database.
func OpenSQLite(path string) (*dalgo2sqlite.Database, error) {
	return dalgo2sqlite.NewDatabaseWithOptions(path, dal.NewSchema(nil, nil), dalgo2sql.DbOptions{
		Recordsets: map[string]*dalgo2sql.Recordset{
			"users": dalgo2sql.NewRecordset("users", dalgo2sql.Table, []dal.FieldRef{dal.Field("id")}),
		},
	})
}

// EnsureUsersTable creates the SQL table these functions write.
// Memory and Firestore do not use this. SQLite and Postgres do
// when the database implements ddl.SchemaModifier.
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

// OpenPostgres opens PostgreSQL. Constructors force the postgres dialect,
// so structured queries do not fall through to the legacy text emitter.
// The caller closes the returned database.
func OpenPostgres(dsn string) (*dalgo2postgres.Database, error) {
	return dalgo2postgres.NewDatabase(dsn)
}

// OpenFirestore wraps a Firestore client. The caller closes the client.
// dalgo2firestore.NewDatabase panics on an empty id or a nil client.
func OpenFirestore(ctx context.Context, projectID string) (dal.DB, *firestore.Client, error) {
	client, err := firestore.NewClient(ctx, projectID)
	if err != nil {
		return nil, nil, err
	}
	return dalgo2firestore.NewDatabase(projectID, client), client, nil
}
```

`LoadUser` and `SaveUser` name `dal.DB` and nothing else about storage. The same two functions are what the test below calls once the process has chosen an adapter.

## One pair of functions, three ways to open the database

[`dalgo2memory`](https://github.com/dal-go/dalgo/tree/main/adapters/dalgo2memory) is the in-memory adapter in the core module. `New` requires a profile, because the stand-in copies one backend's transaction rules. `FirestoreProfile` follows [Cloud Firestore](https://cloud.google.com/firestore/docs) transaction behavior, including a rejection of a read that follows a write inside the transaction. `SingleWriterProfile` follows a store that serializes writers, which is the shape SQLite has. `NewDB` still exists and calls `New(FirestoreProfile)`; the constructor the package documents as current is `New` with the profile written at the call site.

[`dalgo2sqlite`](https://github.com/dal-go/dalgo2sqlite) opens a SQLite file with the pure-Go `modernc.org/sqlite` driver and returns a `*Database` that implements `dal.DB`. The `Recordset` in `OpenSQLite` tells [`dalgo2sql`](https://github.com/dal-go/dalgo2sql) that the record key is the column `id`. Other columns come from the exported field names of `User`, so the table has `Name` and `Email`, matching the Go identifiers. [`ddl.CreateCollection`](https://pkg.go.dev/github.com/dal-go/dalgo/ddl) asks the driver for `ddl.SchemaModifier`. The SQLite and [Postgres](https://github.com/dal-go/dalgo2postgres) drivers both implement that method. The memory adapter and [`dalgo2firestore`](https://github.com/dal-go/dalgo2firestore) are not where this table helper belongs: memory has no SQL catalog, and Firestore stores the struct as a document.

[`dalgo2postgres.NewDatabase`](https://github.com/dal-go/dalgo2postgres) takes a data-source name and forces the `postgres` structured-query dialect, so a structured query on that handle does not fall through to the legacy text emitter that writes values into SQL text. [`dalgo2firestore.NewDatabase`](https://github.com/dal-go/dalgo2firestore) takes a database id and a `*firestore.Client` from `cloud.google.com/go/firestore`. It panics if the id is empty or the client is nil. The caller closes the Firestore client; `dal.DB` has no `Close` method. The SQLite and Postgres `*Database` values do, and the caller closes those.

```go
package store

import (
	"context"
	"path/filepath"
	"testing"

	"github.com/dal-go/dalgo/adapters/dalgo2memory"
	"github.com/dal-go/dalgo/dal"
)

func TestSameFunctionsOnMemoryAndSQLite(t *testing.T) {
	ctx := context.Background()
	want := User{Name: "Ada Lovelace", Email: "ada@example.com"}

	roundTrip(t, ctx, OpenMemoryForTests(dalgo2memory.SingleWriterProfile()), want)
	roundTrip(t, ctx, OpenMemoryForTests(dalgo2memory.FirestoreProfile()), want)

	sqlDB, err := OpenSQLite(filepath.Join(t.TempDir(), "users.db"))
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { _ = sqlDB.Close() })
	if err := EnsureUsersTable(ctx, sqlDB); err != nil {
		t.Fatal(err)
	}
	roundTrip(t, ctx, sqlDB, want)
}

func roundTrip(t *testing.T, ctx context.Context, db dal.DB, want User) {
	t.Helper()
	if _, err := LoadUser(ctx, db, "u1"); !Missing(err) {
		t.Fatalf("LoadUser missing: %v", err)
	}
	if err := SaveUser(ctx, db, "u1", want); err != nil {
		t.Fatal(err)
	}
	got, err := LoadUser(ctx, db, "u1")
	if err != nil {
		t.Fatal(err)
	}
	if got != want {
		t.Fatalf("got %+v, want %+v", got, want)
	}
}
```

That test was run on 7 November 2026 against `github.com/dal-go/dalgo` v0.101.4, `dalgo2sqlite` v0.6.1, `dalgo2sql` v0.32.2, `dalgo2postgres` v0.11.0, `dalgo2firestore` v0.11.0, and `github.com/dal-go/record` v0.1.5. `go test` passed for both memory profiles and for a temporary SQLite file. `OpenPostgres` and `OpenFirestore` were compiled in the same package. This check did not open a Postgres server or a Firestore project, so it is evidence that those constructors type-check and that the shared functions run on the adapters the test actually opened. Adapter limits still live in each adapter README and in the [adapter matrix](/adapters/).

A service wires one of those openers in `main` and passes the `dal.DB` into `LoadUser` and `SaveUser`. A test wires `OpenMemoryForTests` and passes that value into the same functions. The domain functions stay put. [Queries](/queries/) that go beyond a point read use the structured builder (`dal.From`, `WhereField`, `OrderBy`, `Limit`) and can be serialized as [TugQL](/tugql/). An adapter that cannot run a query returns `dal.ErrNotSupported`.

## How the usual Go libraries answer a different question

These libraries are good at what their own docs say they do. None of the sentences below is a benchmark, and none is a claim about speed, popularity, or which one "wins".

| Library | What its docs say it is | Where the database shows up |
| --- | --- | --- |
| [`database/sql`](https://pkg.go.dev/database/sql) | A generic interface around SQL (or SQL-like) databases. | You write the SQL text, call `QueryRowContext`, and `Scan` into fields. The driver is one SQL driver. |
| [sqlx](https://github.com/jmoiron/sqlx) | A set of extensions on `database/sql`. The README says the sqlx types leave the underlying interfaces untouched, so they are a superset. | You still write SQL. `StructScan` and named queries sit on top of `*sql.DB`. There is no Firestore client in that design. |
| [GORM](https://gorm.io/docs/) | "The fantastic ORM library for Golang", described in its guide as a full-featured ORM, with associations, hooks, and auto migration. The [quick start](https://gorm.io/docs/index.html) opens a database through a driver; the sample uses SQLite. | Schema and queries are expressed as Go on a `*gorm.DB` aimed at a relational database. |
| [ent](https://entgo.io/docs/getting-started) | An entity framework: schema as Go code, static typing from code generation, graph edges. The getting-started page shows SQLite, PostgreSQL, and MySQL. | You generate a client and call builders such as `client.User.Create()`. The model is the generated graph, not a swappable document API. |
| [sqlc](https://docs.sqlc.dev/en/latest/tutorials/getting-started-postgresql.html) | A generator. You write SQL schema and queries; `sqlc generate` emits Go. The PostgreSQL tutorial uses `pgx`. | The SQL stays in the repository as the source of truth. The generated package talks to that engine. |

DALgo's job is the row those tools leave open: one record, query, and transaction API that also has adapters whose backend is not SQL. The core README states the matching limit in plain language: DALgo does not try to hide every database difference. `dal.ErrNotSupported` is how an adapter says so. A window function, a recursive common-table expression, or a Firestore realtime listener is a reason to call the driver that has that feature. [When to use DALgo, and when not to](/articles/when-to-use-dalgo/) walks those cases with the adapter READMEs.

Use `database/sql` or sqlx when the program is one SQL database and the team wants the statements in source control as SQL. Use sqlc when those statements should also produce the Go call sites. Use GORM or ent when the product is an object or entity model over a relational schema, including associations and migrations those projects document. [DALgo vs GORM: a gorm alternative](/articles/dalgo-vs-gorm/) is that GORM choice in more detail. Use DALgo when the same Go functions must run against more than one store, and a test double counts. The in-memory adapter, SQLite, Postgres, and Firestore in the listing above are that situation. The [repository article](/articles/go-repository-pattern/) is the next step when callers should not mention `dal.DB` at all.

## What you are buying, and what you still pin

The Go module is [MIT-licensed](https://github.com/dal-go/dalgo/blob/main/LICENSE). It is still a v0 module path: the example above pins v0.101.4, and a service should pin the version it has tested. Adapters are separate modules with their own versions. Read the adapter you deploy. A structured query that the memory adapter runs can still return `dal.ErrNotSupported` on another backend. That is the contract, documented in the [core README](https://github.com/dal-go/dalgo).

The TypeScript package follows the same idea and is a separate codebase. Use it for a browser or Node program that imports an adapter written against `@dalgo/core`. It does not execute the Go functions on this page.

## FAQ

### What is a golang database abstraction layer?

A database abstraction layer in Go is a library your domain code calls instead of a database driver. DALgo is one such layer: functions accept `dal.DB`, and an adapter supplies the database. The standard library's `database/sql` is a generic interface around SQL databases, which is a narrower seam.

### When does a Go service need one?

It needs one when the same functions will run, on purpose, against more than one store. A production database plus `dalgo2memory` in tests is enough. A service that will only ever speak one engine's SQL can stay on `database/sql`, sqlx, sqlc, GORM, or ent.

### Is DALgo an object-relational mapper?

DALgo is a database abstraction layer with adapters for SQL and for other stores, including Firestore, files, and memory. An object-relational mapper maps objects onto a relational schema. GORM and ent document that relational job. DALgo's SQL adapters map a key and exported struct fields onto columns; they also return `dal.ErrNotSupported` when a backend cannot do what was asked.

### Can the same Go functions use memory, SQLite, and Firestore?

`LoadUser` and `SaveUser` above take `dal.DB`. The test ran them on `dalgo2memory` (Firestore profile and single-writer profile) and on `dalgo2sqlite` after `EnsureUsersTable`. `OpenFirestore` returns a `dal.DB` from `dalgo2firestore.NewDatabase` and was compiled in that package. Firestore still has its own client lifecycle, and SQL still needs the table. The [adapter matrix](/adapters/) is the list of what each backend actually implements.

## Sources

Public module docs and repository source, checked on 7 November 2026. The Go listings on this page were `go test`ed that day at the versions named above.

- [dal-go/dalgo](https://github.com/dal-go/dalgo) v0.101.4, including `dal.CollectionOf`, `dalgo2memory.New`, `FirestoreProfile`, and `SingleWriterProfile`. License: [MIT](https://github.com/dal-go/dalgo/blob/main/LICENSE).
- [dal-go/record](https://github.com/dal-go/record) v0.1.5 (`record.IsNotFound`).
- [dal-go/dalgo2sql](https://github.com/dal-go/dalgo2sql) v0.32.2, [dalgo2sqlite](https://github.com/dal-go/dalgo2sqlite) v0.6.1, [dalgo2postgres](https://github.com/dal-go/dalgo2postgres) v0.11.0, [dalgo2firestore](https://github.com/dal-go/dalgo2firestore) v0.11.0.
- [`database/sql`](https://pkg.go.dev/database/sql), [jmoiron/sqlx](https://github.com/jmoiron/sqlx), [GORM](https://gorm.io/docs/index.html), [ent getting started](https://entgo.io/docs/getting-started), [sqlc PostgreSQL tutorial](https://docs.sqlc.dev/en/latest/tutorials/getting-started-postgresql.html).
- [Wikipedia: database abstraction layer](https://en.wikipedia.org/wiki/Database_abstraction_layer), [CRUD](https://en.wikipedia.org/wiki/Create,_read,_update_and_delete), [SQL](https://en.wikipedia.org/wiki/SQL), [object-relational mapping](https://en.wikipedia.org/wiki/Object%E2%80%93relational_mapping).
