---
title: Repository pattern in Go with a swappable storage backend
slug: go-repository-pattern
date: 2026-11-07
description: The Go repository pattern with a swappable backend: a golang repository pattern on DALgo, using memory in tests and SQL or Firestore in production.
summary: A Go repository is a small interface around storage. With DALgo behind it, the same repository type can be constructed on the in-memory adapter, SQLite, Postgres, or Firestore.
order: 2
schema: techarticle
---

The [repository pattern](https://martinfowler.com/eaaCatalog/repository.html), as Martin Fowler describes it, mediates between the domain and data-mapping layers using a collection-like interface for accessing domain objects. In [Go](https://go.dev/), that interface is an ordinary `interface` type: methods such as `Get` and `Save`, with parameters the rest of the program already understands. A [database abstraction layer](https://en.wikipedia.org/wiki/Database_abstraction_layer) (DAL) is the library under the repository that speaks to more than one store through one application programming interface (API). [DALgo](/) is an [open-source](https://github.com/dal-go/dalgo) DAL; the Go module is [`github.com/dal-go/dalgo`](https://github.com/dal-go/dalgo), and the TypeScript package with the same idea is [`@dalgo/core`](https://github.com/dal-go/dalgo-js). [CRUD](https://en.wikipedia.org/wiki/Create,_read,_update_and_delete) — create, read, update, and delete — stays on the repository methods. [SQL](https://en.wikipedia.org/wiki/SQL), short for Structured Query Language, is the query language of a relational database. An [ORM](https://en.wikipedia.org/wiki/Object%E2%80%93relational_mapping), short for object-relational mapper, maps objects onto one relational schema. The repository on this page is a port; DALgo is one implementation of the storage behind that port.

[Database abstraction layer in Go: what it is and when you need one](/articles/go-database-abstraction-layer/) defines the layer and compares it with `database/sql`, sqlx, GORM, ent, and sqlc. This page puts a repository in front of [`dal.DB`](https://pkg.go.dev/github.com/dal-go/dalgo/dal#DB). The handle is documented at [/interfaces/](/interfaces/), typed collections at [/collections/](/collections/), the Go overview at [/go/](/go/), and the backends at [/adapters/](/adapters/). [Why use DALgo](/articles/why-use-dalgo/) and [When to use DALgo, and when not to](/articles/when-to-use-dalgo/) are the wider case and the limits.

## The interface callers see

A repository here is three things. The interface is what HTTP handlers, jobs, and tests accept. The struct is the only type that holds a `dal.DB`. The constructor is the only place that learns which adapter was opened. Callers of `UserRepository` never import an adapter, and they never mention Structured Query Language, Cloud Firestore, or `*sql.DB`.

The implementation uses a typed collection. `dal.CollectionOf[string, User]` builds a session-less handle whose name comes from `User.CollectionName`. `GetData` accepts a `dal.ReadSession`, and a `dal.DB` satisfies that. `SetByID` accepts a `dal.WriteSession`. A plain `dal.DB` is not a write session, so `Save` enters `RunReadwriteTransaction` and uses the transaction the adapter passes in. A missing record is `record.IsNotFound` from [`github.com/dal-go/record`](https://github.com/dal-go/record).

```go
package users

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

// UserRepository is the port the rest of the program calls.
// It does not mention SQL, Firestore, or an adapter.
type UserRepository interface {
	Get(ctx context.Context, id string) (User, error)
	Save(ctx context.Context, id string, user User) error
}

type userRepository struct {
	db dal.DB
}

// NewUserRepository binds the repository to any dal.DB.
func NewUserRepository(db dal.DB) UserRepository {
	return userRepository{db: db}
}

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

func (r userRepository) Get(ctx context.Context, id string) (User, error) {
	return LoadUser(ctx, r.db, id)
}

func (r userRepository) Save(ctx context.Context, id string, user User) error {
	return SaveUser(ctx, r.db, id, user)
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

// EnsureUsersTable creates the SQL table the repository writes.
// Memory and Firestore do not use this. SQLite and Postgres do,
// and only when the database implements ddl.SchemaModifier.
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

`LoadUser` and `SaveUser` are the same operations the [abstraction-layer article](/articles/go-database-abstraction-layer/) shows taking a `dal.DB` directly. The repository methods delegate to them. That split is deliberate: code that is allowed to know about DALgo can call the functions, and code that should stay storage-agnostic accepts `UserRepository`.

## Swapping the backend

`NewUserRepository` takes any `dal.DB`. These constructors produce one:

- `OpenMemoryForTests(dalgo2memory.SingleWriterProfile())` for a stand-in that serializes writers, the way SQLite does. `FirestoreProfile()` copies [Cloud Firestore](https://cloud.google.com/firestore/docs) transaction rules instead. Both profiles are part of [`dalgo2memory`](https://github.com/dal-go/dalgo/tree/main/adapters/dalgo2memory) in the core module. `New` requires the profile; there is no silent default.
- `OpenSQLite` uses [`dalgo2sqlite`](https://github.com/dal-go/dalgo2sqlite). The recordset names `id` as the primary-key column. `EnsureUsersTable` creates `users` through [`ddl.CreateCollection`](https://pkg.go.dev/github.com/dal-go/dalgo/ddl), which the SQLite driver implements as `ddl.SchemaModifier`. Columns other than the key use the exported field names `Name` and `Email`.
- `OpenPostgres` uses [`dalgo2postgres.NewDatabase`](https://github.com/dal-go/dalgo2postgres). The constructor forces the `postgres` dialect so structured queries do not use the legacy text emitter. That driver also implements `CreateCollection`. The caller closes `*Database`.
- `OpenFirestore` builds a client with `cloud.google.com/go/firestore` and wraps it with [`dalgo2firestore.NewDatabase`](https://github.com/dal-go/dalgo2firestore). The caller closes the client. Firestore stores the struct as a document, so `EnsureUsersTable` is not part of that path.

```go
package users

import (
	"context"
	"path/filepath"
	"testing"

	"github.com/dal-go/dalgo/adapters/dalgo2memory"
)

func TestRepositorySwapsMemoryAndSQLite(t *testing.T) {
	ctx := context.Background()
	want := User{Name: "Ada Lovelace", Email: "ada@example.com"}

	memory := OpenMemoryForTests(dalgo2memory.SingleWriterProfile())
	assertRoundTrip(t, ctx, NewUserRepository(memory), want)

	firestoreShaped := OpenMemoryForTests(dalgo2memory.FirestoreProfile())
	assertRoundTrip(t, ctx, NewUserRepository(firestoreShaped), want)

	sqlDB, err := OpenSQLite(filepath.Join(t.TempDir(), "users.db"))
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { _ = sqlDB.Close() })
	if err := EnsureUsersTable(ctx, sqlDB); err != nil {
		t.Fatal(err)
	}
	assertRoundTrip(t, ctx, NewUserRepository(sqlDB), want)
}

func assertRoundTrip(t *testing.T, ctx context.Context, repo UserRepository, want User) {
	t.Helper()
	if _, err := repo.Get(ctx, "u1"); !Missing(err) {
		t.Fatalf("Get missing user: %v", err)
	}
	if err := repo.Save(ctx, "u1", want); err != nil {
		t.Fatal(err)
	}
	got, err := repo.Get(ctx, "u1")
	if err != nil {
		t.Fatal(err)
	}
	if got != want {
		t.Fatalf("got %+v, want %+v", got, want)
	}
}
```

`go test` on 7 November 2026 ran this package against `github.com/dal-go/dalgo` v0.101.4, `dalgo2sqlite` v0.6.1, `dalgo2sql` v0.32.2, `dalgo2postgres` v0.11.0, `dalgo2firestore` v0.11.0, and `record` v0.1.5. The test passed for both memory profiles and for SQLite. Postgres and Firestore constructors were part of the compilation. They were not pointed at a live server in this check. A production `main` would call `OpenPostgres` or `OpenFirestore`, pass the `dal.DB` to `NewUserRepository`, and give that interface to the rest of the process. The test does the same with memory and SQLite.

The swap stops being free when a call leaves the intersection of the adapters you actually run. `dal.ErrNotSupported` is the error an adapter returns for a capability it does not have. A repository method that runs a join, a `GROUP BY`, or a decimal aggregate on memory has not shown that Firestore will run it. Keep those methods inside the [adapter matrix](/adapters/), or return the adapter error to the caller on purpose. [Queries](/queries/) and [TugQL](/tugql/) are the structured form when a method needs more than a point read.

## Where an ORM, sqlc, or database/sql still fits

The repository pattern does not require DALgo. A `UserRepository` can be implemented with [`database/sql`](https://pkg.go.dev/database/sql), with [sqlx](https://github.com/jmoiron/sqlx) on top of it, with a [sqlc](https://docs.sqlc.dev/en/latest/tutorials/getting-started-postgresql.html)-generated package, or with [GORM](https://gorm.io/docs/) or [ent](https://entgo.io/docs/getting-started). Those are honest implementations when every deployment is one SQL database. GORM's guide describes a full-featured ORM and shows a driver-backed `*gorm.DB`. ent's getting-started page generates an entity client for SQLite, PostgreSQL, or MySQL. sqlc generates Go from SQL you write. sqlx extends `database/sql` and keeps SQL in the call. Each of those can hide behind `Get` and `Save`. What they do not give you is the same concrete type opened with `dalgo2memory`, `dalgo2sqlite`, and `dalgo2firestore`.

DALgo earns the place inside the repository when that swap is a requirement, including the test double. The Go module is [MIT-licensed](https://github.com/dal-go/dalgo/blob/main/LICENSE) and still on a v0 path; pin the modules the test used, or newer ones you have run yourself. Handlers should depend on `UserRepository`. The package that calls `OpenPostgres` can depend on the adapter. That is the same shape the [bots framework](https://github.com/bots-go-framework/bots-fw) uses when it keeps a small store port in the core and puts DALgo in an optional implementation, described in [Why use DALgo](/articles/why-use-dalgo/).

## FAQ

### What is the golang repository pattern?

The repository pattern in Go is an interface that stands for a collection of domain objects. Callers use the interface. One package implements it with a database. Fowler's [repository](https://martinfowler.com/eaaCatalog/repository.html) is the description this page follows. The listing above is a `UserRepository` with `Get` and `Save`.

### Does the repository replace the database abstraction layer?

The repository is the port. DALgo is the implementation behind `NewUserRepository`. A program can have the interface with a `database/sql` implementation instead. Use DALgo inside the repository when the implementation must be constructable on more than one adapter.

### How do tests swap the storage backend?

Construct `dalgo2memory` with the profile that matches production transaction rules, pass that `dal.DB` to `NewUserRepository`, and pass the `UserRepository` into the code under test. The test on this page also opens SQLite, creates the `users` table, and calls the same interface. The code under test does not import either adapter.

### Will every adapter honor every repository method?

A method written against `dal.DB` runs where the adapter implements that operation. Point `Get` and `Set` in the test ran on memory and SQLite. A method that needs a query the adapter cannot run returns `dal.ErrNotSupported`. Check the adapter README and the [adapter matrix](/adapters/) before promising the method on that backend.

## Sources

Public module docs and the compilable listing, checked on 7 November 2026.

- [dal-go/dalgo](https://github.com/dal-go/dalgo) v0.101.4 and [dal-go/record](https://github.com/dal-go/record) v0.1.5. License: [MIT](https://github.com/dal-go/dalgo/blob/main/LICENSE).
- [dalgo2sqlite](https://github.com/dal-go/dalgo2sqlite) v0.6.1, [dalgo2sql](https://github.com/dal-go/dalgo2sql) v0.32.2, [dalgo2postgres](https://github.com/dal-go/dalgo2postgres) v0.11.0, [dalgo2firestore](https://github.com/dal-go/dalgo2firestore) v0.11.0.
- [Martin Fowler, Repository](https://martinfowler.com/eaaCatalog/repository.html).
- [`database/sql`](https://pkg.go.dev/database/sql), [sqlx](https://github.com/jmoiron/sqlx), [GORM](https://gorm.io/docs/index.html), [ent](https://entgo.io/docs/getting-started), [sqlc](https://docs.sqlc.dev/en/latest/tutorials/getting-started-postgresql.html).
