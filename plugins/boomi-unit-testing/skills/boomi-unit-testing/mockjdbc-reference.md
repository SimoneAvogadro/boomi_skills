# mockjdbc reference for Boomi tests

Source: https://github.com/SimoneAvogadro/mockjdbc (README, TUTORIAL.md, FEATURES.md section 11). Written for
mockjdbc 2.0.x; check the CHANGELOG of the repository when a newer version is installed.

## Contents
- Installation on the runtime
- How a statement finds its mock data
- Captured parameters (assertions)
- CSV format
- Database V2 connector
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
2. `-- TESTCASE: <name>` as the **first line** of the SQL (wins over the table name);
3. table name after `FROM`;
4. stored procedure after `EXEC`, `EXECUTE`, `CALL`, `{call ...}`, `{? = call ...}`;
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
| `-- TESTCASE: t_014a` + any SQL | `mockjdbc_t_014a` |
| `EXEC get_rate ?` | `mockjdbc_get_rate` |

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
| `EXEC upd_status ?, ?` / `{call upd_status(?, ?)}` | `mockjdbc_upd_status_params` |
| `-- TESTCASE: t_014a` + any statement but a SELECT | `mockjdbc_t_014a_params` |
| statement on a step resource | `mockjdbc_##step<n>_params` |

- `_params` holds the **last** write; each write is also in `_params#1`, `_params#2`... (counter shared with the
  queries on the same name: a SELECT on `orders` then an INSERT into `orders` is occurrence 1 then 2).
- Batches: one capture per parameter set.
- A parameter not set is left empty (`,a`).
- The table name after `INSERT INTO` / `UPDATE` / `DELETE FROM` is matched with **letters only**: `order_lines` or
  `t2` are not captured by name. Use a `-- TESTCASE:` comment for them (in the operation's SQL).
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
- Default date formats (`SimpleDateFormat`, JVM locale and time zone): date `dd-MMM-yy` (`17-MAY-12`; with an
  Italian locale `17-MAG-12`), time `HH:mm` (seconds dropped), timestamp `yyyyMMdd HHmmss.SSS`
  (`20120517 143000.000`, milliseconds required). The same formats render date parameters in `_params`.

## Database V2 connector

The connector reads the metadata (`getColumns`) before running operations it builds from a table definition
(Standard Get/Insert/Update/Delete, Dynamic Get/Insert...):

- **define every table the operation writes to or filters on**, even header only, e.g. `mockjdbc_orders` =
  `order_id|integer,customer_id,segment,amount|double` (types make numbers bound as numbers);
- **every field of the input document must be a column of that header**, otherwise NullPointerException.

Overrides: the legacy connector needs Driver Type `Custom`, Class Name and Connection URL; Database V2 has no
driver type, only `className` and `url`. Take the `xpath` of each override from a process where the override was
configured in the GUI and pulled (Companion `process_extensions.md`).

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
| Query returns no rows | property name not `mockjdbc_` + lower-case table; arrange path not run before the act path; CSV with `;` |
| `_params` empty | statement is a SELECT; table name with digits/underscore (use `-- TESTCASE:`); wrong name case in the Decision (use lower case) |
| Real database contacted / connection error | extensions not applied: field not extensible, override without `xpath`, Test Extensions not filled, wrong environment |
| `ClassNotFoundException` for the driver | Custom Library not deployed on that runtime, or `aspectjrt` / `opencsv` missing |
| Old behaviour after an upgrade | old jar still loaded: stop Atom, delete old jars, restart |
| NullPointerException in Database V2 | table header missing, or input field not in the header |
| `NumberFormatException` / date parse error | value does not match the getter: see CSV format |
| `UnsupportedOperationException` | JDBC method not implemented by mockjdbc: report it on the repository |
