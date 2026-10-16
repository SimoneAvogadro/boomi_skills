---
name: boomi-unit-testing
description: Use when a Boomi process or subprocess needs a unit test, a mock, a stub or a test harness - especially when it reads or writes a database (Database Legacy or Database V2 connector, stored procedures) that is not reachable or must not be touched by the test, or when a test must fail by itself instead of someone reading Notify logs.
---

# Boomi unit testing (database mocked with mockjdbc)

## Overview

A unit test is a **separate `[UT]` process** that prepares the data, calls the `[S]` subprocess under test
**unchanged** with a Process Call, and checks the result with Decision shapes that end in an **Exception** when
the check fails. The test passes when the execution completes, fails when it ends in error: no one has to read the
logs.

The database is replaced by **mockjdbc** (https://github.com/SimoneAvogadro/mockjdbc), a JDBC driver that
answers queries with CSV data taken from Dynamic Process Properties and records the parameters of every INSERT,
UPDATE, DELETE and stored procedure call in other Dynamic Process Properties. The switch to mockjdbc happens only in
the test run, through **extensions** of the database connection: the process and its connection keep pointing to
the real database.

**REQUIRED BACKGROUND:** `bc-integration:boomi-integration` for the XML of each shape and the push/deploy/execute
scripts. **REQUIRED:** `boomi-coding-conventions` for names (`[S]`, `[UT]`, `PP_`, `D_`).

## Design the process so it can be tested

- Put the logic in an `[S]` subprocess with a passthrough start; a listener (WSS, JMS, FSS...) is only a thin
  wrapper (listener → Process Call `[S]` → Return Documents). Listener processes cannot run in test mode.
- The `[S]` takes everything it needs as input documents, `PP_` / `D_` properties or connections: no hardcoded
  test data, no "if test" branches inside it. Test data and checks live in the `[UT]` process only.
- Every connection the `[S]` uses is a real component that the test can override with extensions.
- Do not add a mock Message shape in the `[S]` main path, nor a test branch driven by a property: this skill
  replaces the Companion "temporary Message" and `DPP_FROM_WRAPPER` patterns. Test code inside the `[S]` is
  forgotten and reaches production.

## The `[UT]` process

Create it in a folder named `Unit test`, inside the folder of the process under test (`Unit test - <description>` if
the folder has several groups of tests); see `boomi-coding-conventions`.

```
[UT] <process under test> - <scenario>
Start (No Data)
└─ Branch  (Boomi runs the paths one after the other, in order)
   1 Arrange: Message "Mock customers" (CSV) → Set Properties mockjdbc_customers = Current Data
              → Message "Mock orders" (header only, DB V2) → Set Properties mockjdbc_orders = Current Data
              → Stop (continue)
   2 Act:     Message "Input order" (the document the [S] receives) → Process Call "[S] ..."
              → Stop (continue)
   3 Assert:  Decision "INSERT orders as expected?"  mockjdbc_orders_params = "1001,C42,GOLD,250.00"
              ├ true  → next Decision ... → Stop (continue)
              └ false → Exception "orders: expected 1001,C42,GOLD,250.00 got {1}"
```

- **Arrange**: one Message (CSV, header first, comma separator) + one Set Properties per table the `[S]` reads.
  The property is `mockjdbc_` + table name in **lower case**. Tables that are only written still need the header with
  Database V2 (see reference).
- **Act**: the input document of the `[S]` comes from a Message shape in the `[UT]` (the execution API cannot inject
  documents). Call the `[S]` with a Process Call (`wait="true"`, `abort="true"`): it shares the Dynamic Process
  Properties of the test, so it reads the mock tables and its writes are captured.
- **Assert**: in the last Branch path, one Decision per expected write: first value Dynamic Process Property
  `mockjdbc_<table>_params`, Equal To, the expected parameters **comma-separated in the order of the `?`**. False →
  Exception (`stopsingledoc="false"`, so the whole execution ends in ERROR) whose message shows expected and
  actual value (`{1}` = the same property). Each value is the `toString()` of what the connector binds: a Double
  `250` is `250.0`, a date uses the mockjdbc date format. When unsure, run the test once, read the actual value in
  the Exception message, and set it as expected only after checking that it is right. Several writes on the same table: check
  `mockjdbc_<table>_params#1`, `#2`, ... For documents returned by the `[S]`: store them with Set Properties on its
  return path (`PP_ACTUAL_RESPONSE` = Current Data) and compare in the assert path.
- One scenario per `[UT]` process is the default; several scenarios in one process need `mockjdbc#RESET` between them.

## Switch the connection to mockjdbc (only for the test)

| Connection field (extension) | Database (Legacy) | Database V2 (`GenericConnectionConfig`) | Test value |
|---|---|---|---|
| Driver Type | yes | (no such field) | `Custom` |
| Class Name | yes | `className` | `me.avogadro.mockjdbc.MockJdbcDriver` |
| Connection URL | yes | `url` | `any` |

User name and password stay those of the real connection: mockjdbc ignores them.

1. In the `[UT]` process Extensions → Connection Settings: make **all** these fields of the `[S]`'s DB connection
   extensible, always: with the legacy connector **Driver Type, Class Name and Connection URL**, even when the
   connection already uses `Custom`. Only the `Custom` driver type uses the Class Name: a connection with a
   predefined type (SQL Server, Oracle, ...) ignores the mockjdbc class, and the test would reach the real driver.
   A `[UT]` without the Driver Type extension works only by chance and breaks when the connection changes type.
   Extensions are declared on the process that is deployed and run (the `[UT]`) and apply to the connections of the
   subprocesses it calls. Declare them in the GUI or start from a pulled process that has them: each override needs its
   connector-specific `xpath`, otherwise it is silently ignored (Companion error reference, Issue #31).
2. **mockjdbc Custom Library**: before the first test on an environment, check (Companion scripts) that
   - `boomi-component-search.sh --type customlibrary` + `boomi-component-pull.sh` finds a library with
     `<Type>connector</Type>`, the `<connectorType>` of the `[S]`'s connection (`database` = Database Legacy,
     `officialboomi-X3979C-dbv2da-prod` = Database V2) and `Files` `mockjdbc-*.jar`, `opencsv-*.jar`, `aspectjrt-*.jar`;
   - it is deployed on the test environment: `POST DeployedPackage/query` with `environmentId`, `componentId` of
     the library, `active` = `true` (the lookup of `boomi-undeploy.sh --by-component`; no read-only script).

   No such library: **stop**. Tell the user that uploading the jars and creating the library are manual (Boomi has
   no API to upload jars), point to
   https://github.com/SimoneAvogadro/mockjdbc/blob/master/FEATURES.md#setting-up-the-custom-library and wait for
   their confirmation; never upload jars or create the library yourself. After the confirmation check again.
   Library found but not deployed there: `boomi-deploy.sh <pulled library XML>` (to `BOOMI_ENVIRONMENT_ID`, the test
   environment), then go on.
3. Run it:
   - **GUI**: Test → Test Extensions → Connection Settings → untick "Use connection component value" for those
     fields and enter the values above.
   - **Automated** (Companion scripts): deploy the `[UT]` to a **dedicated test environment**, set the values as
     Environment Extensions there (`boomi-extensions.sh`, legacy Driver Type value `custom`), run
     `boomi-test-execute.sh --process-id <[UT] id>`; the test passed if the status is `COMPLETE`, failed if `ERROR`
     (the Exception message says why).
   - **After every `set`, `get` again**: each of the three fields must show the value with `useDefault: false`. The
     platform can accept a `set` and keep the default without any error (seen with Driver Type on a field added to
     the declarations by a redeploy; once saved in the GUI, later API writes work). A field still at
     `useDefault: true`: **stop**, ask the user to set it once in Manage → Environment Extensions of the test
     environment (untick "Use connection component value"), then `get` again before running the test. Running
     with a field at its default can reach the real driver.
4. Never set the mockjdbc values on an environment where real processes run.

## Quick reference

| Need | Dynamic Process Property |
|---|---|
| rows returned by `SELECT ... FROM customers` | `mockjdbc_customers` = CSV |
| typed columns / NULL | header `id\|integer,amount\|double,day\|date`; empty value in a typed column = NULL |
| different rows for the 1st, 2nd... query on the table | `mockjdbc_customers#1`, `#2` (fallback: `mockjdbc_customers`) |
| different rows per bound parameter (lower case) | `mockjdbc_customers?c42` |
| result of a stored procedure `EXEC get_rate ?` | `mockjdbc_get_rate` |
| parameters of the last INSERT/UPDATE/DELETE on `orders` | read `mockjdbc_orders_params` |
| parameters of each write | read `mockjdbc_orders_params#1`, `#2`... |
| parameters of a stored procedure call | read `mockjdbc_<proc>_params` |
| table name with digits/underscores, or same table in two places | `-- TESTCASE: <name>` as first SQL line → `mockjdbc_<name>`, `mockjdbc_<name>_params` |
| restart the `#n` counters inside one execution | set `mockjdbc#RESET` = `true` |

`mockjdbc_*` names are defined by the driver: they are the exception to the `PP_` prefix. Details, CSV format, date
formats, Database V2 rules and troubleshooting: [mockjdbc-reference.md](mockjdbc-reference.md).

## Common mistakes

| Mistake | Effect | Fix |
|---|---|---|
| Branch paths in the wrong order | Mock not yet set when the `[S]` queries (no rows), or check run before the write | Path 1 arrange, path 2 Process Call, path 3 assert |
| `mockjdbc_Customers` / `PP_mockjdbc_customers` | Driver does not find it, query returns no rows | lower case, no prefix: `mockjdbc_customers` |
| Expected value with spaces or in column order | Decision false | parameters in `?` order, comma, no spaces: `1001,C42,GOLD,250.00` |
| Asserting a SELECT through `_params` | always empty | SELECT parameters are never captured: use `?params` mocks to check them indirectly |
| Database V2 insert into a table without mock header | NullPointerException in the connector | define `mockjdbc_orders` with the header (types included) |
| A stub switch in the `[S]` (Decision on `PP_DB_STUB` → stub subprocess instead of the DB connector) | test code shipped to production; the real DB operations are never exercised | `[S]` unchanged, DB connection switched to mockjdbc by extensions |
| Hand-written stub subprocesses that record the "inserted" values | the connector step, its SQL and its parameter binding are not tested | mockjdbc behind the real operation captures what the connector actually sends |
| Test "passes" by reading Notify output | needs a human, not repeatable | Decision + Exception |
| Extension field without `xpath` | real DB is used | declare the override from the GUI / a pulled component |
| Old jar still on the runtime | old behaviour | stop the Atom, delete old jars, restart |
