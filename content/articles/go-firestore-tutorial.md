---
title: Firestore in Go: CRUD and transactions with DALgo
slug: go-firestore-tutorial
date: 2026-11-16
description: Golang Firestore tutorial: Firestore Go CRUD and Firestore transactions in Go with DALgo, tested on the Firestore emulator and an in-memory stand-in.
summary: Connect to Cloud Firestore from Go through DALgo's dalgo2firestore adapter, then create, read, update and delete a document and run a read-write transaction. The same functions run on an in-memory adapter in unit tests.
order: 1
schema: techarticle
---

[Cloud Firestore](https://firebase.google.com/docs/firestore) is Google's document database: it stores documents, each a set of named fields, in collections. [Go](https://go.dev/) is the programming language this page uses. An SDK (software development kit) is the library a vendor ships for its service; for Firestore in Go that is the official client, [`cloud.google.com/go/firestore`](https://pkg.go.dev/cloud.google.com/go/firestore). [DALgo](/) is an [open-source](https://github.com/dal-go/dalgo) database abstraction layer (DAL) for Go: a library that sits between application code and a database, so the program loads and stores records without calling one vendor's client. [Database abstraction layer in Go](/articles/go-database-abstraction-layer/) is the longer definition. An adapter is the DALgo module that speaks to one backend; the Firestore adapter is [`dalgo2firestore`](https://github.com/dal-go/dalgo2firestore). [CRUD](https://en.wikipedia.org/wiki/Create,_read,_update_and_delete) is short for create, read, update and delete, the four record operations. A transaction is a group of reads and writes that commits together or not at all.

This is a golang Firestore tutorial for one small `tasks` collection: open Firestore, then create, read, update and delete a task, and change it inside a read-write transaction. Every listing below ran against the [Firestore emulator](https://firebase.google.com/docs/emulator-suite/connect_firestore) and against DALgo's in-memory adapter on 16 November 2026. The [repository pattern article](/articles/go-repository-pattern/) puts an interface in front of the same calls, [DALgo vs GORM](/articles/dalgo-vs-gorm/) compares DALgo with an ORM, and the [adapters page](/adapters/) lists what each backend supports.

## Install the modules

```bash
go get github.com/dal-go/dalgo github.com/dal-go/dalgo2firestore github.com/dal-go/record cloud.google.com/go/firestore
```

The listings were tested with `github.com/dal-go/dalgo` v0.102.4, `dalgo2firestore` v0.11.2, `record` v0.1.5 and `cloud.google.com/go/firestore` v1.29.2. DALgo is still on a v0 module path, so pin the versions you have run.

## The record, the collection and the connection

A DALgo record type names its own collection with a value-receiver `CollectionName` method. `dal.CollectionOf[string, Task]()` returns a session-less handle: it holds no connection and can be a package-level variable. `dalgo2firestore.NewDatabase` wraps an official `*firestore.Client` in a `dal.DB`, so authentication, project selection and the emulator switch stay the official client's job.

```go
// Package tasks stores to-do tasks in Firestore through DALgo.
package tasks

import (
	"context"
	"errors"

	"cloud.google.com/go/firestore"
	"github.com/dal-go/dalgo/dal"
	"github.com/dal-go/dalgo2firestore"
	"github.com/dal-go/record"
	"github.com/dal-go/record/update"
)

// Task is one document in the "tasks" collection.
// Firestore stores the exported fields as document fields: Title and Done.
// The document id is the record key, not a field of Task.
type Task struct {
	Title string
	Done  bool
}

func (Task) CollectionName() string { return "tasks" }

// Tasks is a session-less handle to the "tasks" collection, keyed by string ids.
var Tasks = dal.CollectionOf[string, Task]()

// OpenFirestore wraps an official Firestore client in a dal.DB.
// The caller closes the client. NewDatabase panics on an empty id or a nil client.
func OpenFirestore(ctx context.Context, projectID string) (dal.DB, *firestore.Client, error) {
	client, err := firestore.NewClient(ctx, projectID)
	if err != nil {
		return nil, nil, err
	}
	return dalgo2firestore.NewDatabase(projectID, client), client, nil
}

// Create inserts a new task. Writes need a dal.WriteSession,
// so they run inside a read-write transaction.
func Create(ctx context.Context, db dal.DB, id string, task Task) error {
	return db.RunReadwriteTransaction(ctx, func(ctx context.Context, tx dal.ReadwriteTransaction) error {
		_, err := Tasks.InsertWithID(ctx, tx, id, task)
		return err
	})
}

// Get reads one task. A plain dal.DB is a dal.ReadSession.
func Get(ctx context.Context, db dal.DB, id string) (Task, error) {
	return Tasks.GetData(ctx, db, id)
}

// Complete sets Done to true without rewriting the rest of the document.
func Complete(ctx context.Context, db dal.DB, id string) error {
	return db.RunReadwriteTransaction(ctx, func(ctx context.Context, tx dal.ReadwriteTransaction) error {
		return Tasks.UpdateByID(ctx, tx, id, []update.Update{update.ByFieldName("Done", true)})
	})
}

// Delete removes one task.
func Delete(ctx context.Context, db dal.DB, id string) error {
	return db.RunReadwriteTransaction(ctx, func(ctx context.Context, tx dal.ReadwriteTransaction) error {
		return Tasks.DeleteByID(ctx, tx, id)
	})
}

// ErrAlreadyDone is returned by Rename for a completed task.
var ErrAlreadyDone = errors.New("task is already done")

// Rename reads and writes in one transaction: the title changes only
// if the task is still open when the transaction commits.
// Firestore requires every read in a transaction to come before its writes.
func Rename(ctx context.Context, db dal.DB, id, title string) error {
	return db.RunReadwriteTransaction(ctx, func(ctx context.Context, tx dal.ReadwriteTransaction) error {
		task, err := Tasks.GetData(ctx, tx, id)
		if err != nil {
			return err
		}
		if task.Done {
			return ErrAlreadyDone
		}
		task.Title = title
		return Tasks.SetByID(ctx, tx, id, task)
	})
}

// Missing reports a not-found read.
func Missing(err error) bool {
	return record.IsNotFound(err)
}
```

## Firestore Go CRUD, one function per operation

- **Create.** `InsertWithID` writes a new document at a known id. On the emulator, a second insert at the same id failed with Firestore's `AlreadyExists` error. Use `Insert` without an id to let DALgo generate one, or `SetByID` to create-or-replace.
- **Read.** `GetData` takes a `dal.ReadSession`, and a plain `dal.DB` is one. A missing document comes back as an error that [`record.IsNotFound`](https://pkg.go.dev/github.com/dal-go/record) recognizes; `Missing` wraps it.
- **Update.** `UpdateByID` with `update.ByFieldName("Done", true)` changes one field and leaves the others alone. `dalgo2firestore` passes the field name to Firestore as the update path, so it must be the stored field name: here the Go field name, because `Task` has no `firestore` struct tags.
- **Delete.** `DeleteByID` removes the document.

Writes take a `dal.WriteSession`. A plain `dal.DB` is not one, so calling `SetByID` or `DeleteByID` with it is a compile error. Every write above runs inside `RunReadwriteTransaction`, which is where a `dal.ReadwriteTransaction` comes from.

## Firestore transactions in Go

`Rename` is the transaction: it reads the task, refuses to rename a finished one, and writes the new title, all in one read-write transaction. `dalgo2firestore` runs `RunReadwriteTransaction` through the official client's `RunTransaction`, so Firestore's rules apply unchanged. Google's [transactions guide](https://firebase.google.com/docs/firestore/manage-data/transactions) says read operations must come before write operations, and that a transaction function might run more than once if a concurrent edit affects a document it reads. The [Go client reference](https://pkg.go.dev/cloud.google.com/go/firestore#Client.RunTransaction) says `RunTransaction` retries the function when the commit fails because of a conflicting transaction. So:

- Do every `GetData` before the first write in the callback.
- Use the `ctx` and `tx` the callback receives, not the outer ones.
- Keep side effects such as sending email out of the callback, because it can run again.
- Return an error, like `ErrAlreadyDone`, to abandon the transaction without writing.

`db.RunReadonlyTransaction` is the read-only form when the callback only reads.

## Test the same code without Firestore

The functions take a `dal.DB`, not a `*firestore.Client`, so a unit test can hand them DALgo's in-memory adapter. `dalgo2memory.FirestoreProfile()` makes that stand-in follow Firestore's transaction rules; it is part of the core module, so the test needs no emulator, network or credentials.

```go
package tasks

import (
	"context"
	"errors"
	"testing"

	"github.com/dal-go/dalgo/adapters/dalgo2memory"
)

func TestTasksOnFirestoreProfile(t *testing.T) {
	ctx := context.Background()
	// The in-memory adapter with Firestore's transaction rules stands in for Firestore.
	db := dalgo2memory.New(dalgo2memory.FirestoreProfile())

	if err := Create(ctx, db, "t1", Task{Title: "Write the tutorial"}); err != nil {
		t.Fatal(err)
	}
	if err := Rename(ctx, db, "t1", "Publish the tutorial"); err != nil {
		t.Fatal(err)
	}
	if err := Complete(ctx, db, "t1"); err != nil {
		t.Fatal(err)
	}
	got, err := Get(ctx, db, "t1")
	if err != nil {
		t.Fatal(err)
	}
	if got != (Task{Title: "Publish the tutorial", Done: true}) {
		t.Fatalf("got %+v", got)
	}
	if err := Rename(ctx, db, "t1", "Too late"); !errors.Is(err, ErrAlreadyDone) {
		t.Fatalf("Rename done task: %v", err)
	}
	if err := Delete(ctx, db, "t1"); err != nil {
		t.Fatal(err)
	}
	if _, err := Get(ctx, db, "t1"); !Missing(err) {
		t.Fatalf("Get deleted task: %v", err)
	}
}
```

`go test` passed this test on 16 November 2026. A second test, run with `FIRESTORE_EMULATOR_HOST` set, ran the same steps through `OpenFirestore` against the Firestore emulator from `firebase-tools` 15.36.0 (`cloud-firestore-emulator` v1.22.0) and also passed; it skips when the variable is unset. The official client switches to the emulator when that variable is set. The same functions also accept the [SQL adapters](/adapters/), with the setup the [abstraction-layer article](/articles/go-database-abstraction-layer/) shows.

## DALgo or the official Firestore client directly

The official client is the shorter path when the service will only ever use Firestore. Google's [add-data guide](https://firebase.google.com/docs/firestore/manage-data/add-data) writes with `client.Collection("cities").Doc("LA").Set(ctx, data)`, reads with `Doc(...).Get(ctx)` and `DataTo`, updates fields with a `[]firestore.Update`, and deletes with `Doc(...).Delete(ctx)`. `client.RunTransaction` is the transaction. Everything Firestore-specific, such as real-time listeners, is available there first.

DALgo earns its place when the code that reads and writes tasks should not depend on Firestore: unit tests on the in-memory adapter, a second deployment on SQL, or one data-access style across several stores. The cost is a second layer and its limits. An adapter returns `dal.ErrNotSupported` for a capability its backend cannot provide, and Firestore-only features stay on the official client, which `OpenFirestore` still returns. [Why use DALgo](/articles/why-use-dalgo/) and [When to use DALgo, and when not to](/articles/when-to-use-dalgo/) cover that trade-off.

## FAQ

### How do I connect to Firestore from Go?

Create an official client with `firestore.NewClient(ctx, projectID)`. To use it through DALgo, wrap it with `dalgo2firestore.NewDatabase(projectID, client)` and pass the resulting `dal.DB` to your functions. Close the client when the program exits.

### Can I run Firestore transactions in Go with DALgo?

Yes. `db.RunReadwriteTransaction` runs the callback through Firestore's `RunTransaction`, so reads must come before writes and the callback can be retried on contention. `db.RunReadonlyTransaction` is the read-only form.

### How do I test Firestore Go code without Firestore?

Pass `dalgo2memory.New(dalgo2memory.FirestoreProfile())` to the same functions in unit tests. For a check against Firestore itself, run the Firestore emulator and set `FIRESTORE_EMULATOR_HOST`.

### Do I need DALgo to use Firestore from Go?

No. The official `cloud.google.com/go/firestore` client is complete on its own. DALgo is useful when the same code must also run on another store or on an in-memory stand-in.

## Sources

Public module docs, Google's documentation, and the listings above, checked on 16 November 2026.

- [dal-go/dalgo](https://github.com/dal-go/dalgo) v0.102.4, [dalgo2firestore](https://github.com/dal-go/dalgo2firestore) v0.11.2 and [dal-go/record](https://github.com/dal-go/record) v0.1.5. License: [MIT](https://github.com/dal-go/dalgo/blob/main/LICENSE).
- [`cloud.google.com/go/firestore`](https://pkg.go.dev/cloud.google.com/go/firestore) v1.29.2.
- Google: [Add data to Cloud Firestore](https://firebase.google.com/docs/firestore/manage-data/add-data), [Transactions and batched writes](https://firebase.google.com/docs/firestore/manage-data/transactions), [Connect your app to the Cloud Firestore Emulator](https://firebase.google.com/docs/emulator-suite/connect_firestore).
