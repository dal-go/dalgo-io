---
title: MongoDB in Go with DALgo: the dalgo2mongodb adapter
slug: dalgo2mongodb
date: 2026-11-26
description: "Golang MongoDB with DALgo: the read-only dalgo2mongodb adapter opens a MongoDB URI in Go and runs point reads and bounded structured queries through dal.DB."
summary: dalgo2mongodb is the read-only MongoDB adapter for DALgo in Go. It opens a MongoDB database URI with the official Go driver and supports Get, GetMulti, Exists, and bounded structured queries; writes return dal.ErrNotSupported.
order: 2
schema: techarticle
repo: https://github.com/dal-go/dalgo2mongodb
matrix: mongodb
---

[DALgo](/) is an [open-source](https://github.com/dal-go/dalgo) database abstraction layer for [Go](https://go.dev/) and TypeScript; the Go module is [`github.com/dal-go/dalgo`](https://github.com/dal-go/dalgo). A DAL, short for [database abstraction layer](/articles/go-database-abstraction-layer/), is a library that sits between application code and a database so the program can store and load records without calling one vendor's client; [Wikipedia](https://en.wikipedia.org/wiki/Database_abstraction_layer) uses the same name. An adapter, or driver in this module's own wording, is the package that implements that interface for one kind of store. [MongoDB](https://www.mongodb.com/docs/manual/) is a document database that stores records as [BSON](https://www.mongodb.com/docs/manual/reference/bson-types/) documents — BSON is short for Binary JSON, MongoDB's binary encoding of JSON-like values — and is typically reached over the network with a connection [URI](https://en.wikipedia.org/wiki/Uniform_Resource_Identifier), short for uniform resource identifier. [`dalgo2mongodb`](https://github.com/dal-go/dalgo2mongodb) is the MongoDB adapter for DALgo: it opens that database with the [official MongoDB Go driver](https://www.mongodb.com/docs/drivers/go/current/) and returns a [`dal.DB`](https://pkg.go.dev/github.com/dal-go/dalgo/dal#DB) that can read records. The adapter is read-only. [CRUD](https://en.wikipedia.org/wiki/Create,_read,_update_and_delete), short for create, read, update, and delete, names the four usual record operations; this module supports the read operations `Get`, `GetMulti`, and `Exists`, plus bounded structured queries, and returns `dal.ErrNotSupported` for writes. The module on current `main` is [Apache-2.0 licensed](https://github.com/dal-go/dalgo2mongodb/blob/main/LICENSE).

This page is the reference for the Go module [`github.com/dal-go/dalgo2mongodb`](https://github.com/dal-go/dalgo2mongodb). The [adapter matrix](/adapters/) lists what the MongoDB row implements. A broader survey of Go data-access libraries is in [Go ORM and data-access libraries compared (2026)](/articles/go-orm-comparison-2026/); ORM is short for [object-relational mapping](https://en.wikipedia.org/wiki/Object%E2%80%93relational_mapping). [Repository pattern in Go](/articles/go-repository-pattern/) puts a smaller interface in front of `dal.DB`. [SQLite in Go with DALgo: the dalgo2sqlite adapter](/adapters/dalgo2sqlite/) is the SQLite adapter page. [Switching between PostgreSQL and Firestore in Go](/articles/switch-postgres-to-firestore/) is a walkthrough of the same record calls on two other stores that do support writes. The [quickstart](/quickstart/) and the [FAQ](/faq/) are the shorter product pages.

## What dalgo2mongodb is

The module README calls dalgo2mongodb a read-only MongoDB adapter for DALgo, built on the official MongoDB Go driver, [`go.mongodb.org/mongo-driver/v2`](https://pkg.go.dev/go.mongodb.org/mongo-driver/v2). The package comment says it provides bounded, read-only MongoDB structured queries. The public constructor is `dalgo2mongodb.NewDB(ctx, uri)`. It returns a `dal.DB`. Close that value through `io.Closer` when the work is finished.

The facts on this page were checked against current `main` of [dal-go/dalgo2mongodb](https://github.com/dal-go/dalgo2mongodb), commit `08ff6460d3498f5b307acdb86c6e35a2b6933a3e`, which depends on [dalgo v0.102.6](https://github.com/dal-go/dalgo/tree/v0.102.6), [record v0.1.5](https://github.com/dal-go/record), and [go.mongodb.org/mongo-driver/v2 v2.10.1](https://pkg.go.dev/go.mongodb.org/mongo-driver/v2@v2.10.1). The latest Git tag is [v0.1.0](https://github.com/dal-go/dalgo2mongodb/tree/v0.1.0) (commit `1c6549d8dc1e43878501ebe69f7c461615ce9773`, 27 October 2026). `Adapter()` still reports the version string `"0.1.0"` on current `main`. The public constructor, the read methods, and the query surface described below are the same on the tag and on `main`. A short read program using `NewDB`, `Get`, `Exists`, and `ExecuteQueryToRecordsReader` compiled against both the tag and that `main` commit on 26 November 2026. `NewDB` pings the server, so that program was not executed against a live MongoDB instance.

## What it supports, and what it does not

These operations are supported:

- `Get`, `GetMulti`, and `Exists` — point reads of a document by key in one root collection
- `ExecuteQueryToRecordsReader` — a bounded structured query that returns a `dal.RecordsReader`
- `RunReadonlyTransaction` — the callback runs as ordinary reads on the same handle; the README states that this does not provide snapshot isolation across calls

These operations are not provided:

- Writes: the README states that writes return `dal.ErrNotSupported`. `RunReadwriteTransaction` returns `dal.ErrNotSupported` with the message that the MongoDB adapter is read-only.
- `ExecuteQueryToRecordsetReader` returns `dal.ErrNotSupported`. Use `ExecuteQueryToRecordsReader`.
- Schema discovery: `Schema()` returns `nil`.

`Get` requires a root collection (no parent key), a collection name the adapter accepts, and a non-nil, comparable document ID. Collection names must be non-empty, at most 120 characters, and must not contain `.`, `$`, or a NUL byte. Queried record keys and `Get`/`Exists` preserve native comparable BSON scalar IDs, including ObjectID and numbers, even when a projection omits `_id`. Null IDs and non-comparable IDs, such as embedded documents and binary slices, are unsupported. A string ID is different from an ObjectID.

## Install and constructor

```text
go get github.com/dal-go/dalgo2mongodb
```

`NewDB(ctx, uri)` opens the database named in `uri`, pings the server so a bad URI or failed authentication fails at construction time, and returns a `dal.DB`. The URI must select a database: `mongodb://host/database` or `mongodb+srv://host/database`. Official [MongoDB connection string](https://www.mongodb.com/docs/manual/reference/connection-string/) documentation describes those URI forms. The constructor rejects a URI that does not use one of those schemes, has an empty host, includes a fragment, or does not name exactly one database in the path.

The README says to use a dedicated MongoDB account with the [`read` role](https://www.mongodb.com/docs/manual/reference/built-in-roles/#mongodb-authrole-read) for that database, and to keep credentials in environment variables or a secret store. TLS and authentication options are handled by the official driver. The adapter does not return driver error messages that may contain credentials. Default driver timeouts on this constructor are 10 seconds for server selection and 30 seconds for an operation. On current `main`, caller cancellation and deadlines return the standard `context.Canceled` or `context.DeadlineExceeded` sentinels; other driver failures use fixed redacted messages.

Close the handle when finished. The value returned by `NewDB` implements `io.Closer`; `Close` disconnects the official driver client.

## Structured queries

Queries run with `db.ExecuteQueryToRecordsReader`. Supported queries use one root collection, top-level fields, scalar `==`, `<`, `<=`, `>`, `>=` comparisons, AND/OR groups, field projection, ordering, offset (up to 100000), and a positive limit (at most 1000, the package constant `MaxResults`). An omitted limit defaults to 1000. Results are additionally bounded to 16 MiB of BSON. MongoDB comparison, missing-field, and null semantics apply. `_id` is returned unless a projection omits it.

Computed expressions, aliases, qualified or nested fields, joins, grouping, cursors, raw commands, and aggregation pipelines are rejected. No query can submit `$where`, `$out`, or `$merge`. Those refusals return an error wrapping `dal.ErrNotSupported`.

## A short read example

The listing below opens MongoDB through `NewDB`, reads one document with `Get`, and runs a structured query with `WhereField`, `OrderBy`, and `Limit`. It compiled against dalgo2mongodb commit `08ff6460d3498f5b307acdb86c6e35a2b6933a3e` and against tag v0.1.0 on 26 November 2026. It was not executed against a live server, because `NewDB` pings MongoDB at construction time.

```go
package store

import (
	"context"
	"errors"
	"io"

	"github.com/dal-go/dalgo/dal"
	"github.com/dal-go/dalgo2mongodb"
	"github.com/dal-go/record"
)

func ReadProducts(ctx context.Context, uri string) error {
	db, err := dalgo2mongodb.NewDB(ctx, uri)
	if err != nil {
		return err
	}
	if closer, ok := db.(io.Closer); ok {
		defer closer.Close()
	}

	loaded := record.NewRecordWithData(record.NewKeyWithID("products", "sku-1"), map[string]any{})
	if err := db.Get(ctx, loaded); err != nil && !errors.Is(err, record.ErrRecordNotFound) {
		return err
	}

	q := dal.From(dal.NewRootCollectionRef("products", "")).NewQuery().
		WhereField("price", dal.GreaterOrEqual, 10).
		OrderBy(dal.DescendingField("price")).
		Limit(20).
		SelectIntoRecord(nil)
	reader, err := db.ExecuteQueryToRecordsReader(ctx, q)
	if err != nil {
		return err
	}
	defer reader.Close()
	for {
		rec, err := reader.Next()
		if errors.Is(err, dal.ErrNoMoreRecords) {
			break
		}
		if err != nil {
			return err
		}
		_ = rec.Data()
	}
	return nil
}
```

`Get` and `Exists` take a `dal.DB` directly, because that handle is a read session. There is no write path on this adapter: `RunReadwriteTransaction` returns `dal.ErrNotSupported`.

## When to choose MongoDB

Choose dalgo2mongodb when the data already lives in [MongoDB](https://www.mongodb.com/docs/manual/) and the Go code needs to read it through `dal.DB` — point reads and the bounded structured queries above — with the official Go driver. The same `Get`, `Exists`, `GetMulti`, and `ExecuteQueryToRecordsReader` calls can run against this adapter. Writes need a different store; this module will not insert, update, or delete.

Choose [dalgo2sqlite](/adapters/dalgo2sqlite/) when the database should live in-process as a SQLite file or an in-memory SQL engine, including when you need writes, schema, and DDL. Choose [dalgo2postgres](https://github.com/dal-go/dalgo2postgres) when the service needs a networked PostgreSQL server and SQL writes. [Switching between PostgreSQL and Firestore in Go](/articles/switch-postgres-to-firestore/) shows that constructor and what still differs when the same records move to Firestore. Choose [dalgo2firestore](https://github.com/dal-go/dalgo2firestore) when the product is a Cloud Firestore document store; [Firestore in Go: CRUD and transactions with DALgo](/articles/go-firestore-tutorial/) is that walkthrough.

DALgo does not hide every engine difference. The limits above are part of this adapter, not a generic MongoDB client. [When to use DALgo, and when not to](/articles/when-to-use-dalgo/) is the wider limit list.

## Capability summary

The [adapter matrix](/adapters/#adapter-mongodb) is the inventory. For the Go module it lists these capabilities as implemented: point-read, structured-query, and cancellation. It lists write, transactions, and schema discovery as not implemented, with the limit "Bounded root collection/top-level scalar filters, projection and order. No writes, joins, grouping, cursors, native commands or recordset reader." This page does not add capabilities to that row. The same matrix has a TypeScript row for a different package, `@dalgo/dalgo2mongodb`; that is not this Go module.

## FAQ

### What is dalgo2mongodb?

dalgo2mongodb is the read-only MongoDB adapter for DALgo in Go. It opens a MongoDB database URI with the official MongoDB Go driver and returns a `dal.DB` that supports `Get`, `GetMulti`, `Exists`, and bounded structured queries. The module is [`github.com/dal-go/dalgo2mongodb`](https://github.com/dal-go/dalgo2mongodb).

### Can dalgo2mongodb insert, update, or delete documents?

No. The adapter is read-only. The README states that writes return `dal.ErrNotSupported`. `RunReadwriteTransaction` returns that error and states that the MongoDB adapter is read-only. `ExecuteQueryToRecordsetReader` is also unsupported; use `ExecuteQueryToRecordsReader`.

### How do I open a MongoDB database with DALgo?

Call `dalgo2mongodb.NewDB(ctx, uri)`. The URI must select a database, as `mongodb://host/database` or `mongodb+srv://host/database`. The constructor pings the server. Close the returned handle through `io.Closer`. The README recommends a dedicated MongoDB account with the `read` role for that database.

### When should I use this adapter instead of SQLite, PostgreSQL, or Firestore?

Use dalgo2mongodb when you need to read an existing MongoDB database through `dal.DB`. Use [dalgo2sqlite](/adapters/dalgo2sqlite/) for an in-process SQLite file or memory database, including writes and schema. Use dalgo2postgres for a PostgreSQL server, and dalgo2firestore when the product is Cloud Firestore. Write operations belong on those other adapters, not on this one.

## Sources

Public module documentation and source, checked on 26 November 2026.

- [dal-go/dalgo2mongodb](https://github.com/dal-go/dalgo2mongodb) current `main` commit `08ff6460d3498f5b307acdb86c6e35a2b6933a3e`, and latest tag [v0.1.0](https://github.com/dal-go/dalgo2mongodb/tree/v0.1.0) (commit `1c6549d8dc1e43878501ebe69f7c461615ce9773`). Public APIs cited: `NewDB`, `Get`, `GetMulti`, `Exists`, `ExecuteQueryToRecordsReader`, `ExecuteQueryToRecordsetReader`, `RunReadonlyTransaction`, `RunReadwriteTransaction`, `Schema`, and `Close`. License on current `main`: [Apache License 2.0](https://github.com/dal-go/dalgo2mongodb/blob/main/LICENSE). The v0.1.0 tag does not include that LICENSE file; the license was added on `main` after the tag.
- [dal-go/dalgo](https://github.com/dal-go/dalgo) v0.102.6 (the version current `main` requires; tag v0.1.0 requires v0.95.3), [dal-go/record](https://github.com/dal-go/record) v0.1.5. DALgo license: [MIT](https://github.com/dal-go/dalgo/blob/main/LICENSE).
- [go.mongodb.org/mongo-driver/v2](https://pkg.go.dev/go.mongodb.org/mongo-driver/v2@v2.10.1) v2.10.1, the official driver current `main` imports (tag v0.1.0 imports v2.4.4). Driver documentation: [MongoDB Go driver](https://www.mongodb.com/docs/drivers/go/current/) and the [mongo-go-driver](https://github.com/mongodb/mongo-go-driver) repository.
- [MongoDB documentation](https://www.mongodb.com/docs/manual/), including [connection strings](https://www.mongodb.com/docs/manual/reference/connection-string/) and [BSON types](https://www.mongodb.com/docs/manual/reference/bson-types/).
- [Adapter matrix](/adapters/) MongoDB row.
