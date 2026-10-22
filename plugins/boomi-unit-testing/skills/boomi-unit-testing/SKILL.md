---
name: boomi-unit-testing
description: Use when a Boomi process or subprocess needs a unit test, a test harness, a mock or a stub, when [UT] test processes are built, run again or extended, when an environment must be chosen for unit tests, or when test deployments must be cleaned up - whatever connectors the process uses.
---

# Boomi unit testing (strategy)

## Overview

A unit test is a **separate `[UT]` process** that prepares the data, calls the `[S]` subprocess under test
**unchanged** with a Process Call, and checks the result with Decision shapes that end in an **Exception** when
the check fails. The test passes when the execution completes, fails when it ends in error.

**The goal**: the processes that go to production never contain logic of the kind "if I am in a test, then...".
Every external system the `[S]` talks to (database, JMS, file system, HTTP...) is replaced in the test by switching
its connection with extensions, and each connector, or condition, is mocked by **its own skill**:

| Connector | Skill |
|---|---|
| Database Legacy, Database V2 (SQL, stored procedures) | `boomi-unit-testing-database-operations` |

Load the skill of every connector the `[S]` uses. A connector with no skill: tell the user, and build its part of the
test with your own Boomi knowledge, with the rules of this skill (the `[S]` unchanged, every check a Decision that
ends in an Exception). Everything else in the `[UT]` (input documents and properties, the logic, the documents the
`[S]` returns) is built the same way.

**REQUIRED BACKGROUND:** `bc-integration:boomi-integration` for the XML of each shape and the push/deploy/execute
scripts. Names (`[S]`, `[UT]`, `PP_`, `D_`, the `Unit test` folder) follow `boomi-coding-conventions`, or the
project's own conventions when there are any.

## Which skill wins

From the lowest priority to the highest:

1. **Boomi Companion** (`bc-integration:boomi-integration`): the same for everyone who uses Boomi.
2. **These skills** (unit testing, conventions): specialised for unit testing with agents, independent of the project.
3. **Project or customer skills** (and the workspace `CLAUDE.md`): when one covers the same topic (naming, a unit-test
   strategy agreed by contract...), it wins over everything else.

## Arrange, Act, Assert

The `[UT]` follows the **Arrange-Act-Assert** pattern of unit testing (Bill Wake, 2001; the same idea as
Given-When-Then in BDD): prepare the inputs and the mocks, run the code under test once, check the outcome.

## Principles

1. **The process under test is not changed by its test.** Wherever possible the `[S]` runs in the `[UT]` exactly as
   it runs in production: same XML, same shapes, same connectors. Test data, mocks and checks live in the `[UT]`.
   The `[S]` is changed only when the user explicitly picks option 1 or 2 of the question below.
2. **Arrange and Assert are outside the `[S]`.** The `[UT]` prepares the mocks before the Process Call and checks what
   they captured after it.
3. **Fidelity**: the only difference between production and test is the connections switched by extensions in the
   test run.

## Design the process so it can be tested

- Put the logic in an `[S]` subprocess with a passthrough start; a listener (WSS, JMS, FSS...) is only a thin
  wrapper (listener → Process Call `[S]` → Return Documents). Listener processes cannot run in test mode.
- The `[S]` takes everything it needs as input documents, `PP_` / `D_` properties or connections: no hardcoded
  test data, no "if test" branches inside it. Test data and checks live in the `[UT]` process only.
- Every connection the `[S]` uses is a real component that the test can override with extensions.
- Do not add a mock Message shape in the `[S]` main path, nor a test branch driven by a property (the Companion
  "temporary Message" and `DPP_FROM_WRAPPER` patterns): test code inside the `[S]` is forgotten and reaches production.

## When a mock needs a change in the `[S]`

A connector skill can find that a better test needs a small change in the `[S]` (for the database: a `-- QUERY_ID:`
comment in the SQL). Never make it on your own: propose it (what, where, the value) and ask the user with
AskUserQuestion, one question per change or one per group (up to four per call):

1. **Yes, the agent does it.** The agent changes the `[S]`, pushes it and deploys it **only to the unit-test
   environment**. It tells the user that the `[S]` changed and that deploying it where it runs (production and the
   other environments) is part of their release; the agent never deploys there.
2. **Yes, the user does it, and the agent waits.** The agent stops, says exactly what to change and where, and waits
   for the confirmation. After it, the agent pulls the process again, checks the change, and only then goes on.
3. **No, the agent uses an alternative** that leaves the `[S]` as it is (the connector skill says which).

Put the trade-off in the question. The connector skill says when option 3 is the one to mark **(Recommended)**.

## Connector skills: what each one provides

A skill that mocks a connector gives, for that connector:

1. the **inventory** of its operations in the `[S]` and in the subprocesses it calls;
2. the **changes to the `[S]`** that would help, to propose with the question above, and the alternatives;
3. the **connection fields** to override and their test values;
4. the **runtime prerequisites** (libraries, components) and what to do when they are missing;
5. the **Arrange** part: how to give the mock its data;
6. the **Assert** part: what the mock captures and how to compare it;
7. its common mistakes.

## The `[UT]` process

Create it in a folder named `Unit test`, inside the folder of the process under test (`Unit test - <description>` if
the folder has several groups of tests), named `[UT] <process under test> - <scenario>`.

```
[UT] <process under test> - <scenario>
Start (No Data)
└─ Branch  (Boomi runs the paths one after the other, in order)
   1 Arrange: mock data of each connector (connector skills), input properties → Stop (continue)
   2 Act:     Message "Input ..." (the document the [S] receives) → Process Call "[S] ..." → Stop (continue)
   3 Assert:  Decision "<what is checked>?"
              ├ true  → next Decision ... → Stop (continue)
              └ false → Exception "<check>: expected <value> got {1}"
```

- **Act**: the input document of the `[S]` comes from a Message shape in the `[UT]` (the execution API cannot inject
  documents). Call the `[S]` with a Process Call (`wait="true"`, `abort="true"`): it shares the Dynamic Process
  Properties of the test.
- **Assert**: one Decision per check. False → Exception (`stopsingledoc="false"`, so the whole execution ends in
  ERROR) whose message shows expected and actual value (`{1}`). When unsure of the exact value, run the test once,
  read the actual value in the Exception message, and set it as expected only after checking that it is right.
- One scenario per `[UT]` process is the default.

## Switch the connections (only for the test)

1. In the `[UT]` process Extensions → Connection Settings: make extensible every field that the connector skill lists,
   always all of them. Extensions are declared on the process that is deployed and run (the `[UT]`) and apply to the
   connections of the subprocesses it calls. Declare them in the GUI or start from a pulled process that has them:
   each override needs its connector-specific `xpath`, otherwise it is silently ignored (Companion error reference,
   Issue #31).
2. Run it:
   - **GUI**: Test → Test Extensions → Connection Settings → untick "Use connection component value" for those
     fields and enter the test values.
   - **Automated** (Companion scripts): deploy the `[UT]` to the unit-test environment (below), set the values as
     Environment Extensions there (`boomi-extensions.sh`), run `boomi-test-execute.sh --process-id <[UT] id>`.
   - **After every `set`, `get` again**: each field must show the value with `useDefault: false`. The platform can
     accept a `set` and keep the default without any error (seen on a field added to the declarations by a redeploy;
     once saved in the GUI, later API writes work). A field still at `useDefault: true`: **stop**, ask the user to
     set it once in Manage → Environment Extensions of the test environment (untick "Use connection component
     value"), then `get` again before running the test. Running with a field at its default reaches the real system.
3. Never set test values on an environment where real processes run.

## Running the tests

The tests run again and again (build, run, fix, run) until every process is complete and every test passes with
adequate coverage. They run on a unit-test environment chosen once (prerequisite), and what the agent deploys for
them must not stay behind afterwards (cleanup).

**Verdict from the status, diagnosis from the logs.** The checks are Decisions in the `[UT]` that end in an
Exception: the status of the execution (`COMPLETE` or `ERROR`) and the Exception message (expected vs actual) are the
result, with no log to download, which keeps each run fast. The process log is still the tool to understand why a
`[UT]` fails when the message is not enough (a connector error, a mock that found no data, a path not taken):
download it (`boomi-execution-query.sh --execution-id <id> --logs`) for the failed runs, not for every run.

### Prerequisite: choose the unit-test environment

An Environment Extension value on a connection applies to that connection in the whole environment: every process
deployed there that declares those fields extensible takes the environment value. On an environment shared with other
uses (for example the same environment for unit tests and for user acceptance tests, "collaudo"), switching a
connection to a mock switches the other processes that use it as well. So, before the first deploy:

1. **Candidates**: list the environments of the account (`POST Environment/query`) and keep those classified `TEST`
   with a runtime attached (`POST EnvironmentAtomAttachment/query`). A `PROD` environment is never a candidate.
2. **Connections**: collect the connections the `[UT]` will override (those of the `[S]` and of the subprocesses it
   calls).
3. **Conflicts**, for each candidate and each of those connections, with read-only calls (`GET
   EnvironmentExtensions/<environmentId>`; `boomi-extensions.sh get` reads only `BOOMI_ENVIRONMENT_ID`):
   - the connection already has extension values on the environment (a field with `useDefault: false` that is not
     a test value): someone uses it with a real system there;
   - the connection is deployed there in a process that is not a `[UT]`: the test values would switch it too.
     One call covers every environment: `POST ConnectionLicensingReport` (body `{}`, or a `QueryFilter` on
     `environmentId`) returns a download `url`; `GET` it with the same credentials (retry while it is not ready) to
     get a CSV with one row per deployed connection and process: `ENVIRONMENT_ID`, `ENVIRONMENT_CLASS`,
     `CONTAINER_NAME`, `COMPONENT_ID` (the connection), `USED_IN_PROCESS_ID`, `USED_IN_PROCESS_NAME`. The connection
     is not in the CSV for that environment: no conflict. The first line of the CSV carries the report time, which
     can be earlier than the latest deployments: for those, also check `POST DeployedPackage/query` on the
     environment for packages deployed after that time.

   A candidate with neither is free; test values already set by earlier unit tests are not a conflict.
4. **Choice**: show the user the candidates and what was found on each, and ask with AskUserQuestion which one to use
   (a free one recommended). Only one candidate, and it has conflicts (or none at all): **stop**, explain the
   conflict (which connection, which processes or values) and agree with the user how to go on, for example a new
   `TEST` environment with its own runtime (created by the user), or runs from the GUI with Test Extensions, which
   apply to that run only. Never set test values on a connection with a conflict.
5. The Companion scripts deploy and write extensions on `BOOMI_ENVIRONMENT_ID`: if the chosen environment is another
   one, ask the user to change it in the workspace `.env` (or to let the agent do it) before the first deploy.

### Cleanup

1. **Baseline, before the first deploy of the session**: list what is already active on the test environment
   (`POST DeployedPackage/query` with `environmentId` and `active` = `true`, as in `boomi-undeploy.sh --by-component`)
   and keep the `componentId`s. What is in the baseline is never undeployed by the agent.
2. **Track every deploy** the agent makes for the tests: `[UT]` processes, `[S]` deployed on their own, mock libraries
   or components deployed by the agent, components made for an experiment.
3. **When the work is done** (all processes complete, all tests passing): undeploy what the agent deployed and is not
   in the baseline (`boomi-undeploy.sh --by-component <file>`; a component that only travels inside a process package
   has no deployment of its own). A baseline component that the agent redeployed with a new version stays deployed:
   tell the user that the version on the environment changed.
4. **Long chain of sessions**: when more development-test-improvement rounds are expected (open work, the user said
   so, the feature is only partly built), ask the user before undeploying: keep the test deployments for the next
   session, or remove them now. Kept deployments are listed in the final answer, so the next session can clean them.
5. **Extension values stay**: the test values on the unit-test environment are not reverted (the next tests need
   them), but the final answer of the session always lists them: environment, connection, fields and values.

## Common mistakes

| Mistake | Effect | Fix |
|---|---|---|
| Branch paths in the wrong order | mock data not yet set when the `[S]` runs, or check run before the `[S]` | path 1 arrange, path 2 Process Call, path 3 assert |
| A stub switch in the `[S]` (Decision on `PP_STUB` → stub subprocess instead of the connector) | test code shipped to production; the real connector step is never exercised | `[S]` unchanged, connection switched by extensions |
| Hand-written stub subprocesses that record what was "sent" | the connector step and its parameters are not tested | a mock behind the real connector (connector skill) |
| A change to the `[S]` made for the test without asking | the test no longer runs the production process unchanged | the question with three options first |
| Test "passes" by reading Notify output | needs a human, not repeatable | Decision + Exception |
| Extension field without `xpath` | the real system is used | declare the override from the GUI / a pulled component |
| Test values set on an environment shared with other processes | those processes switch to the mock too | choose the unit-test environment first (prerequisite) |
