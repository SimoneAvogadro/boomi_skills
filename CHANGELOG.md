# Changelog

Each plugin has its own version (in its `.claude-plugin/plugin.json`) and its own section. Releases are tagged
`<plugin>-<version>`. Format after [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow
[Semantic Versioning](https://semver.org/).

## boomi-unit-testing

### 1.2.0 - 2026-10-29

- Database operations: technical failures are caused with mockjdbc error resources (mockjdbc 2.3.0, beta jars from
  `2.3.0-b1`): a statement fails with the `SQLException` class, SQLState and error code of a CSV, chosen per QUERY_ID,
  per n-th use of a name or per bound values. `mockjdbc_<name>_error` proves the injection fired and `_params` says
  what the `[S]` tried to write. With an older jar the failure paths stay a coverage gap.
- A connection lost in the middle of the `[S]`: listed for every `[S]` with two or more database steps, caused with an
  error resource with SQLState `08` on the first failing step and on every later step that must fail.
- Database V2: the error never goes on the plain table name or procedure name (they keep the header or the signature).
  Coverage gap stated: a Try/Catch for "database down" around a step with `returnApplicationErrors="true"` cannot be
  reached (observed on an Atom with 2.3.0-b1: the error never reaches a Try/Catch, also with SQLState `08`).
- What the `[UT]` checks, from runs with 2.3.0-b1: a Database V2 error document on `errorMessage` (single quotes are
  removed from a write's message) and on `errorCode` only for writes (a Standard Get answers 405); the Legacy Try/Catch
  message with a wildcard on a distinctive part (a Get adds a prefix); a `[S]` with its own Try/Catch is checked on what
  it returns, routes or logs.
- Order of the writes: a failed first write is checked with an error resource. Observed: a document error (Legacy, a
  Set Properties error) in a Branch path skips every later path of that Branch for all documents, so in a
  multi-document `[S]` the good documents lose their later-path writes; with Database V2 error documents the later paths
  run. `mockjdbc-reference.md`: new section "Errors (fault injection)". Strategy skill: the lost connection named
  among the technical failures.

### 1.1.1 - 2026-10-25

- Read-only platform queries that have no Companion script: one `boomi_api` example to copy; never a hand-written
  `curl`; one auth error (401/403) stops the work.
- The environment `BOOMI_ENVIRONMENT_ID` in `.env` points to is told to the user before anything else; changing it
  needs their answer; the original is recorded in `.boomi-unit-testing` and restored in the cleanup, and the final
  answer says so.
- New section "Talking to the user": short, focused messages for a Boomi specialist.
- An `[S]` the agent builds in the task is fixed at once (test-first welcome); levels and questions apply to the
  processes that existed before the task.
- The unit-test environment is saved in `.boomi-unit-testing`; later sessions only check conflicts.
- Level 3: answers already given (the request, `CLAUDE.md`, `.boomi-unit-testing`) count; tracker and `fix-defects`
  policies saved; the tracker's standards are read before asking.
- The read-only API calls of the skill need no "stop and discuss".
- Database operations: a missing mockjdbc library blocks only deploying and running, not the rest of the work.

### 1.1.0 - 2026-10-24

- Scope section: unit tests make the `[S]` repeatable and deterministic; what only DEV can verify (SQL text and
  semantics, real types, constraints) is listed in the final answer.
- Coverage of happy and failure flows: application and technical failures, `[UT]`s that expect an exception check
  "none raised" and "a different one"; coverage gaps reported, never invented mechanisms.
- Level 3: a red-to-green `[UT]` is the non-regression test, a new one only for an unchecked variant; pull after
  pushing a fix, version in the defect record.
- Database operations: connector behaviour under the mock from static analysis of Database Legacy 20.03.0 and
  Database V2 0.0.73 (error handling, binding from the mock header, response fields, vendor branches, pooling,
  CLOB/BLOB, batching); Database V2 errors returned as output documents (`returnApplicationErrors`); no fault
  injection in mockjdbc 2.2.0.
- Database operations: an older mockjdbc jar is a request to upgrade, not a stop; numeric captured parameters
  compared by the bound type; review of the order of the writes.

### 1.0.0 - 2026-10-22

- Three-level agentic workflow: build the tests, run them to full coverage recording the defects, then report, ask
  and fix with non-regression tests.
- Defects found by review (what a mock cannot see), proof by direct evidence or an experiment process, expected
  exceptions with Try/Catch, return-path checks, callers without `[S]`.
- Prerequisite questions gathered before the first write; read-only query bodies; licensing report for the
  connection conflicts; cleanup with a baseline and a final answer.
- Bug tracker only when a connector or MCP for it is available; interview on the project's standards; issues kept up
  to date.
- `[UT]` name without the `[S]` prefix of the tested process; one `Unit test` folder per group.
- Database operations: QUERY_ID policy asked once per workspace (`minimal-changes`, `structured-agent`,
  `structured-user`) and stored in `.boomi-unit-testing`; no question when the table keys cover the operation; every
  SQL read against the spec during the inventory; jar locking after an upgrade; `ConnectionOverride` blocks for
  Legacy (with `xpath`) and Database V2 (without).

### 0.4.0 - 2026-10-22

- Split into two skills: `boomi-unit-testing` (the strategy, for any connector: the `[S]` unchanged, each connector
  mocked by its own skill) and `boomi-unit-testing-database-operations` (mockjdbc 2.2.0 for Database Legacy and V2).

### 0.3.0 - 2026-10-22

- Principle: the process under test is not changed by its test; the QUERY_ID question with three options.
- Mock keys by table, table + bound values, occurrence, step (backups labelled order-dependent).
- mockjdbc 2.2.0 rules: first `FROM`, quoted and schema-qualified names, stored procedures with signatures.
- Running the tests: verdict from the status, logs for diagnosis; choice of a unit-test environment without
  connection conflicts; cleanup of the test deployments.

### 0.2.0 - 2026-10-19

- `-- QUERY_ID: <project>.<service>.<step>` first, table names as the fallback (mockjdbc 2.1.0+).

### 0.1.2 - 2026-10-16

- Always extend Driver Type, Class Name and Connection URL; verify the extensions after each `set`.

### 0.1.1 - 2026-10-16

- Check the mockjdbc Custom Library (component and deployment) before the first test; manual setup from mockjdbc's
  FEATURES.md, since Boomi has no API to upload jars.

### 0.1.0 - 2026-10-13

- First release: `[UT]` processes that call the `[S]` under test, database mocked with mockjdbc, Decision + Exception
  checks on the captured writes.

## boomi-conventions

### 0.2.0 - 2026-10-25

- `[UT]` name: the tested process's name without its `[S]` prefix, then ` - <scenario>`.
- Priority stated: Boomi Companion < these conventions < project or customer skills and the workspace `CLAUDE.md`.
- Naming hook only in a Boomi workspace (`active-development/`, or a `.env` with `BOOMI_` variables) and only on
  Boomi component XML files.
- `DPP_` / `DDP_` names already used by a component of the workspace are not new; a name fixed outside the workspace
  goes to `.boomi-naming-allow` by the agent, which tells the user.
- Session context names the plugin's conventions and the priority order.

### 0.1.0 - 2026-10-13

- First release: `PP_` / `D_` prefixes, `[S]` and `[UT]` process names, `Unit test` folder; session-start context
  and a pre-write naming guard as plugin hooks.

## boomi-companion-known-bugs

### 0.1.0 - 2026-10-25

- First release, against Boomi Companion 1.0.87: CB-1 Database V2 Standard Update uses `Type`, not `UpdateType`;
  CB-2 SDK connectors declare connection overrides without `xpath`; CL-1 to CL-4 script limitations (extensions on
  another environment, environment and deployment queries, deleting components, sync state of pulls elsewhere).
