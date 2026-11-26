---
title: Switching between PostgreSQL and Firestore in Go without rewriting business code
slug: switch-postgres-to-firestore
date: 2026-11-23
description: Switch Postgres to Firestore in Go without rewriting business code, using DALgo adapters for PostgreSQL, Cloud Firestore, and in-memory tests.
summary: Write a small users repository once against dal.DB, then open it on PostgreSQL, Cloud Firestore, or DALgo's in-memory adapter. This page shows what those calls share, what still differs, and how to copy records through the same interface.
order: 1
schema: techarticle
---

A [database abstraction layer](https://en.wikipedia.org/wiki/Database_abstraction_layer) (DAL) is a library that sits between application code and a database, so the program can store and load records without calling one vendor's client. [DALgo](/) is an [open-source](https://github.com/dal-go/dalgo) database abstraction layer for [Go](https://go.dev/); the Go module is [`github.com/dal-go/dalgo`](https://github.com/dal-go/dalgo). [Database abstraction layer in Go](/articles/go-database-abstraction-layer/) is that definition for this project. An adapter is the DALgo module that speaks to one backend. [PostgreSQL](https://www.postgresql.org/docs/current/) is a relational database that stores rows in tables and is queried with [SQL](https://en.wikipedia.org/wiki/SQL) (Structured Query Language). [Cloud Firestore](https://firebase.google.com/docs/firestore) is Google's document database: it stores documents, each a set of named fields, in collections. [CRUD](https://en.wikipedia.org/wiki/Create,_read,_update_and_delete) is short for create, read, update, and delete, the four record operations. [DDL](https://en.wikipedia.org/wiki/Data_definition_language) (data definition language) is the SQL used to create and alter tables. An [ORM](https://en.wikipedia.org/wiki/Object%E2%80%93relational_mapping) (object-relational mapper) maps objects onto a relational schema; this page is about swapping adapters, not about choosing an ORM.

The [quick start](/quickstart/) and the [adapter matrix](/adapters/) are the product overview. This page is the walkthrough the home page's "swap Postgres for Firestore" line does not itself show: one small `users` domain written against [`dal.DB`](https://pkg.go.dev/github.com/dal-go/dalgo/dal#DB), then wired to [`dalgo2postgres`](https://github.com/dal-go/dalgo2postgres) (which wraps [`dalgo2sql`](https://github.com/dal-go/dalgo2sql)), to [`dalgo2firestore`](https://github.com/dal-go/dalgo2firestore), and to [`dalgo2memory`](https://github.com/dal-go/dalgo/tree/main/adapters/dalgo2memory) in tests. [Firestore in Go: CRUD and transactions with DALgo](/articles/go-firestore-tutorial/) is the Firestore adapter on its own. SQLite is a separate SQL option through [dalgo2sqlite](/adapters/dalgo2sqlite/); this page is the PostgreSQL-to-Firestore walkthrough. A read-only MongoDB option is documented on [MongoDB in Go with DALgo: the dalgo2mongodb adapter](/adapters/dalgo2mongodb/). [Repository pattern in Go with a swappable storage backend](/articles/go-repository-pattern/) puts an interface in front of the same calls. [Why use DALgo](/articles/why-use-dalgo/) and [When to use DALgo, and when not to](/articles/when-to-use-dalgo/) are the wider case and the limits. The [FAQ](/faq/) collects short answers.

Nothing below is a benchmark. There is no timing, no migration duration, and no claim about which store is faster.

## The record, written once against dal.DB

A DALgo record type names its own collection with a value-receiver `CollectionName` method. `dal.CollectionOf[string, User]()` returns a session-less handle: it holds no connection and can be a package-level variable. Reads take a `dal.ReadSession`, and a plain `dal.DB` is one. Writes take a `dal.WriteSession`. A plain `dal.DB` is not a write session, so every write below enters `RunReadwriteTransaction` and uses the transaction the adapter passes in.

```go
// Package users stores user records through DALgo, so the same functions
// can run on PostgreSQL, Cloud Firestore, or the in-memory adapter.
package users

import (
	"context"
	"fmt"
	"reflect"

	"cloud.google.com/go/firestore"
	"github.com/dal-go/dalgo/adapters/dalgo2memory"
	"github.com/dal-go/dalgo/dal"
	"github.com/dal-go/dalgo/dbschema"
	"github.com/dal-go/dalgo/ddl"
	"github.com/dal-go/dalgo2firestore"
	"github.com/dal-go/dalgo2postgres"
	"github.com/dal-go/dalgo2sql"
	"github.com/dal-go/record"
	"github.com/dal-go/record/update"
)

// User is one record in the "users" collection.
// The id is the record key, not a field of User.
// Firestore stores the exported fields as document fields: Name and Email.
// PostgreSQL maps those fields onto columns; with the default identifier
// mode the adapter lower-cases the names when it writes SQL.
type User struct {
	Name  string
	Email string
}

func (User) CollectionName() string { return "users" }

// Users is a session-less handle to the "users" collection, keyed by string ids.
var Users = dal.CollectionOf[string, User]()

// Create inserts a new user at a known id.
func Create(ctx context.Context, db dal.DB, id string, user User) error {
	return db.RunReadwriteTransaction(ctx, func(ctx context.Context, tx dal.ReadwriteTransaction) error {
		_, err := Users.InsertWithID(ctx, tx, id, user)
		return err
	})
}

// Get reads one user. A plain dal.DB is a dal.ReadSession.
func Get(ctx context.Context, db dal.DB, id string) (User, error) {
	return Users.GetData(ctx, db, id)
}

// Save writes or replaces one user at a known id.
func Save(ctx context.Context, db dal.DB, id string, user User) error {
	return db.RunReadwriteTransaction(ctx, func(ctx context.Context, tx dal.ReadwriteTransaction) error {
		return Users.SetByID(ctx, tx, id, user)
	})
}

// SetEmail changes the Email field and leaves Name alone.
func SetEmail(ctx context.Context, db dal.DB, id, email string) error {
	return db.RunReadwriteTransaction(ctx, func(ctx context.Context, tx dal.ReadwriteTransaction) error {
		return Users.UpdateByID(ctx, tx, id, []update.Update{update.ByFieldName("Email", email)})
	})
}

// Rename reads and writes in one transaction: the name changes only
// if the record is still there when the transaction commits.
func Rename(ctx context.Context, db dal.DB, id, name string) error {
	return db.RunReadwriteTransaction(ctx, func(ctx context.Context, tx dal.ReadwriteTransaction) error {
		user, err := Users.GetData(ctx, tx, id)
		if err != nil {
			return err
		}
		user.Name = name
		return Users.SetByID(ctx, tx, id, user)
	})
}

// Delete removes one user.
func Delete(ctx context.Context, db dal.DB, id string) error {
	return db.RunReadwriteTransaction(ctx, func(ctx context.Context, tx dal.ReadwriteTransaction) error {
		return Users.DeleteByID(ctx, tx, id)
	})
}

// FindByEmail returns the first user whose Email field equals email,
// together with that record's id. It uses a structured query the SQL
// and Firestore adapters both implement for equality filters.
func FindByEmail(ctx context.Context, db dal.DB, email string) (id string, user User, err error) {
	query := dal.From(dal.NewRootCollectionRef("users", "")).NewQuery().
		WhereField("Email", dal.Equal, email).
		Limit(1).
		SelectIntoRecord(func() record.Record {
			return record.NewRecordWithIncompleteKey("users", reflect.String, new(User))
		})
	records, err := dal.ExecuteQueryAndReadAllToRecords(ctx, query, db)
	if err != nil {
		return "", User{}, err
	}
	if len(records) == 0 {
		return "", User{}, fmt.Errorf("find user by email %q: %w", email, record.ErrRecordNotFound)
	}
	rec := records[0]
	id, ok := rec.Key().ID.(string)
	if !ok {
		return "", User{}, fmt.Errorf("users: unexpected key type %T", rec.Key().ID)
	}
	return id, *rec.Data().(*User), nil
}

// Missing reports a not-found read.
func Missing(err error) bool {
	return record.IsNotFound(err)
}
```

The operations that stay on `dal.DB` are:

- **Insert.** `InsertWithID` writes a new record at a known id. `Insert` without an id lets DALgo generate one.
- **Read.** `GetData` loads one record. A missing record is an error that [`record.IsNotFound`](https://pkg.go.dev/github.com/dal-go/record) recognizes; `Missing` wraps it.
- **Set.** `SetByID` creates or replaces the record at that id.
- **Update.** `UpdateByID` with `update.ByFieldName("Email", email)` changes one field and leaves the others alone. The field name is the stored name: here the exported Go field name, because `User` has no `firestore` or SQL struct tags.
- **Delete.** `DeleteByID` removes the record.
- **Query.** `FindByEmail` is a structured query: `dal.From(...).NewQuery()`, an equality filter, a limit, and `SelectIntoRecord` so each row comes back as a `record.Record` with a key. `Collection.All` returns values only, without ids, which is why this query is the form that keeps the id.
- **Transactions.** `Rename` reads and writes in one `RunReadwriteTransaction` closure. `db.RunReadonlyTransaction` is the read-only form when the callback only reads.

## Wire PostgreSQL, Firestore, and memory

The functions above never import an adapter. Constructors live next to `main` or in tests:

```go
// OpenMemory builds the in-memory adapter. The profile names the
// transaction rules the stand-in follows. FirestoreProfile follows
// Firestore's rules; SingleWriterProfile follows a single-writer store.
func OpenMemory(profile dalgo2memory.Profile) dal.DB {
	return dalgo2memory.New(profile)
}

// usersRecordsets tells the SQL adapter that the record key is the "id" column.
// Insert, Get and Delete need this metadata; NewDatabase without options is not
// enough for those point operations.
func usersRecordsets() map[string]*dalgo2sql.Recordset {
	return map[string]*dalgo2sql.Recordset{
		"users": dalgo2sql.NewRecordset("users", dalgo2sql.Table, []dal.FieldRef{dal.Field("id")}),
	}
}

// OpenPostgres opens PostgreSQL through dalgo2postgres, which wraps dalgo2sql
// and forces the postgres dialect. The caller closes the returned database.
func OpenPostgres(dsn string) (*dalgo2postgres.Database, error) {
	return dalgo2postgres.NewDatabaseWithOptions(dsn, dal.NewSchema(nil, nil), dalgo2sql.DbOptions{
		Recordsets: usersRecordsets(),
	})
}

// EnsureUsersTable creates the SQL table the repository writes.
// Memory and Firestore do not use this. PostgreSQL does, and only when
// the database implements ddl.SchemaModifier.
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

// OpenFirestore wraps an official Firestore client in a dal.DB.
// The caller closes the client. NewDatabase panics on an empty id or a nil client.
func OpenFirestore(ctx context.Context, projectID string) (dal.DB, *firestore.Client, error) {
	client, err := firestore.NewClient(ctx, projectID)
	if err != nil {
		return nil, nil, err
	}
	return dalgo2firestore.NewDatabase(projectID, client), client, nil
}
```

- `OpenMemory` uses [`dalgo2memory`](https://github.com/dal-go/dalgo/tree/main/adapters/dalgo2memory) in the core module. `New` requires a profile; there is no silent default. `FirestoreProfile()` follows [Cloud Firestore](https://cloud.google.com/firestore/docs) transaction rules. `SingleWriterProfile()` follows a single-writer store such as SQLite. If production might be either PostgreSQL or Firestore, run the same tests on both profiles; the Firestore profile is the stricter one (reads must come before writes).
- `OpenPostgres` uses [`dalgo2postgres.NewDatabaseWithOptions`](https://github.com/dal-go/dalgo2postgres). That constructor wraps [`dalgo2sql`](https://github.com/dal-go/dalgo2sql), opens the server with [`github.com/jackc/pgx/v5/stdlib`](https://pkg.go.dev/github.com/jackc/pgx/v5/stdlib) (pure Go, `CGO_ENABLED=0`), pings at construction time, and forces the `postgres` structured-query dialect so a structured query does not use the legacy text emitter. The recordset names `id` as the primary-key column. The [dalgo2postgres README](https://github.com/dal-go/dalgo2postgres) says `NewDatabase(dsn)` is the minimal constructor, and that per-collection primary-key metadata is required for `Insert`/`Get`/`Delete` with `map[string]any` data. The SQL write path also needs a primary-key column for a typed record with a known id, so this listing registers the recordset. The caller closes `*dalgo2postgres.Database`.
- `EnsureUsersTable` calls [`ddl.CreateCollection`](https://pkg.go.dev/github.com/dal-go/dalgo/ddl). The PostgreSQL driver implements `ddl.SchemaModifier`. The memory adapter and `dalgo2firestore` do not: memory has no SQL catalog, and Firestore stores the struct as a document. On a handle that is not a schema modifier, `CreateCollection` returns a not-supported error.
- `OpenFirestore` builds a client with [`cloud.google.com/go/firestore`](https://pkg.go.dev/cloud.google.com/go/firestore) and wraps it with [`dalgo2firestore.NewDatabase`](https://github.com/dal-go/dalgo2firestore). The caller closes the client. `dal.DB` has no `Close` method.

A production `main` would call `OpenPostgres` or `OpenFirestore`, optionally `EnsureUsersTable` on the SQL path, and pass the `dal.DB` to the functions above. A unit test can do the same with memory:

```go
package users

import (
	"context"
	"testing"

	"github.com/dal-go/dalgo/adapters/dalgo2memory"
	"github.com/dal-go/dalgo/dal"
)

func TestUsersRoundTrip(t *testing.T) {
	ctx := context.Background()
	want := User{Name: "Ada Lovelace", Email: "ada@example.com"}
	db := OpenMemory(dalgo2memory.FirestoreProfile())

	if _, err := Get(ctx, db, "u1"); !Missing(err) {
		t.Fatalf("Get missing user: %v", err)
	}
	if err := Create(ctx, db, "u1", want); err != nil {
		t.Fatal(err)
	}
	got, err := Get(ctx, db, "u1")
	if err != nil {
		t.Fatal(err)
	}
	if got != want {
		t.Fatalf("got %+v, want %+v", got, want)
	}
	id, found, err := FindByEmail(ctx, db, want.Email)
	if err != nil {
		t.Fatal(err)
	}
	if id != "u1" || found != want {
		t.Fatalf("FindByEmail got %s %+v", id, found)
	}
	if err := Rename(ctx, db, "u1", "Ada"); err != nil {
		t.Fatal(err)
	}
	if err := SetEmail(ctx, db, "u1", "ada@example.org"); err != nil {
		t.Fatal(err)
	}
	if err := Delete(ctx, db, "u1"); err != nil {
		t.Fatal(err)
	}
	if _, err := Get(ctx, db, "u1"); !Missing(err) {
		t.Fatalf("Get deleted user: %v", err)
	}
}

func TestOpenSignaturesCompile(t *testing.T) {
	_ = OpenPostgres
	_ = OpenFirestore
	_ = EnsureUsersTable
	var _ dal.DB = OpenMemory(dalgo2memory.SingleWriterProfile())
}
```

`go test` on 23 November 2026 ran this package against `github.com/dal-go/dalgo` v0.102.6, `dalgo2sql` v0.32.6, `dalgo2postgres` v0.11.6, `dalgo2firestore` v0.11.3, `record` v0.1.5, and `cloud.google.com/go/firestore` v1.29.2, using Go 1.27.3. The test passed for `FirestoreProfile` and for `SingleWriterProfile`. `OpenPostgres` and `OpenFirestore` were compiled in the same package. This check did not open a PostgreSQL server or a Firestore project, so it is evidence that those constructors type-check and that the shared functions run on the adapters the test actually opened. Adapter limits still live in each adapter README and in the [adapter matrix](/adapters/).

## What stays the same

Across the adapters this page names, the business functions keep the same shape:

- The record type, the collection name, and the string id stay on `dal.CollectionOf`. The id is the key, not a field of `User`.
- Point [CRUD](https://en.wikipedia.org/wiki/Create,_read,_update_and_delete) uses `InsertWithID`, `GetData`, `SetByID`, `UpdateByID`, and `DeleteByID`.
- Writes run inside `RunReadwriteTransaction`. Reads can use a plain `dal.DB` or a transaction session.
- A missing record is `record.IsNotFound`.
- Structured queries use the same builder (`From`, `WhereField`, `Limit`, `SelectIntoRecord`). An equality filter with a limit, as in `FindByEmail`, is in the intersection the Firestore and PostgreSQL adapters both implement for structured queries.
- Tests inject `dalgo2memory` with a profile, without changing the functions under test.

## What differs

The swap is not a complete hiding of the two stores. These differences remain, and they come from the adapter repositories and from official PostgreSQL and Firestore documentation.

**Schema and DDL versus document collections.** PostgreSQL needs a table. `EnsureUsersTable` is the DALgo form of that DDL. Firestore has no table to create: a document appears when you write it, in a collection that the path names. Google's [add-data guide](https://firebase.google.com/docs/firestore/manage-data/add-data) describes documents and collections; PostgreSQL's documentation describes [creating a table](https://www.postgresql.org/docs/current/sql-createtable.html). You still choose, in `main`, whether to run `EnsureUsersTable`.

**Identifier names.** `dalgo2postgres` defaults to `IdentifierFoldLower`: it lower-cases every name before it quotes it, which is also what its DDL stores, so `Name` and `name` are the same column on a database this package created. `WithIdentifierMode(dalgo2postgres.IdentifierExact)` writes names as spelled, inside quotes, for databases whose tables were created with mixed-case names. Firestore stores the exported Go field names as document fields unless you add `firestore` struct tags. Typed structs can still round-trip when the SQL adapter matches column names case-insensitively, but a raw map of stored names will show the folded SQL names. Do not put a field mask or an access check on a folding PostgreSQL handle unless the names it compares are folded first; the [dalgo2postgres README](https://github.com/dal-go/dalgo2postgres) states that limit.

**Hierarchical keys.** DALgo keys can be nested, which maps naturally to a Firestore path such as `users/u1/orders/o1`. `Collection.In(parent)` scopes a handle to a subcollection, and `record.NewKeyWithParentAndID` builds the key. On SQL, `dalgo2sql` does not store that path as a document path. It joins the collection names with `_` to form the recordset name, so a key `orders` under `users` addresses the recordset `orders_users`, which you must declare, with its own primary-key column. That is a different table, not a Firestore subcollection. A parent id is not, by itself, a PostgreSQL foreign key.

**Queries the adapter cannot run.** An adapter returns `dal.ErrNotSupported` for a capability it does not implement. `dalgo2firestore` returns that error for `GROUP BY` and for `HAVING`. It also refuses query sources it does not recognize, `IS NULL` on a field (a native `== null` would miss documents where the field is absent), and some comparison operators. It implements structured filters, order, limit, and offset on a collection or collection group. `dalgo2postgres` runs filtering, ordering, grouping, aggregation, and joins on the server through dalgo2sql's typed PostgreSQL compiler. A business method that needs a join or a `GROUP BY` has not been shown to run on Firestore by compiling it against `dal.DB` alone. Check the [adapter matrix](/adapters/) and the adapter README before promising that method on both backends. [Queries](/queries/) is the structured form.

**Transaction semantics.** Both adapters use a closure: you pass a function, the driver gives you a session. The sessions are not the same. `dalgo2firestore` runs `RunReadwriteTransaction` through the official client's `RunTransaction`, so Firestore's rules apply. Google's [transactions guide](https://firebase.google.com/docs/firestore/manage-data/transactions) says read operations must come before write operations, and that a transaction function might run more than once if a concurrent edit affects a document it reads. Use the `ctx` and `tx` the callback receives, keep side effects such as sending email out of the callback, and return an error to abandon the transaction without writing. `dalgo2postgres` starts a `database/sql` transaction, runs the callback once, and commits or rolls back. The SQL adapter does not retry the callback on a conflict the way Firestore's client does. PostgreSQL transaction behaviour is documented in the [PostgreSQL tutorial](https://www.postgresql.org/docs/current/tutorial-transactions.html). PostgreSQL also advertises concurrent connections (`dal.ConcurrencyAware`); that is a property of the server and the pgx pool, not of Firestore's transaction retry loop.

**What stays on the official client.** Firestore-only features such as real-time listeners stay on `*firestore.Client`, which `OpenFirestore` still returns. PostgreSQL-only features such as native SQL, views, or extensions stay on the `*sql.DB` behind the driver, not on `dal.DB`.

## When not to switch this way

Do not use this swap as a way to move a heavily relational service onto Firestore while keeping the same queries. If the domain depends on joins, on `GROUP BY`/`HAVING`, on foreign keys, on SQL views, or on statements you want to keep as SQL, the PostgreSQL adapter is the honest backend and the official Postgres client or a specialized tool such as [sqlc](https://docs.sqlc.dev/en/latest/tutorials/getting-started-postgresql.html) may be the better API. `dalgo2firestore` will not compile those query shapes into Firestore.

Do not use it when the product *is* Firestore: real-time listeners, security rules, or other features that exist only on the official client. [Firestore in Go: CRUD and transactions with DALgo](/articles/go-firestore-tutorial/) says the official client is the shorter path when the service will only ever use Firestore.

Do not assume every method you wrote against `dal.DB` on memory will run on both production adapters. Memory can run many structured queries end to end; that is not a proof that Firestore will run a join. The price of portability is to stay inside the intersection, or to handle `dal.ErrNotSupported` on purpose. [When to use DALgo, and when not to](/articles/when-to-use-dalgo/) is the longer limit list.

## Copying records through the interface

A point-by-point copy of one collection is something the current APIs can do: read records with their keys from one `dal.DB`, then `InsertWithID` them into another. `Collection.All` is not enough, because it returns values without ids. The query below keeps the key.

```go
// CopyUsers copies every users record from src to dest, keeping the same ids.
// Each record is written in its own transaction with InsertWithID.
func CopyUsers(ctx context.Context, src, dest dal.DB) error {
	query := dal.From(dal.NewRootCollectionRef("users", "")).NewQuery().
		SelectIntoRecord(func() record.Record {
			return record.NewRecordWithIncompleteKey("users", reflect.String, new(User))
		})
	records, err := dal.ExecuteQueryAndReadAllToRecords(ctx, query, src)
	if err != nil {
		return err
	}
	for _, rec := range records {
		id, ok := rec.Key().ID.(string)
		if !ok {
			return fmt.Errorf("users: unexpected key type %T", rec.Key().ID)
		}
		user := *rec.Data().(*User)
		if err := Create(ctx, dest, id, user); err != nil {
			return err
		}
	}
	return nil
}
```

The same 23 November 2026 test ran `CopyUsers` from one in-memory database to another, on both memory profiles, and then `Get` on the destination returned the original record. That is a copy of records the interface can read and write. It is not a general migrator: it does not convert types, remap hierarchical keys onto SQL tables, batch according to Firestore or PostgreSQL limits, or move a schema. Official tools exist for those jobs: Google's [export and import](https://firebase.google.com/docs/firestore/manage-data/export-import) documentation (also on [cloud.google.com](https://cloud.google.com/firestore/docs/manage-data/export-import)), and PostgreSQL's [`pg_dump`](https://www.postgresql.org/docs/current/app-pgdump.html) and [`pg_restore`](https://www.postgresql.org/docs/current/app-pgrestore.html). Use `SetByID` instead of `InsertWithID` if the destination may already hold the id.

## FAQ

### How do I switch a Go service from PostgreSQL to Firestore without rewriting business code?

Write the record functions against `dal.DB`, as the listing above does. In `main`, open `dalgo2postgres` or `dalgo2firestore`. In tests, pass `dalgo2memory` with a profile that matches the production transaction rules. Keep queries and transactions inside the intersection of the adapters you actually run, or handle `dal.ErrNotSupported`.

### Do I still need a PostgreSQL table after the switch?

Only on the PostgreSQL path. Call `EnsureUsersTable` (or your own DDL) before the first SQL write. Firestore stores documents and does not use that helper.

### Will every structured query run on both adapters?

No. Equality filters, ordering, and limits, as in `FindByEmail`, are in the shared structured-query subset this page used. `GROUP BY` and `HAVING` return `dal.ErrNotSupported` from `dalgo2firestore`. Joins run on the PostgreSQL server through `dalgo2postgres`; do not assume the same join runs on Firestore. See the [adapter matrix](/adapters/).

### Can I copy the data with DALgo?

You can copy one collection of records the interface can read and write, as `CopyUsers` does, if you also copy the ids. That is not a substitute for official export and import tools, linked in the previous section.

### Do I need DALgo to use PostgreSQL or Firestore from Go?

No. The official `database/sql` (or pgx) client and `cloud.google.com/go/firestore` are complete on their own. DALgo is useful when the same code must also run on the other store or on an in-memory stand-in.

## Sources

Public module docs, official PostgreSQL and Firestore documentation, and the listings above, checked on 23 November 2026.

- [dal-go/dalgo](https://github.com/dal-go/dalgo) v0.102.6 and [dal-go/record](https://github.com/dal-go/record) v0.1.5. License: [MIT](https://github.com/dal-go/dalgo/blob/main/LICENSE).
- [dalgo2sql](https://github.com/dal-go/dalgo2sql) v0.32.6, [dalgo2postgres](https://github.com/dal-go/dalgo2postgres) v0.11.6, [dalgo2firestore](https://github.com/dal-go/dalgo2firestore) v0.11.3.
- [`cloud.google.com/go/firestore`](https://pkg.go.dev/cloud.google.com/go/firestore) v1.29.2, [`github.com/jackc/pgx/v5`](https://pkg.go.dev/github.com/jackc/pgx/v5).
- Google: [Cloud Firestore](https://firebase.google.com/docs/firestore), [Add data](https://firebase.google.com/docs/firestore/manage-data/add-data), [Transactions and batched writes](https://firebase.google.com/docs/firestore/manage-data/transactions), [Export and import data](https://firebase.google.com/docs/firestore/manage-data/export-import), and the same topics on [cloud.google.com/firestore/docs](https://cloud.google.com/firestore/docs).
- PostgreSQL: [current documentation](https://www.postgresql.org/docs/current/), [CREATE TABLE](https://www.postgresql.org/docs/current/sql-createtable.html), [transactions](https://www.postgresql.org/docs/current/tutorial-transactions.html), [`pg_dump`](https://www.postgresql.org/docs/current/app-pgdump.html), [`pg_restore`](https://www.postgresql.org/docs/current/app-pgrestore.html).
