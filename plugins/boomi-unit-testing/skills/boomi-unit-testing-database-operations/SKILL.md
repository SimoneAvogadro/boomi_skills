---
name: boomi-unit-testing-database-operations
description: Use when a Boomi process or subprocess under unit test reads or writes a database with the Database Legacy or Database V2 connector (SQL queries, inserts, updates, deletes, stored procedures, SQL lookups) and the database must be mocked with mockjdbc, or when a [UT] test must check the DB writes of the process.
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

**REQUIRED:** `boomi-unit-testing` for the strategy this skill plugs into: the `[UT]` process, the question before any
change to the `[S]`, how extensions are declared, set and checked, the unit-test environment and the cleanup.
This skill gives the database part of the test; the rest of the `[UT]` is built as that skill says.

Priority: Boomi Companion < these skills < project or customer skills (see `boomi-unit-testing`, "Which skill wins").

The rules below are those of mockjdbc **2.2.0**.

## Prerequisite: the mockjdbc Custom Library

Before the first test on an environment, check (Companion scripts) that

- `boomi-component-search.sh --type customlibrary` + `boomi-component-pull.sh` finds a library with
  `<Type>connector</Type>`, the `<connectorType>` of the `[S]`'s connection (`database` = Database Legacy,
  `officialboomi-X3979C-dbv2da-prod` = Database V2) and `Files` `mockjdbc-*.jar`, `opencsv-*.jar`, `aspectjrt-*.jar`,
  with `mockjdbc-2.2.0.jar` or later (an older jar: ask the user to upgrade the library);
- it is deployed on the unit-test environment: `POST DeployedPackage/query` with `environmentId`, `componentId` of
  the library, `active` = `true` (the lookup of `boomi-undeploy.sh --by-component`; no read-only script).

No such library: **stop**. Tell the user that uploading the jars and creating the library are manual (Boomi has no API
to upload jars), point to https://github.com/SimoneAvogadro/mockjdbc/blob/master/FEATURES.md#setting-up-the-custom-library
and wait for their confirmation; never upload jars or create the library yourself. After the confirmation check
again. Library found but not deployed there: `boomi-deploy.sh <pulled library XML>` (to the unit-test environment),
then go on; it is part of the cleanup of `boomi-unit-testing`.

**The library is not what the runtime runs.** After an upgrade of the library the runtime can keep loading the old
jar (jar locking: the old file stays in `userlib` and on the classpath until the runtime is stopped and the file
removed). Suspect it when the driver behaves like an older version: a schema-qualified write not captured under
`mockjdbc_<schema>.<table>_params`, a "Stored Procedure" operation failing in `prepareCall`, a `-- QUERY_ID:` ignored.
Then check it (a temporary Notify that logs the expected `_params` key and its neighbours, or an existing test of
that feature run on the same runtime) and **ask the user how to go on**. On a local Atom the user can stop it, delete
the old jars and start it again. **Cloud runtimes and Atoms cannot be restarted and their jars cannot be deleted**:
there the choice is another runtime, or keys that work with the behaviour the runtime has (a QUERY_ID, options 1 or
2; a step key, key 4).

## Inventory of the database operations

Before writing the `[UT]`, list every database operation that the `[S]` runs, and those of the subprocesses it calls:
Database Legacy (`<sql>` of the `profile.db`, or dynamic insert/update/delete) and Database V2 (SQL operations, or
operations built from a table). For each one record: the step, the connector (Legacy or V2), the table or procedure,
the kind (SELECT, INSERT, UPDATE, DELETE, stored procedure), whether the process defines its SQL text, and whether
that SQL starts with `-- QUERY_ID:` or `-- TESTCASE:` (both count as an ID).

- **Already has an ID**: the test uses the ID keys (`mockjdbc_<id>`, `mockjdbc_<id>_params`). No question.
- **SQL generated by the connector** (Legacy dynamic insert/update/delete; Database V2 Dynamic Insert and Dynamic
  Get, whose `query` field is empty): there is no text to put the comment in. No question: choose the mock key
  directly (below). With mockjdbc, Database V2 generates plain SQL such as
  `Insert into payments(pay_id,amount) values (?,?)`: no schema, even with `schemaName` set, and no quotes, so the
  table-name key works. Database V2 Standard Get/Insert/Update/Delete and Update Commit By Rows keep their SQL in the
  operation: they get the question.
- **Every other operation**: ask the QUERY_ID question.

Also note the connection of each operation: a connection shared with other projects (for example in a `#common`
folder) is more likely to be deployed in other processes of the unit-test environment, and a QUERY_ID on an operation
shared with them changes their SQL too.

**Database V2 Standard Get**: its input document must hold only the `$` parameters of the query. With other fields
the connector returns one empty document and no rows, without an error (Companion, Database V2 references), also
against the real database: when the `[S]` sends a wider document, a `[UT]` that checks the rows finds a defect of the
`[S]`.

## The QUERY_ID question

This is the question of `boomi-unit-testing` ("When a mock needs a change in the `[S]`") for the database: for each
of these operations, propose an ID and ask which of the three options applies. Option 1 adds
`-- QUERY_ID: <id>` as the **first line** of the SQL; option 3 uses the mock keys below.

Trade-off to put in the question: the QUERY_ID is a comment on the first line, the real database ignores it and the
process behaves the same in production, and the test gets a key that depends neither on the SQL text nor on the order
of the statements. Option 3 keeps the `[S]` exactly as it is in production, with nothing to push or redeploy. Mark
option 3 **(Recommended)** when key 1 or key 2 below covers the operation; otherwise recommend option 1 and say why
(for example: a write on a temporary table `#tmp` is not captured by name and would need a step key).

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
   depends on the values, not on the position, so it survives a reordering of the process. Reads only: writes are
   not keyed by value.
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
written table is `mockjdbc_<table>` in every case (see reference).

## Stored procedures

The resource is `mockjdbc_<procedure>` (lower case), and its header says what the call returns:

- **Signature** (every column starts with `in_`, `out_`, `inout_` or `ret_`): the procedure answers with OUT
  parameters. The columns follow the order of the `?` of the call (`ret_` is the return value of `{? = call ...}`),
  the `|type` is the parameter type, the first data row gives the OUT values (IN values are ignored):
  `in_customer_id|integer,out_status,out_message` + `,OK,Saved`.
- **Any other header**: the result set of the procedure, as for a table.

Captured: `mockjdbc_<procedure>_params` holds the IN and IN OUT values only. Different answers per call or per IN
values work as for tables (`mockjdbc_<procedure>#2`, `mockjdbc_<procedure>?c42`).

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

The example uses the table-name keys (option 3, key 1). With a QUERY_ID the keys are `mockjdbc_<query id>` and
`mockjdbc_<query id>_params`.

- **Arrange**: one Message (CSV, header first, comma separator) + one Set Properties per query the `[S]` runs. The
  property is `mockjdbc_` + the key chosen for that operation, lower case. Tables that are only written still need
  the header with Database V2 (see reference).
- **Act**: the Process Call shares the Dynamic Process Properties of the test, so the `[S]` reads the mock tables and
  its writes are captured.
- **Assert**: one Decision per expected write: first value Dynamic Process Property `mockjdbc_<key>_params`, Equal To,
  the expected parameters **comma-separated in the order of the `?`**. Each value is the `toString()` of what the
  connector binds: a Double `250` is `250.0`, a date uses the mockjdbc date format (`17-May-12`). Same query run
  several times: check `mockjdbc_<key>_params#1`, `#2`, ...
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
| write on `#tmp`, `@rows`, `[order details]` | a `-- QUERY_ID:` (options 1 or 2); without one, step key `mockjdbc_##stepN` = `1`, read `mockjdbc_##stepN_params` |
| restart the `#n` counters inside one execution | set `mockjdbc#RESET` = `true` |

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
| Write on `#tmp` / `@rows` / `[order details]`, keyed by table | not captured by name: `_params` stays empty | QUERY_ID (options 1 or 2), or step key 4 |
| Database V2 *Stored Procedure* that returns rows, IN values asserted on `_params` | always empty: without a signature the connector calls it with no parameters | assert the rows and their use; with OUT parameters, a signature named after the profile fields |
| Database V2 insert into a table without mock header | NullPointerException in the connector | define `mockjdbc_orders` with the header (types included) |
| Old jar still on the runtime after a library upgrade | older driver behaviour (schema writes not captured, `prepareCall` failing) | check it, then ask the user: local Atom stop, delete old jars, start; cloud runtime (no restart, no delete): another runtime, a QUERY_ID or a step key |
| Database V2 Standard Get fed with the whole input document | one empty document, no rows, no error | the input holds only the `$` parameters of the query |
| Wrong N for `mockjdbc_##stepN` | a read returns no rows, or the write is not captured | confirm N with a first run (Notify on `##step0_params`, `##step1_params`...) |
