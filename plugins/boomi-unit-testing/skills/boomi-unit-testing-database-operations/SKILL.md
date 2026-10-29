---
name: boomi-unit-testing-database-operations
description: Use when a Boomi process or subprocess under unit test reads or writes a database with the Database Legacy or Database V2 connector (SQL queries, inserts, updates, deletes, stored procedures, SQL lookups) and the database must be mocked with mockjdbc, when a [UT] test must check the DB writes of the process, or when a technical database failure (an SQLException, a lost connection) must be simulated.
---

# Mocking database operations in Boomi unit tests (mockjdbc)

## What this skill does: mock the JDBC layer

The `[S]` under test keeps its database operations exactly as they are: same connector, same operations, same SQL.
What changes in the test is **only the JDBC driver under the connection**: the test switches it, through
**extensions** of the connection, to **mockjdbc** (https://github.com/SimoneAvogadro/mockjdbc). mockjdbc answers the
queries with CSV data taken from Dynamic Process Properties and records the parameters of every INSERT, UPDATE,
DELETE and stored procedure call in other Dynamic Process Properties. The connector, its SQL and its parameter
binding are exercised for real; only the database behind them is fake.

The extensions to set (on the database connection the `[S]` uses, in the `[UT]` test run only):

| Connection field (extension) | Database (Legacy) | Database V2 (`GenericConnectionConfig`) | Test value |
|---|---|---|---|
| Driver Type | yes | (no such field) | `Custom` (value `custom` through `boomi-extensions.sh`) |
| Class Name | yes | `className` | `me.avogadro.mockjdbc.MockJdbcDriver` |
| Connection URL | yes | `url` | `any` |

With the Legacy connector extend **all three**, also when the connection already uses `Custom`: only the `Custom`
driver type uses the Class Name, so a connection with a predefined type (SQL Server, Oracle, ...) would ignore the
mockjdbc class and reach the real driver, and a `[UT]` without the Driver Type extension breaks the day the connection
changes type. User name and password stay those of the real connection: mockjdbc ignores them. The
`ConnectionOverride` blocks to copy into the `[UT]` (Legacy with `xpath`, Database V2 without) are in
[mockjdbc-reference.md](mockjdbc-reference.md#extension-declarations).

**Database V2 with connection pooling**: with pooling on, test-on-borrow and no validation query, the pool asks
mockjdbc `isValid()`, which answers false, and no connection can be borrowed ("isValid() returned false"). When the
connection has pooling on, also extend `enablePooling` = `false`, or `validationQuery` = `SELECT 1` (found by reading
the connector code: verify on the first run).

**REQUIRED:** `boomi-unit-testing` for the strategy this skill plugs into: the `[UT]` process, the question before any
change to the `[S]`, how extensions are declared, set and checked, the unit-test environment and the cleanup.
This skill gives the database part of the test; the rest of the `[UT]` is built as that skill says.

Priority: Boomi Companion < these skills < project or customer skills (see `boomi-unit-testing`, "Which skill wins").

The rules below are those of mockjdbc **2.2.0**, plus the error resources of **2.3.0** (beta jars from `2.3.0-b1`),
with the Legacy connector 20.03.0 and Database V2 0.0.73 (effective version 64). The connector behaviour under the mock
comes from static analysis of those connector versions (2026-10-23): recheck it when the connector changes
([mockjdbc-reference.md](mockjdbc-reference.md#connector-behaviour-under-the-mock)). What is marked "observed" comes
from runs on a Boomi Atom with mockjdbc 2.3.0-b1.

## Prerequisite: the mockjdbc Custom Library

Before the first test on an environment, check (Companion scripts) that

- `boomi-component-search.sh --type customlibrary` + `boomi-component-pull.sh` finds a library with
  `<Type>connector</Type>`, the `<connectorType>` of the `[S]`'s connection (`database` = Database Legacy,
  `officialboomi-X3979C-dbv2da-prod` = Database V2) and `Files` `mockjdbc-*.jar`, `opencsv-*.jar`, `aspectjrt-*.jar`,
  with `mockjdbc-2.2.0.jar` or later (an older jar: ask the user to upgrade the library); the failure `[UT]`s need
  error resources: `mockjdbc-2.3.0.jar` or later, or a beta jar from `2.3.0-b1`;
- it is deployed on the unit-test environment: `POST DeployedPackage/query` with `environmentId`, `componentId` of
  the library, `active` = `true` (the lookup of `boomi-undeploy.sh --by-component`; no read-only script).

No such library: tell the user, together with the other prerequisite questions, that uploading the jars and creating
the library are manual (Boomi has no API to upload jars), and point to
https://github.com/SimoneAvogadro/mockjdbc/blob/master/FEATURES.md#setting-up-the-custom-library; never upload jars or
create the library yourself. Meanwhile go on with everything that does not run a test: the inventory, the review of
the SQL, the QUERY_ID policy, building and pushing the `[UT]`s with their extension declarations. Only deploying and
running the `[UT]`s wait for the user's confirmation; after it, check again. Library found but not deployed there: `boomi-deploy.sh <pulled library XML>` (to the unit-test environment),
then go on; it is part of the cleanup of `boomi-unit-testing`.

**An older jar** is a request to the user (upgrade the library: manual, from the GUI), not a stop. Until the upgrade,
go on with what the old jar does, and confirm each feature you rely on with a first run. Release 2.1.0, from the
mockjdbc CHANGELOG: writes are captured only on table names made of letters (`crm_customers` is not named: step key 4
or a QUERY_ID), the table of a SELECT is the word after the **last** `from`, quoted and schema-qualified names are not
recognised, `prepareCall` returns `null` (no stored procedures); `-- QUERY_ID:` works. The final answer gives the jar
version and lists the `[UT]`s made order-dependent by it, to review after the upgrade. A jar without error resources
reads their CSV as plain data: nothing is thrown and `mockjdbc_<name>_error` stays empty (see "Failure paths").

**The library is not what the runtime runs.** After an upgrade of the library the runtime can keep loading the old
jar (jar locking: the old file stays in `userlib` and on the classpath until the runtime is stopped and the file
removed). Suspect it when the driver behaves like an older version: a schema-qualified write not captured under
`mockjdbc_<schema>.<table>_params`, a "Stored Procedure" operation failing in `prepareCall`, a `-- QUERY_ID:` ignored,
an error resource that throws nothing.
Then check it (a temporary Notify that logs the expected `_params` key and its neighbours, or an existing test of
that feature run on the same runtime) and **ask the user how to go on**. On a local Atom the user can stop it, delete
the old jars and start it again. **Cloud runtimes and Atoms cannot be restarted and their jars cannot be deleted**:
there the choice is another runtime, or keys that work with the behaviour the runtime has (a QUERY_ID; a step key, key 4).

## Inventory of the database operations

Before writing the `[UT]`, list every database operation that the `[S]` runs, and those of the subprocesses it calls:
Database Legacy (`<sql>` of the `profile.db`, or dynamic insert/update/delete) and Database V2 (SQL operations, or
operations built from a table). For each one record: the step, the connector (Legacy or V2), the table or procedure,
the kind (SELECT, INSERT, UPDATE, DELETE, stored procedure), whether the process defines its SQL text, and whether
that SQL starts with `-- QUERY_ID:` or `-- TESTCASE:` (both count as an ID).

- **Already has an ID**: the test uses the ID keys (`mockjdbc_<id>`, `mockjdbc_<id>_params`), whatever the policy.
- **SQL generated by the connector** (Legacy dynamic insert/update/delete; Database V2 Dynamic Insert and Dynamic
  Get, whose `query` field is empty): there is no text to put the comment in. Choose the mock key directly (below),
  whatever the policy. With mockjdbc, Database V2 generates plain SQL such as
  `Insert into payments(pay_id,amount) values (?,?)`: no schema, even with `schemaName` set, and no quotes, so the
  table-name key works. Database V2 Standard Get/Insert/Update/Delete and Update Commit By Rows keep their SQL in the
  operation: the policy applies to them.
- **Every other operation**: follow the QUERY_ID policy.

Also note the connection of each operation: a connection shared with other projects (for example in a `#common`
folder) is more likely to be deployed in other processes of the unit-test environment, and a QUERY_ID on an operation
shared with them changes their SQL too.

**What the mock cannot see.** mockjdbc does not run the SQL: it returns the mock rows whatever the statement says,
and captures only the bound parameters. Literals (`status = 'PAID'`), WHERE logic, joins, aggregates, ORDER BY and
column lists are never checked by a test. So, during the inventory, **read every SQL against the spec of the `[S]`**:
a mismatch is a defect "found by review" (`boomi-unit-testing`, "When the `[S]` must change"), recorded with the SQL
line and the sentence of the spec it breaks. How much this review weighs depends on the situation
(`boomi-unit-testing`, "Scope"):

- **before the first DEV run**: the review is the only check of the SQL before DEV. Its findings go to the defect
  list as "found by review", and the final answer lists what DEV must still verify (SQL text and semantics, real
  types, constraints);
- **after DEV**: a lighter review, since the SQL already ran against the real database.

SQL validation (syntax, semantics against the real database) belongs to the DEV phase, not to the mock.

Read the **order of the writes** too: when the spec puts two writes in sequence ("insert the refund, then update the
order") and the `[S]` runs them in separate Branch paths, what the second write does after a failure of the first
depends on the kind of failure:

- a **document error** (Legacy, or any failed document) makes Boomi skip every later path of that Branch, **for all
  documents**, with or without a Try/Catch in the caller (observed with 2.3.0-b1, on Legacy Send errors and on a Set
  Properties error). In a multi-document `[S]` one failing document also loses the later-path writes of the good ones
  (seen: one failed reminder INSERT skipped the reminder-count UPDATE of all 3 invoices);
- an error that is an **output document** (Database V2 with `returnApplicationErrors="true"`) lets the later paths
  run: the second write runs although the first failed.

Fail the first write with an error resource (below) and check the second: with Legacy its `_params` stays empty (also
for the good documents), with Database V2 error documents it is captured. A `[UT]` that stays red for what the spec says
is a defect: the good documents must still be processed, or the second write must depend on the first. With an older
jar no test sees it: a defect "found by review" when the spec makes the second write depend on the first, otherwise a
check for DEV in the final answer.

**Failure paths of the database operations.** In the inventory, also list the technical failures the `[S]` handles
around its database steps: a Try/Catch around a database step, an error route, a check of the connector's error
output. Application failures that depend on the data are deterministic and are covered as usual: for example a
header-only mock (no rows) for a "not found" that the `[S]` turns into an Exception. Technical failures are caused
with an **error resource**, available from mockjdbc 2.3.0 (beta jars from `2.3.0-b1`). With an older jar they stay a
**coverage gap**, reported in the final answer ("technical failure paths not testable with the current mockjdbc"): do
not invent a mechanism.

An **error resource** is a mock whose CSV header starts with the simple name of a `java.sql` exception. The first
column is the message, the other columns can only be `SQLState` and `ErrorCode`, and the first data row gives the
values. The statement it names throws exactly that class (never deduced from the SQLState):

```
SQLException,SQLState,ErrorCode
Deadlock victim,40001,1205
```

It is set like any mock (Message + Set Properties; in a Message shape a literal apostrophe is written `''`) and found
by the same keys; from 2.3.0 a write looks up its key too, so a write can fail. Class list, defaults, batch, what the
connector returns and an example: [mockjdbc-reference.md](mockjdbc-reference.md#errors-fault-injection).

- **Name**: the key of the statement that must fail, and only of it. A QUERY_ID (`mockjdbc_<id>`); the n-th use of a
  name (`mockjdbc_orders#2`: reads and writes of the table share the counter, so after a SELECT on `orders` its INSERT
  is `#2`; an error on `#1` and none on `#2` is a retry that succeeds); the bound values (`mockjdbc_customers?c42`),
  also on a write. **With Database V2 never the plain table name** (`mockjdbc_orders`): the connector reads the
  columns of the table there and metadata ignores error resources, so the plain name keeps the header and the error
  goes on `#n`, `?params` or a QUERY_ID. The same for the signature of a Database V2 *Stored Procedure*
  (see "Stored procedures").
- **What it leaves behind**: `mockjdbc_<name>_params` (and `#n`) is captured before the throw, as for a good write:
  it says what the `[S]` **tried** to write. `mockjdbc_<name>_error` (and `_error#n` when counted; lower case, named
  like `_params`) holds the message: a Decision on it **proves the injection fired**, which matters with Database V2,
  where an error document that the process ignores looks the same as a misspelled resource name.

**A connection lost in the middle of the `[S]`** is one of the most important technical failures: list it for every
`[S]` with two or more database steps, also when the `[S]` handles no error at all. The first steps succeed (their
writes are usually committed already), a later one fails, and every later use of the lost connection fails too. The
`[S]` must not return a success, and what it returns or logs must show which writes were done. Cause it with an error
resource of a connection class and a SQLState that starts with `08`:

```
SQLNonTransientConnectionException,SQLState,ErrorCode
Communications link failure,08S01,0
```

Put it on the first database step that must fail **and on every later step that must fail too** (the write of an error
log, a compensation in the catch path): mockjdbc keeps no state of a broken connection and gives `08` no meaning, so a
step without its own error resource succeeds. Cover each point of loss that leaves a different set of writes done, and
check the steps done before it (`_params`), the failing steps (`_error` is the failure, `_params` only the attempt),
that a later step with no error resource, which the `[S]` must not reach, shows no attempt, and what the `[S]` returns.
Expect the later Branch paths not to run with Legacy (their `_params` stay empty), and to run with Database V2 error
documents: there the later steps that must fail carry their own error resource.

What a database error does depends on the connector, so the `[UT]` checks a different outcome:

- **Legacy**: an error in a write (insert, update, delete, stored procedure write) fails **only that document**,
  after a rollback of its uncommitted rows; the other documents go on in that path, but the later paths of the Branch
  do not run, for any document (see the order of the writes, above). An error in a Get fails the whole connector
  call. When the `[S]` has its own Try/Catch or error route, the `[UT]` checks what the `[S]` returns, routes or logs.
  When the error leaves the `[S]`, the `[UT]` wraps the Process Call in a Try/Catch (`boomi-unit-testing`) and checks
  the caught message with a wildcard on a distinctive part of it (`*Duplicate entry*`): observed with 2.3.0-b1, a Get
  adds a prefix (`Errors occurred while building or executing SQL statement: <message>; Caused by: <message>`), a
  Send gives the bare message.
- **Database V2**: an error on one document becomes an application error, with payload
  `{"errorCode": <int>, "errorMessage": "<msg>"}`. With `returnApplicationErrors="true"` on the operation (the
  Companion's default) it is a **normal output document** of the connector, not an Exception: the `[UT]` checks the
  error document the `[S]` receives or routes (or the error path it takes), not only a caught Exception. Observed
  with 2.3.0-b1: `errorMessage` is the message of the resource, but a write loses its single quotes, so check it with
  a wildcard on a distinctive part without apostrophes (`*Duplicate entry*`); `errorCode` is the declared `ErrorCode`
  for a write and always 405 for a Standard Get, so check it **only for writes**. With `false` the document fails (a
  Try/Catch catches it). An error outside the per-document loop (connection, metadata) fails all documents. Besides
  error resources, a test can cause the connector's own errors (error 405 for the IN clause option) and those driven
  by the data.

**Coverage gap: "database down" behind Database V2 with `returnApplicationErrors="true"`.** An error resource makes a
statement fail, and the statement error becomes an error document on the normal path (observed with 2.3.0-b1, also
with a connection class and SQLState `08`: it never reaches a Try/Catch). A real connection failure happens outside the
per-document loop and fails the whole shape. So a Try/Catch around such a step, there for "database down", cannot be
reached: the `[UT]` tests the route the `[S]` gives the error document, not that Try/Catch. List the Try/Catch as a
coverage gap in the final answer, and name the scenario of the `[UT]` for what it tests. With
`returnApplicationErrors="false"`, or with the Legacy connector, the failure reaches the Try/Catch.

**Database V2 Standard Get**: its input document must hold only the `$` parameters of the query. With other fields
the connector returns one empty document and no rows, without an error (Companion, Database V2 references), also
against the real database: when the `[S]` sends a wider document, a `[UT]` that checks the rows finds a defect of the
`[S]`.

## The QUERY_ID policy

Whether the processes get a `-- QUERY_ID:` comment is a policy of the user, asked **once per workspace**: it takes the
place of the question of `boomi-unit-testing` ("When the `[S]` must change") for the QUERY_ID. Read the file
`.boomi-unit-testing` in the workspace directory (next to `.env`). It has no `query-id-policy` line: this is the first
time unit tests are built here, so ask the user with AskUserQuestion, write their answer in the file
(`query-id-policy=<value>`), and follow it from then on without asking again. The user can change it at any time (by
asking, or by editing the file).

The question: how should the tests recognise the queries of the processes?

1. **Minimal or no changes** (`minimal-changes`): the processes are not touched. The tests use the keys the driver
   deduces from the SQL (below), in their order of preference.
2. **Structured census, the agent adds the IDs** (`structured-agent`): every SQL written in the processes gets
   `-- QUERY_ID: <id>` as its **first line**. The agent adds it, pushes the `[S]` and deploys it only to the unit-test
   environment, and tells the user that the `[S]` changed and that deploying it where it runs is part of their release.
3. **Structured census, the user adds the IDs** (`structured-user`): the agent gives the user the list "operation →
   ID", waits for the confirmation, pulls the processes again and checks the first line of each SQL before going on.

Trade-off to put in the question: the QUERY_ID is a comment that the real database ignores, so the process behaves the
same in production, and each query gets a name that depends neither on the SQL text nor on the order of the
statements: the tests are structured and robust, at the price of changing every process once. With minimal changes the
processes stay exactly as in production, but the tests are less structured: they depend on table names, bound values
and, as a last resort, on the order of the statements.

With `minimal-changes`, an operation that only key 3 or 4 can name is mocked that way, labelled order-dependent, and
listed in the final answer with the note that a QUERY_ID would make its test robust: inform, do not ask.

**ID names**: `<project>.<service>.<step>`, grouped by project, then by service / flow / interface, then a meaningful
name for the step: `ecommerce.create-order-ws.select-customer`, `ecommerce.create-order-ws.insert-order`. One word of
lower case letters, digits, `.`, `-`, `_`: spaces, `?`, `#` and `,` make the statement fail with an `SQLException`.
Unique in the `[S]` and in the subprocesses it calls. Each ID has its own dataset and its own `#n` counter, whatever
the table; two statements with the same ID share them.

**Existing tests**: once a query has an ID, `mockjdbc_<table>` and `mockjdbc_<table>_params` no longer match it, and
the old test silently reads no rows or finds `_params` empty. Search the `[UT]` processes for the tables of those
statements, update them in the same change and run them again.

## Mock key without a QUERY_ID

Compute the name the driver uses with its own rules, not by reading the SQL as a person would:

- **SELECT**: the table after the **first** `FROM` outside parentheses (strings, comments and quoted names are
  skipped): `... FROM orders WHERE id IN (SELECT id FROM blocked)` gives `orders`, `FROM (SELECT id FROM orders) o`
  gives `orders`, `WITH x AS (...) SELECT * FROM x` gives `x` (the CTE name).
- **INSERT [INTO] / UPDATE / DELETE [FROM]**: the table after the keyword, with or without the column list.
- **Table names** (same rule for reads and writes): letters, digits, `_`, `$`; quotes `[]`, `""`, backticks removed
  (`[customers]` gives `customers`); schema kept (`dbo.customers`, `[dbo].[customers]` and `[dbo.customers]` all give
  `dbo.customers`). A qualified **read** looks for `mockjdbc_dbo.customers` first, then `mockjdbc_customers`; a
  qualified **write** is captured only under the full name: `mockjdbc_dbo.customers_params`.
- **Not named by the driver**: temporary tables (`#tmp`), table variables (`@rows`), quoted names with spaces, `?`,
  `#` or `,` (`[order details]`). They need a QUERY_ID or a step key.
- **Stored procedure**: the name after `EXEC`, `EXECUTE`, `CALL`, `{call ...}`, also through a "Stored Procedure"
  operation: see "Stored procedures" below.

Choose the key in this order:

1. **Table name** (default): `mockjdbc_<table>` (rows) and `mockjdbc_<table>_params` (captured write), lower case.
   It holds when the `[S]` has at most one read and at most one write on that table: every INSERT, UPDATE and DELETE
   on a table writes the same `_params`, and the last one wins.
2. **Table name + bound values**: `mockjdbc_<table>?<values>`, lower case, several values joined by `,`
   (`mockjdbc_customers?c42,gold`), when several SELECTs on the same table differ by the values they bind. The key
   depends on the values, not on the position, so it survives a reordering of the process. Reads only: writes
   are not keyed by value, except an error resource (see "Failure paths").
3. **Occurrence number** (backup): `mockjdbc_<table>#n` and `mockjdbc_<table>_params#n`, the n-th use of the name
   (reads and writes share the counter). The only way to tell apart several writes on the same table. It breaks when
   the statements on that name are reordered.
4. **Step number** (last backup): `mockjdbc_##stepN`, the n-th JDBC statement the connector creates in the execution
   (from 0), whatever its SQL. For statements that keys 1-3 cannot name (`#tmp`, `@rows`, `[order details]`).
   When `mockjdbc_##stepN` is defined, that statement uses it before any QUERY_ID or table name: rows for a read, the
   update count (`1`) for a write, whose parameters are then in `mockjdbc_##stepN_params` (no `#n`). It breaks when
   any statement before it is added, removed or moved, and the count depends on how the connector creates its
   statements: confirm N with a first run. Set `mockjdbc_##stepN` = `1` for the guessed N and log
   `mockjdbc_##step0_params`, `##step1_params`, ... with a temporary Notify: only the step of a write has parameters.
   A wrong N on a read takes over its data (the CSV `1` is a header without rows: the SELECT returns no rows), so
   check the reads too.

With keys 3 and 4 the `[UT]` says so in the label of the Set Properties or Decision shape (`order-dependent: step 2`),
and the answer to the user says that the test must be reviewed when the order of the `[S]` changes.

Database V2 reads the metadata of a written table **by table name** whatever the key: the header-only mock of a
written table is `mockjdbc_<table>` in every case (see reference). That header decides the binding: the connector
binds each field with the setter of its `|type`, so give the header every field of the input document, typed as the
captured value must be. A field with no column in the header is not an error for writes: Standard
Insert/Update/Delete silently do not bind it and Dynamic Insert leaves it out of the column list; Standard Get throws
"Keys Provided in Input Request is not matching the Request Profile".

## Stored procedures

The resource is `mockjdbc_<procedure>` (lower case), and its header says what the call returns:

- **Signature** (every column starts with `in_`, `out_`, `inout_` or `ret_`): the procedure answers with OUT
  parameters. The columns follow the order of the `?` of the call (`ret_` is the return value of `{? = call ...}`),
  the `|type` is the parameter type, the first data row gives the OUT values (IN values are ignored):
  `in_customer_id|integer,out_status,out_message` + `,OK,Saved`.
- **Any other header**: the result set of the procedure, as for a table.

Captured: `mockjdbc_<procedure>_params` holds the IN and IN OUT values only. Different answers per call or per IN
values work as for tables (`mockjdbc_<procedure>#2`, `mockjdbc_<procedure>?c42`).

A procedure call that must fail (error resource): with Database V2 keep the signature in the plain
`mockjdbc_<procedure>`, which the connector reads (`getProcedureColumns`) to bind the parameters by name, and put the
error on `mockjdbc_<procedure>#n` or `?params`. An error on the plain name makes the named binding fail before the call.

What to define for each way Boomi calls a procedure:

| Boomi | Resource | Assert on |
|---|---|---|
| Legacy profile *Stored Procedure Read*, OUT parameters | signature in the order of the profile parameters (`ret_` for a *Return* parameter) | the OUT values in the output document |
| Legacy profile *Stored Procedure Read*, rows | plain header | one document per row |
| Legacy profile *Stored Procedure Write*, Program Command *Stored Procedure* | none needed | `mockjdbc_<procedure>_params` |
| Database V2 *Stored Procedure*, OUT parameters | signature named after the profile fields (`in_customer_id` for `customer_id`), with `\|type` | `mockjdbc_<procedure>_params`, and the JSON with one field per OUT parameter |
| Database V2 *Stored Procedure*, rows | plain header | one document per row; the IN values are **not** captured |
| Map *SQL Lookup* / parameter value *Stored Procedure* | signature (inputs first, then outputs) | the value the map or the shape gets |

The Database V2 *Stored Procedure* operation asks the driver which parameters the procedure has
(`getProcedureColumns`), and mockjdbc answers only from a signature. A procedure that **returns rows** is mocked with
a plain header, which is no signature: the connector calls it with no parameters, so the rows come back but the IN
values cannot be asserted (`_params` stays empty). A resource is either a signature or a result set, so there is no
way to have both; the test checks the rows and what the `[S]` does with them. Not supported either: REF CURSOR
parameters, several result sets, functions.

## The database part of the `[UT]`

```
[UT] <process under test> - <scenario>
Start (No Data)
└─ Branch
   1 Arrange: Message "Mock customers" (CSV)
              → Set Properties mockjdbc_customers = Current Data
              → Message "Mock orders" (header only, DB V2) → Set Properties mockjdbc_orders = Current Data
              → Stop (continue)
   2 Act:     Message "Input order" → Process Call "[S] ..." → Stop (continue)
   3 Assert:  Decision "INSERT orders as expected?"
                mockjdbc_orders_params = "1001,C42,GOLD,250.00"
              ├ true  → next Decision ... → Stop (continue)
              └ false → Exception "orders insert: expected 1001,C42,GOLD,250.00 got {1}"
```

The example uses the table-name keys (policy `minimal-changes`, key 1). With a QUERY_ID the keys are `mockjdbc_<query id>` and
`mockjdbc_<query id>_params`.

- **Arrange**: one Message (CSV, header first, comma separator) + one Set Properties per query the `[S]` runs. The
  property is `mockjdbc_` + the key chosen for that operation, lower case. Tables that are only written still need
  the header with Database V2 (see reference).
- **Act**: the Process Call shares the Dynamic Process Properties of the test, so the `[S]` reads the mock tables and
  its writes are captured.
- **Assert**: one Decision per expected write: first value Dynamic Process Property `mockjdbc_<key>_params`, Equal To,
  the expected parameters **comma-separated in the order of the `?`**. Each value is the `toString()` of what the
  connector binds: a Double `250` is `250.0`, a BigDecimal of scale 2 is `250.00`, a date uses the mockjdbc date
  format (`17-May-12`). Same query run several times: check `mockjdbc_<key>_params#1`, `#2`, ...
- **Numbers in the expected value**: the spec gives a value (`50`), the capture gives its rendering (`50`, `50.0` or
  `50.00`, by the type and scale the process binds). Write the expected string from the type the profile or the map
  produces, and when the first run shows another rendering, check that it is numerically the spec value before
  adopting it. A fix that changes the scale (a rounding to 2 decimals) changes the rendering: that is a change of the
  expected value to declare in the defect record, not a new defect.
- Several scenarios in one `[UT]` need `mockjdbc#RESET` between them.
- **`_params` empty**: the process log does not show which properties the driver wrote. Add a temporary Notify in
  path 3 that logs every candidate key (`mockjdbc_<table>_params`, `mockjdbc_<schema>.<table>_params`, `#1`, the
  QUERY_ID key, `mockjdbc_##stepN_params`), run once, read which one holds the value, and remove the Notify.

## Quick reference

| Need | Dynamic Process Property |
|---|---|
| rows returned by the query `-- QUERY_ID: ecommerce.create-order-ws.select-customer` | `mockjdbc_ecommerce.create-order-ws.select-customer` = CSV |
| parameters of the last run of a write with a QUERY_ID | read `mockjdbc_<query id>_params` (each run: `#1`, `#2`...) |
| rows returned by `SELECT ... FROM customers` (default key) | `mockjdbc_customers` = CSV |
| typed columns / NULL | header `id\|integer,amount\|double,day\|date`; empty value in a typed column = NULL |
| several SELECTs on the same table, different bound values | `mockjdbc_customers?c42`, `mockjdbc_customers?c42,gold` |
| different rows for the 1st, 2nd... query on the table (backup, order-dependent) | `mockjdbc_customers#1`, `#2` (fallback: `mockjdbc_customers`) |
| rows of `SELECT ... FROM dbo.customers` | `mockjdbc_dbo.customers`, else `mockjdbc_customers` |
| parameters of the last INSERT/UPDATE/DELETE on `orders` | read `mockjdbc_orders_params` |
| parameters of each write (backup, order-dependent) | read `mockjdbc_orders_params#1`, `#2`... |
| parameters of a write on `[dbo].[orders]` | read `mockjdbc_dbo.orders_params` (full name only) |
| result set of a stored procedure `EXEC get_rate ?` | `mockjdbc_get_rate` |
| OUT parameters of `{call save_order(?, ?, ?)}` | `mockjdbc_save_order` = `in_id\|integer,out_status,out_message` + `,OK,Saved` |
| IN values of a procedure call | read `mockjdbc_<procedure>_params` |
| write on `#tmp`, `@rows`, `[order details]` | a `-- QUERY_ID:` (structured policy); without one, step key `mockjdbc_##stepN` = `1`, read `mockjdbc_##stepN_params` |
| restart the `#n` counters inside one execution | set `mockjdbc#RESET` = `true` |
| the statement `-- QUERY_ID: ecommerce.create-order-ws.insert-order` fails | `mockjdbc_ecommerce.create-order-ws.insert-order` = `SQLException,SQLState,ErrorCode` + `Deadlock victim,40001,1205`; read `mockjdbc_<query id>_error` (the message) and `_params` (what it tried to write) |
| only the 2nd use of `orders` fails (Database V2: the plain `mockjdbc_orders` keeps the header) | `mockjdbc_orders#2` = an error resource; `mockjdbc_orders?c42` for the values bound |
| lost connection from a step on | a connection class with SQLState `08...`, on that step and each later step that must fail (see "Failure paths") |

`mockjdbc_*` names are defined by the driver: they keep its spelling, without the `PP_` prefix. Details, CSV format,
date formats, Database V2 rules and troubleshooting: [mockjdbc-reference.md](mockjdbc-reference.md).

## Common mistakes

| Mistake | Effect | Fix |
|---|---|---|
| Only Class Name and URL extended on a Legacy connection | a predefined driver type ignores the class: the real database is used | extend Driver Type too, value `Custom` |
| `mockjdbc_Customers` / `PP_mockjdbc_customers` | driver does not find it, query returns no rows | lower case, no prefix: `mockjdbc_customers` |
| Mocking `mockjdbc_customers` for a query that has a `QUERY_ID` | no rows / `_params` empty: the ID wins over the table | use `mockjdbc_<query id>` |
| `QUERY_ID` added to the SQL, old `[UT]`s not updated | they still mock and check the table names, and fail or pass by chance | update every `[UT]` of those statements in the same change |
| `-- QUERY_ID:` on the second line, or `-- QUERY_ID: insert order` | not an ID (table name used), or `SQLException` | first line, one word |
| Expected value with spaces or in column order | Decision false | parameters in `?` order, comma, no spaces: `1001,C42,GOLD,250.00` |
| Asserting a SELECT through `_params` | always empty | SELECT parameters are never captured: use `?params` mocks to check them indirectly |
| Key by occurrence (`#n`) or step (`mockjdbc_##stepN`) as the first choice | breaks when the process is reordered | table name, then table + values; `#n`, then `##stepN` only as backup, labelled order-dependent |
| Several writes on the same table asserted on `mockjdbc_<table>_params` | only the last write is there | `_params#1`, `#2`... (key 3) or a QUERY_ID per statement |
| Write on `dbo.orders` asserted on `mockjdbc_orders_params` | always empty: writes are captured under the full name | `mockjdbc_dbo.orders_params` |
| Write on `#tmp` / `@rows` / `[order details]`, keyed by table | not captured by name: `_params` stays empty | QUERY_ID (structured policy), or step key 4 |
| Database V2 *Stored Procedure* that returns rows, IN values asserted on `_params` | always empty: without a signature the connector calls it with no parameters | assert the rows and their use; with OUT parameters, a signature named after the profile fields |
| Database V2 insert into a table without mock header | NullPointerException in the connector | define `mockjdbc_orders` with the header (types included) |
| Database V2 input field missing from the mock header | Standard Insert/Update/Delete do not bind it, Dynamic Insert leaves it out: `_params` lacks it, no error; Standard Get throws "Keys Provided ... not matching" | every field of the input document in the header, with its `\|type` |
| Database V2 failure `[UT]` that only expects an Exception | with `returnApplicationErrors="true"` the error is a normal output document: "none raised" | check the error document the `[S]` receives or routes (`errorMessage` with a wildcard; `errorCode` only for writes), and `mockjdbc_<name>_error` to prove the injection fired |
| Database V2 error resource on the plain table name (`mockjdbc_orders`) or procedure name | metadata ignores it and finds no header or signature: NullPointerException, or the named binding fails before the call | header or signature in the plain name, error on `#n`, `?params` or a QUERY_ID |
| Write failure `[UT]` on a Legacy `[S]` that expects the later Branch paths to run | Boomi skips every later path of the Branch for all documents: their writes are not captured, also those of the good documents | check their `_params` empty; with Database V2 error documents the later paths run |
| Lost connection simulated on one step only | the later steps (a compensation, a log write) succeed: nothing like a lost connection | an error resource of class `SQLNonTransientConnectionException`, SQLState `08...`, on every later step that must fail |
| Database V2 with `returnApplicationErrors="true"`: "database down" tested through an error resource | the error document is checked, not the Try/Catch around the step | coverage gap for that Try/Catch, in the final answer |
| Database V2 connection with pooling, only `className` and `url` extended | "isValid() returned false": no connection | extend `enablePooling` = `false` or `validationQuery` = `SELECT 1` |
| `[S]` logic on `"Rows Effected"` or `"Inserted Id"` (Database V2) tested with the default mock | always 1 row (0 only for an unrecognised table), `"Inserted Id"` always `[]` | "0 rows": step key `mockjdbc_##stepN` = `0`; logic on generated ids: coverage gap |
| Legacy write with a CLOB or BLOB field asserted on that value | captured empty: mockjdbc ignores stream setters | assert the other fields; the CLOB/BLOB value is a coverage gap |
| Legacy "Enable Batching" asserted as a batch | under the mock it runs row by row: the batch path is not exercised | assert the per-document captures; the batch itself is verified in DEV |
| Old jar still on the runtime after a library upgrade | older driver behaviour (schema writes not captured, `prepareCall` failing) | check it, then ask the user: local Atom stop, delete old jars, start; cloud runtime (no restart, no delete): another runtime, a QUERY_ID or a step key |
| Database V2 Standard Get fed with the whole input document | one empty document, no rows, no error | the input holds only the `$` parameters of the query |
| Mockjdbc older than 2.2.0 treated as a stop, or used without checking | no tests at all, or writes silently not captured (`crm_customers` with 2.1.0) | ask for the upgrade and go on with the old jar's limits, confirmed by a first run; list the order-dependent `[UT]`s and the technical failures not testable |
| Numeric parameter expected as the spec writes it (`50`) | Decision false on `50.00`: runs spent adapting strings | expected rendering from the bound type; a different one checked numerically against the spec before adopting it |
| Wrong N for `mockjdbc_##stepN` | a read returns no rows, or the write is not captured | confirm N with a first run (Notify on `##step0_params`, `##step1_params`...) |
| A failure case not tested: a `[UT]` that expects an exception passes when no exception is raised | the error path of the `[S]` is never proved | Decision "exception raised?" then the expected message, as in `boomi-unit-testing`; check that no write was captured |
| A technical database failure simulated without an error resource (a malformed CSV, a wrong name) | the `[UT]` tests nothing, or a connector error that is not an `SQLException` with a SQLState | an error resource; with a jar older than `2.3.0-b1`, a coverage gap in the final answer |