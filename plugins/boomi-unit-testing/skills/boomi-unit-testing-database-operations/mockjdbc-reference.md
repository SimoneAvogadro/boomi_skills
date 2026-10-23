# mockjdbc reference for Boomi tests

Source: https://github.com/SimoneAvogadro/mockjdbc (README, TUTORIAL.md, FEATURES.md sections 3 and 11). Written for
mockjdbc 2.2.x; check the CHANGELOG of the repository when a newer version is installed.

## Contents
- Installation on the runtime
- How a statement finds its mock data
- Captured parameters (assertions)
- CSV format
- Database V2 connector
- Connector behaviour under the mock
- Extension declarations
- Counters and several scenarios
- Scripts
- Troubleshooting

## Installation on the runtime

Manual setup (download, upload to Account Libraries, Custom Library component, deployment):
https://github.com/SimoneAvogadro/mockjdbc/blob/master/FEATURES.md#setting-up-the-custom-library. Identifiers the
agent needs:

- Custom Library XML (`type="customlibrary"`): `<Type>connector</Type>`, `<connectorType>` `database` (Database
  Legacy) or `officialboomi-X3979C-dbv2da-prod` (Database V2), one library per connector; `Files` entries
  `mockjdbc-<version>.jar`, `opencsv-2.3.jar`, `aspectjrt-1.9.22.1.jar` (the driver classes do not load without it);
  `slf4j-api` is provided by the Boomi runtime.
- Deployed to the test environment only; after the deployment the jars are in `/userlib/<connector type>` of the runtime.
- Driver class `me.avogadro.mockjdbc.MockJdbcDriver`, JDBC URL `any` (or `jdbc::mock::<dir>` for a directory of CSV
  files). The driver detects Boomi (`com.boomi.execution.ExecutionUtil`) and then reads and writes Dynamic Process
  Properties. Container log at startup: `MockJDBC <version> registered in DriverManager: false`.

**Upgrade**: stop the Atom, delete the old mockjdbc jars (and old data jars of the same library), start the Atom.
Needed with both connectors: with Database V2 Windows keeps the old jars locked; with the legacy connector
(`userlib\database`) the old jar stays on the classpath even when nothing is locked.

## How a statement finds its mock data

Resource name, in order of priority:

1. step resource (`mockjdbc_##step0`, `##step1`...: the n-th statement of the execution, whatever its SQL);
2. `-- QUERY_ID: <id>` as the **first line** of the SQL (wins over the table name). The ID is one
   word: empty, or with spaces, `?`, `#` or `,` → `SQLException`. The older `-- TESTCASE: <name>` works the same,
   without checks;
3. the table after the **first** `FROM` outside parentheses (strings, comments, quoted names skipped; a derived table
   `FROM (SELECT ... FROM t)` gives `t`, a CTE gives its own name); a schema-qualified name looks for the full name,
   then the last part (`dbo.customers`, then `customers`);
4. stored procedure after `EXEC`, `EXECUTE`, `CALL`, `{call ...}`, `{? = call ...}` (also through `prepareCall`);
5. `SELECT` without `FROM` → one row with value `1`;
6. nothing found → empty result set (no error).

For the n-th use of a name the lookup is `name?params#n` → `name?params` → `name#n` → `name`; inside Boomi each
step also checks the Dynamic Process Property `mockjdbc_<lookup>` (first as written in the SQL, then lower case).
**Write the property names in lower case**: they are always read and always written.

| SQL | Mock property read |
|---|---|
| `SELECT ... FROM customers` | `mockjdbc_customers` |
| same, second time in the execution | `mockjdbc_customers#2`, else `mockjdbc_customers` |
| `SELECT ... WHERE id = ?` with `C42` bound | `mockjdbc_customers?c42`... then `mockjdbc_customers` |
| `-- QUERY_ID: ecommerce.orders-ws.select-customer` + any SQL | `mockjdbc_ecommerce.orders-ws.select-customer` |
| same, `C42` bound | `mockjdbc_ecommerce.orders-ws.select-customer?c42`, then without `?c42` |
| `EXEC get_rate ?` | `mockjdbc_get_rate` |
| `SELECT ... FROM [dbo].[customers]` | `mockjdbc_dbo.customers`, then `mockjdbc_customers` |

Table names: letters, digits, `_`, `$`, quoted with `[]`, `""` or backticks, up to 4 parts with schema. Not
recognised: `#tmp`, `@rows`, quoted names with spaces, `?`, `#` or `,` (use a `-- QUERY_ID:`).

Parameters in the `?params` key are rendered with `toString()`, dates with the formats below, joined with `,`.
An empty or blank property counts as not defined.

## Captured parameters (assertions)

Every prepared statement **except SELECT** stores its parameters as a comma-separated string, in the order of the
`?`, in two Dynamic Process Properties (never persisted): `mockjdbc_<Name>_PARAMS` (name as written in the SQL) and
`mockjdbc_<name>_params` (lower case). Assert on the lower case one.

| Statement | Captured in |
|---|---|
| `INSERT INTO orders (...) VALUES (?, ?)` | `mockjdbc_orders_params` |
| `UPDATE orders SET ...` / `DELETE FROM orders ...` | `mockjdbc_orders_params` |
| `INSERT INTO [dbo].[orders] ...` (with or without column list), `INSERT dbo.orders ...` | `mockjdbc_dbo.orders_params` (full name only) |
| `EXEC upd_status ?, ?` / `{call upd_status(?, ?)}` | `mockjdbc_upd_status_params` (with `prepareCall`: IN and IN OUT values only) |
| `-- QUERY_ID: ecommerce.orders-ws.insert-order` + any statement but a SELECT | `mockjdbc_ecommerce.orders-ws.insert-order_params` |
| statement on a step resource | `mockjdbc_##step<n>_params` |

- `_params` holds the **last** write; each write is also in `_params#1`, `_params#2`... (counter shared with the
  queries on the same name: a SELECT on `orders` then an INSERT into `orders` is occurrence 1 then 2; with a
  QUERY_ID on each statement every query has its own counter).
- Batches: one capture per parameter set.
- A parameter not set is left empty (`,a`).
- The table of `INSERT [INTO]` / `UPDATE` / `DELETE [FROM]` follows the table-name rule above; the capture uses the
  **full** name (`dbo.orders_params`, never `orders_params`). Names the driver does not recognise (`#tmp`, `@rows`,
  `[order details]`) need a `-- QUERY_ID:` comment (in the operation's SQL), or, without one, a step resource
  (`mockjdbc_##stepN` = `1`, parameters in `mockjdbc_##stepN_params`).
- Steps count the JDBC statements the connector **creates** (from 0), not the executions: a prepared statement run
  for many documents is one step.
- SELECT parameters are never captured: assert them indirectly (mock only `customers?c42`; a wrong parameter gives no
  rows and a later assertion fails).
- `executeUpdate` returns 1 when the table is recognised, 0 otherwise. No generated keys (empty result set).

## CSV format

- Header first, one line per row, **comma** separator (a `;` file is one column). Whitespace around values is removed.
- Quotes for values with commas, line breaks or quotes (`"Smith, John"`, `"say ""hi"""`); empty quoted value as
  `a,""` (no space).
- Every row must have as many values as the header (`IllegalArgumentException` otherwise); header only = no rows.
- Optional types: `name|type` with `varchar` (default), `integer`, `bigint`, `double`, `decimal`, `boolean`, `date`,
  `time`, `timestamp`. An empty value in a typed (non-varchar) column is SQL NULL.
- `getBoolean` is true only for `true` (any case): `1`, `yes`, `Y` are false.
- Default date formats (`SimpleDateFormat`, English month names whatever the locale, JVM time zone): date
  `dd-MMM-yy` (`17-MAY-12`, any case, 4-digit year accepted), time `HH:mm` (seconds dropped), timestamp
  `yyyyMMdd HHmmss.SSS` (`20120517 143000.000`, milliseconds required). The same formats render date parameters in
  `_params` and `?params` keys: `17-May-12`.
- Stored procedure signature: a header whose columns all start with `in_`, `out_`, `inout_` or `ret_` (see SKILL.md,
  "Stored procedures"); reading an IN parameter or one not in the header throws an `SQLException`, a header without
  data rows gives NULL for every OUT parameter.

## Database V2 connector

The connector reads the metadata (`getColumns`) before running operations it builds from a table definition
(Standard Get/Insert/Update/Delete, Dynamic Get/Insert...):

- **define every table the operation writes to or filters on**, even header only, by **table name** (also when
  the statement has a QUERY_ID: the metadata is read by table), e.g. `mockjdbc_orders` =
  `order_id|integer,customer_id,segment,amount|double` (types make numbers bound as numbers);
- **every field of the input document must be a column of that header**: a missing table header gives a
  NullPointerException; a missing column is not bound (see "Connector behaviour under the mock");
- **a query with `IN (...)`** (also a subquery, `WHERE id NOT IN (SELECT ...)`) needs the IN clause option of the
  operation: without it the connector rejects the query before the driver sees it, with error 405 `Kindly select the
  IN clause check box only if Sql Query contains IN Clause !` (the output document holds the error). `NOT EXISTS
  (SELECT ...)` needs no option;
- a **Stored Procedure** operation reads the parameters from the signature (`getProcedureColumns`): name the columns
  after the profile fields and type them.

Overrides: the legacy connector always needs all three, Driver Type `Custom`, Class Name and Connection URL (never
only Class Name and URL, see SKILL.md); Database V2 has no driver type, only `className` and `url`. The blocks to
declare them are below.

## Connector behaviour under the mock

Source: decompiled connectors, Legacy `connector-database-20.03.0.jar` and Database V2 `connector-db-v2-0.0.73.jar`
(effective version 64), 2026-10-23. Static analysis, not reproduced at run time unless said: recheck it when the
connector changes.

### Legacy

- **CLOB and BLOB fields are captured empty**: the connector binds them with `setCharacterStream(int, Reader, int)`
  and `setBinaryStream(int, InputStream, int)`, which mockjdbc 2.2.0 ignores. The other fields of the write are
  captured; the CLOB/BLOB value cannot be asserted (planned in mockjdbc FUTURE.md).
- **"Enable Batching" runs row by row**: batching needs `supportsBatchUpdates()` true, and mockjdbc returns false.
  The batch path is not exercised; captures are per document, as without batching.
- **Errors**: an `SQLException` in a Send (insert, update, delete, stored procedure write) fails only that document,
  after `rollback()` of its uncommitted rows; the other documents go on. In a Get the whole connector call fails.

### Database V2

- **Errors**: an `SQLException` on one document becomes `APPLICATION_ERROR`, status code = the SQL error code,
  payload `{"errorCode": <int>, "errorMessage": "<msg>"}`. With `returnApplicationErrors="true"` on the operation
  (the default the Companion writes) it is a normal output document of the connector shape; otherwise the document
  fails (a Try/Catch catches it). An error outside the per-document loop (connection, metadata) fails all documents.
  The errors a test can cause are the connector's own (error 405 for the IN clause option) and those driven by the
  data; mockjdbc 2.2.0 cannot inject an `SQLException`.
- **Response fields**: `"Rows Effected"` (Standard/Dynamic Update, Delete, Upsert) is 1 for a recognised table, 0 when
  the target is not recognised; a step resource `mockjdbc_##stepN` = `0` gives 0. `"Inserted Id"` (inserts) is always
  `[]` (no generated keys). The connector never branches on 0 rows: this matters only when the `[S]` maps or decides
  on these fields. Then the "0 rows" case needs the step key with `0`, and logic on generated ids cannot be tested.
- **Binding from the mock header**: the connector chooses the setter from `getColumns`, that is from the `|type` of
  the mock header (only `varchar`, `integer`, `bigint`, `double`, `decimal`, `boolean`, `date`, `time`, `timestamp`).
  NVARCHAR, CLOB, BLOB and JSON columns are bound as the header type says, not as in production; the value is still
  captured.
- **Field of the input document with no column in the header**: Standard Insert/Update/Delete silently do not bind
  it (the parameter index still moves on, so that `?` stays empty in `_params`); Dynamic Insert leaves it out of the
  column list; Standard Get throws "Keys Provided in Input Request is not matching the Request Profile". A table with
  no header at all gives a NullPointerException.
- **Vendor branches skipped**: mockjdbc reports the product name "MockJDBC", so the connector always runs its generic
  branch: no SQL Server `SCOPE_IDENTITY` / `FOR JSON`, no Oracle date binding, no MySQL/PostgreSQL upsert variants.
  Vendor-specific behaviour is verified in DEV, not by the unit tests.
- **Connection pooling**: with pooling enabled, test-on-borrow and no validation query, commons-dbcp2 calls
  `isValid()`, which mockjdbc answers false: "isValid() returned false", no connection. In the `[UT]` extend
  `enablePooling` = `false`, or `validationQuery` = `SELECT 1` (mockjdbc answers a `SELECT` without `FROM` with one
  row). The fields `enablePooling`, `validationQuery`, `testOnBorrow` are in the Database V2 `ConnectionOverride`
  field list. Found by reading the code: verify on a first run.

### Dynamic Process Properties

No documented size limit: the values live in memory, so very large mocks are bounded by the runtime memory.

## Extension declarations

Put the block in `<bns:processOverrides><Overrides xmlns=""><Connections>` of the `[UT]`, with the `id` of the
`[S]`'s connection; the other fields of the connection can be omitted or listed with `overrideable="false"`.
Taken from processes declared in the GUI and pulled, and run with mockjdbc.

**Database (Legacy)**: every field needs its `xpath`.

```xml
<ConnectionOverride id="<connection id>">
  <field id="driverId" label="Driver Type" overrideable="true" xpath="DatabaseConnectionSettings/@driverId"/>
  <field id="className" label="Class Name" overrideable="true" xpath="DatabaseConnectionSettings/@className"/>
  <field id="urlFormat" label="Connection URL" overrideable="true" xpath="DatabaseConnectionSettings/@urlFormat"/>
</ConnectionOverride>
```

Environment Extension values (`boomi-extensions.sh`): `driverId` = `custom`, `className` =
`me.avogadro.mockjdbc.MockJdbcDriver`, `urlFormat` = `any`.

**Database V2** (`GenericConnectionConfig`, Connector SDK): no `xpath`; the GUI writes the block this way and it works.

```xml
<ConnectionOverride id="<connection id>">
  <field id="url" label="Connection URL" overrideable="true"/>
  <field id="className" label="Class Name" overrideable="true"/>
</ConnectionOverride>
```

Environment Extension values: `className` = `me.avogadro.mockjdbc.MockJdbcDriver`, `url` = `any`. The GUI also adds an
`<Extensions><ObjectDefinitions>` section with one `objectDefinition` per table the operations use; it is not needed
for the override. A connection with pooling on also needs `enablePooling` or `validationQuery` in the block, declared
the same way (see "Connector behaviour under the mock").

Values in `_params` are the `toString()` of the bound objects, so they depend on how the connector binds each
field: with `amount|double` in the header the connector binds a Double and `250` is captured as `250.0`.

## Counters and several scenarios

The `#n` counters and the step counter restart automatically for each new top-level execution (also across
Try/Catch continuations). Inside one execution, set `mockjdbc#RESET` to any non-blank value between scenarios: the
next statement restarts from `#1` and step 0, and the driver empties the property. Statements running in parallel
threads have separate counters.

## Scripts

```groovy
import com.boomi.execution.ExecutionUtil
ExecutionUtil.setDynamicProcessProperty("mockjdbc_customers", "id,segment\nC42,GOLD", false)
String written = ExecutionUtil.getDynamicProcessProperty("mockjdbc_orders_params")
```

Inside Boomi the driver is not registered in `DriverManager`: from a script use
`new me.avogadro.mockjdbc.MockJdbcDriver().connect("any", new Properties())`.

## Troubleshooting

| Symptom | Cause / fix |
|---|---|
| Query returns no rows | the SQL has a `QUERY_ID` and the mock uses the table name (or the reverse); property name not `mockjdbc_` + lower-case table; arrange path not run before the act path; CSV with `;` |
| `_params` empty | statement is a SELECT; the SQL has a `QUERY_ID` (read `mockjdbc_<id>_params`); schema-qualified write read without the schema (`mockjdbc_dbo.orders_params`); `#tmp` / `@rows` / quoted name with spaces (use `-- QUERY_ID:`); Database V2 procedure without signature; wrong name case in the Decision (use lower case) |
| Database V2 error 405 `Kindly select the IN clause check box ...` | query with `IN (...)`: enable the IN clause option of the operation (connector check, not the driver) |
| `SQLException` reading a procedure parameter | the parameter is IN, or not in the signature header |
| Real database contacted / connection error | extensions not applied: field not extensible, Legacy override without `xpath`, Test Extensions not filled, wrong environment |
| `ClassNotFoundException` for the driver | Custom Library not deployed on that runtime, or `aspectjrt` / `opencsv` missing |
| Old behaviour after an upgrade | old jar still loaded (jar locking): ask the user; local Atom: stop, delete old jars, start; cloud runtime: cannot be restarted nor its jars deleted (SKILL.md, "The library is not what the runtime runs") |
| NullPointerException in Database V2 | table header missing |
| Database V2 `_params` missing a field, no error | input field not in the header: Standard Insert/Update/Delete do not bind it, Dynamic Insert leaves it out |
| Database V2 "Keys Provided in Input Request is not matching the Request Profile" | Standard Get with an input field not in the header |
| Database V2 "isValid() returned false" | pooling on, no validation query: extend `enablePooling` = `false` or `validationQuery` = `SELECT 1` |
| Legacy CLOB / BLOB value empty in `_params` | stream setters ignored by mockjdbc 2.2.0: not assertable |
| `NumberFormatException` / date parse error | value does not match the getter: see CSV format |
| `SQLException: Invalid QUERY_ID` | ID with spaces, `?`, `#` or `,`, or empty: one word, e.g. `ecommerce.orders-ws.insert-order` |
| `-- QUERY_ID:` ignored | not on the first line |
| `UnsupportedOperationException` | JDBC method not implemented by mockjdbc: report it on the repository |
