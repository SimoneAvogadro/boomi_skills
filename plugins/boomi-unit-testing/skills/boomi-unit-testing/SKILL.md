---
name: boomi-unit-testing
description: Use when a Boomi process or subprocess needs a unit test, a test harness, a mock or a stub, when [UT] test processes are built, run again or extended to full coverage, when an environment must be chosen for unit tests, when the defects that unit tests found in the processes must be reported, tracked or fixed with non-regression tests, or when test deployments must be cleaned up - whatever connectors the process uses.
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

## The agentic workflow: three levels

1. **Build the unit tests**: one `[UT]` per scenario, with the connector skills (sections from "Principles" to "Switch
   the connections").
2. **Run them all, to full coverage** ("Running the tests"): iterate until every process in scope has the `[UT]`s it
   needs and all of them have run. A test with a bug is fixed; a defect of a process is **recorded**, not fixed, and
   the work goes on.
3. **Fix the processes** ("Fixing the processes"): report the defects, ask whether to track them and whether to fix
   them, then loop run → identify → fix → non-regression test until every defect that can be fixed is fixed.

Level 3 starts only after level 2 is complete, and only if the user agrees.

## Scope: unit tests, and testing in DEV

This skill covers **unit testing** only. The goal of a unit test is to make the execution of the `[S]` repeatable
and deterministic: same inputs, same mocks, same result at every run. Validating the SQL against the real database,
and everything else that only a real system can check, is the job of the DEV phase, not of the unit tests or of the
mocks.

Unit testing and testing in DEV are two separate phases, with different implications and handling. Find out which
situation applies, from the request and the workspace; when it is not clear, ask the user with AskUserQuestion,
together with the prerequisite questions:

| Situation | What the unit tests do | What stays open |
|---|---|---|
| **Processes already tested in DEV** (against the real systems) | capture the behaviour known to be right: the DEV runs are the reference, expected values can come from what DEV showed | little: the SQL has already met the real database |
| **Self-contained unit tests written before the first DEV run** | make the logic repeatable and deterministic | everything only a real system can check (SQL text and semantics, real types, constraints, connection settings) stays unverified until DEV: say so in the final answer |

In a full-agentic workflow the agent does all the work, following the user's indications, but this skill explains
only how to do unit testing. Whether and how to test in DEV is for the agent to agree with the user, outside this
skill.

## Arrange, Act, Assert

The `[UT]` follows the **Arrange-Act-Assert** pattern of unit testing (Bill Wake, 2001; the same idea as
Given-When-Then in BDD): prepare the inputs and the mocks, run the code under test once, check the outcome.

## Principles

1. **The process under test is not changed by its test.** Wherever possible the `[S]` runs in the `[UT]` exactly as
   it runs in production: same XML, same shapes, same connectors. Test data, mocks and checks live in the `[UT]`.
   The `[S]` is changed only when the user explicitly picks option 1 or 2 of the question below, chose a policy that
   asks for the change, or lets the agent fix the defects in level 3.
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

## When the `[S]` must change

Two cases lead to a change in the `[S]`:

- **A mock needs it**: a connector skill finds that a better test needs a small change (for the database: a
  `-- QUERY_ID:` comment in the SQL).
- **A test found a defect**: a `[UT]` fails and the cause is the `[S]`, not the test or the mock. Prove it first.
  Direct evidence is enough: the values the mock captured for that step, a stack trace that points at the component,
  or a comparison with a component of the same kind that works on the same runtime. Otherwise reproduce the failing
  step alone in a temporary experiment process (`[UT] Experiment - <what>`, same operation, same mock, inputs that
  differ only in the suspected cause), and read what the Companion says about that connector; the experiment process
  is part of the cleanup. In level 2 the defect is only recorded; the fixes are level 3.
- **Reading the code found a defect** that no test can show (a mock does not see it: the connector skill says
  which, for example SQL literals). Record it as "found by review", with the line and the part of the spec it
  breaks; its fix is checked by reading, not by a test.

Never make the change on your own: propose it (what, where, the value, and every component it adds or changes, such
as a new profile) and ask the user with AskUserQuestion, one question per change or one per group (up to four per
call):

1. **Yes, the agent does it.** The agent changes the `[S]`, pushes it and deploys it **only to the unit-test
   environment**. It tells the user that the `[S]` changed and that deploying it where it runs (production and the
   other environments) is part of their release; the agent never deploys there.
2. **Yes, the user does it, and the agent waits.** The agent stops, says exactly what to change and where, and waits
   for the confirmation. After it, the agent pulls the process again, checks the change, and only then goes on.
3. **No, the agent uses an alternative** that leaves the `[S]` as it is (the connector skill says which).

Put the trade-off in the question. For a defect, option 3 means leaving the `[UT]` red, which documents the defect.
For changes that a mock would need in every process (for the database, the QUERY_ID), a connector skill can ask the
user once for a **policy** instead, and record it in the file `.boomi-unit-testing` in the workspace directory, one
`key=value` per line: from then on the policy answers the question.

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

Create it in a folder named `Unit test`, inside the folder of the process under test. When that folder holds several
`[S]` with their tests, one folder per group: `Billing/Unit test - Get customer balance`,
`Billing/Unit test - Send invoice reminders`. The name is `[UT] ` + the name of the process under test **without** its
`[S] ` prefix + ` - <scenario>`: `[S] Scarica fatture` → `[UT] Scarica fatture - fattura duplicata`.

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
  Properties of the test. To get the documents the `[S]` returns, the Process Call lists its Return Documents shape
  (`<returnpaths childShapeName="<shape name of the Return Documents in the [S]>"/>`, Companion
  `references/steps/process_call_step.md`).
- **Check that the response exists before reading it**: on each return path of the Process Call, a Set Properties
  `PP_RETURNED_<PATH>` = `Y` (and the fields to check into `PP_ACTUAL_*`), and in path 3 a Decision per path ("the
  expected path returned? the others did not?") ending in an Exception. Otherwise an empty or broken response makes the
  shape that reads its fields fail in path 2 with a generic error, and the checks of path 3 never run.
- **A scenario where the `[S]` must fail**: an **application failure** (the `[S]` ends in an Exception by design,
  for example "Order not paid", a validation error, a record not found handled as an error) or a **technical
  failure** (an `SQLException` from the database, a connector error), when the connector skill gives a deterministic
  way to cause it. Wrap the Process Call in a Try/Catch; the catch path stores `meta.base.catcherrorsmessage` in a
  property (`PP_CAUGHT_MESSAGE`), and path 3 checks, each with a Decision that ends in an Exception:
  - **an exception was raised**: `PP_CAUGHT_MESSAGE` is not empty. Empty: the `[UT]` fails ("expected exception
    <expected message>, none raised"). A failure scenario that passes with no exception tests nothing;
  - **it is the expected one**: a wildcard or regex on the expected message (and on the type of error, when the
    message carries it). Another message: the `[UT]` fails ("expected <expected message> got {1}");
  - **no unexpected side effect**: no write captured by the mocks, no return path of the `[S]` taken that the
    scenario excludes.

  The Exception of the `[S]` is caught by the `[UT]`'s Try/Catch also with `abort="true"`. Without the Try/Catch the
  expected error turns the test red. Do not put the "none raised" Exception on the try path after the Process Call:
  the same Try/Catch would catch it.

  ```
  2 Act:     Message "Input ..." → Try/Catch
             ├ Try   → Process Call "[S] ..." → Stop (continue)
             └ Catch → Set Properties PP_CAUGHT_MESSAGE = meta.base.catcherrorsmessage → Stop (continue)
  3 Assert:  Decision "exception raised?"  (PP_CAUGHT_MESSAGE not empty)
             ├ false → Exception "expected exception <message>, none raised"
             └ true  → Decision "expected exception?"  (PP_CAUGHT_MESSAGE matches *<message>*)
                       ├ false → Exception "expected <message> got {1}"
                       └ true  → Decision "no write?" ... → Stop (continue)
  ```
- **A caller with no `[S]` prefix** (a batch process with a "No Data" start that calls the `[S]`): it can be tested
  the same way, with a Process Call from the `[UT]`, named `[UT] <caller name> - <scenario>`. Listener wrappers
  cannot run in test mode: check only that they call the `[S]` and wire every return path.
- **Assert**: one Decision per check. False → Exception (`stopsingledoc="false"`, so the whole execution ends in
  ERROR) whose message shows expected and actual value (`{1}`).
- **Expected values on the first run**: the first Decision that fails hides the actual values of the later checks.
  When the exact values are not known, add a temporary Notify at the start of path 3 that logs every value the
  checks read, run once, check that the values are right, set them as expected, and remove the Notify. A value
  hidden behind a failure stays a guess: keep the Notify until it has been seen, and when it differs from the guess,
  correct the expected value as a bug of the test and record it.
- One scenario per `[UT]` process is the default.

## Switch the connections (only for the test)

1. In the `[UT]` process Extensions → Connection Settings: make extensible every field that the connector skill lists,
   always all of them. Extensions are declared on the process that is deployed and run (the `[UT]`) and apply to the
   connections of the subprocesses it calls. Copy the `ConnectionOverride` block from the connector skill or from a
   pulled process that has it. Connectors with their own settings (for example Database Legacy) need the `xpath` of
   each field, otherwise the override is silently ignored (Companion error reference, Issue #31); connectors built on
   the Connector SDK (`GenericConnectionConfig`, for example Database V2) have no `xpath`, and the block the GUI
   writes is valid as it is. No block to copy: create the `[UT]`, ask the user to declare the fields once in the GUI
   (process Extensions → Connection Settings → the connection → tick the fields → OK → Save), then pull it.
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

Level 2: build and run until the set of tests is complete. Iterate:

1. **Coverage**: for every `[S]` in scope, list what its tests must cover, **happy flows and failure flows**: every
   path of its Decision, Route and Branch shapes, every connector operation (each read with data and with no data,
   each write checked), what the `[S]` returns, and the failure paths:
   - **application failures**: every Exception the `[S]` raises on purpose (validation, "Order not paid", not found
     handled as an error);
   - **technical failures**: every error the `[S]` handles from a connector (Try/Catch around a connector step, error
     routes), for example an `SQLException` or a connection error.

   Each failure is a `[UT]` as in "A scenario where the `[S]` must fail". A technical failure that the connector skill
   gives no deterministic way to cause is a **coverage gap**: list it in the final answer, do not invent a mechanism.
   Plan one `[UT]` per scenario until the list is covered.
2. **Build and run** the `[UT]`s, all of them, on the unit-test environment.
3. **Classify every failure**:
   - **bug in the test** (wrong mock data, wrong expected value, a check on the wrong key): fix the `[UT]`, run it
     again;
   - **defect of the process** (proved as in "When the `[S]` must change"): leave the `[UT]` red, record the defect
     (`[S]`, failing `[UT]`, expected vs actual, cause, proposed fix) in the defect list, and **go on** building the
     other tests. Do not fix the `[S]` at this level.
4. Back to 1 until the coverage list is complete and every `[UT]` has run.

Keep the defect list in the session, and in a file of the workspace (`unit-test-defects.md`) when the work spans
sessions. The tests run on a unit-test environment chosen once (prerequisite), and what the agent deploys for them
must not stay behind afterwards (cleanup).

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

**Gather every prerequisite question first.** The environment choice, the checks of the connector skills (libraries,
policies), whether the processes were already tested in DEV (when it is not clear, see "Scope") and any manual step
for the user: collect them all and ask them together, before the first write to the
account, so the user is interrupted once.

Several of the calls below have no Companion script. Make them through `boomi_api` of the Companion's
`scripts/boomi-common.sh` (`load_env`, `build_api_url`), **read-only** (queries and GETs); never write this way.
Bodies that work (an empty `and` group is rejected with HTTP 400):

| Call | Body |
|---|---|
| `POST Environment/query` | `{"QueryFilter":{"expression":{"operator":"LIKE","property":"name","argument":["%"]}}}` |
| `POST EnvironmentAtomAttachment/query` | `{"QueryFilter":{"expression":{"operator":"EQUALS","property":"environmentId","argument":["<env id>"]}}}` |
| `POST DeployedPackage/query` | `{"QueryFilter":{"expression":{"operator":"and","nestedExpression":[{"operator":"EQUALS","property":"environmentId","argument":["<env id>"]},{"operator":"EQUALS","property":"active","argument":["true"]}]}}}` |
| `POST ComponentMetadata/query` (name of a component id) | `{"QueryFilter":{"expression":{"operator":"and","nestedExpression":[{"operator":"EQUALS","property":"componentId","argument":["<id>"]},{"operator":"EQUALS","property":"currentVersion","argument":["true"]}]}}}` |

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
     `environmentId`) returns a download `url` on `platform.boomi.com`, not on the API host; `GET` that URL as it is,
     with the same credentials (retry while it is not ready), to
     get a CSV with one row per deployed connection and process: `ENVIRONMENT_ID`, `ENVIRONMENT_CLASS`,
     `CONTAINER_NAME`, `COMPONENT_ID` (the connection), `USED_IN_PROCESS_ID`, `USED_IN_PROCESS_NAME`. The connection
     is not in the CSV for that environment: no conflict. The first line of the CSV carries the report time, which
     can be earlier than the latest deployments: for those, list the packages deployed on the environment after that
     time (`POST DeployedPackage/query`) and compare their `componentId`s with the processes that use the connection
     (`boomi-component-search.sh --related-to <connection id>`).

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
   or components deployed by the agent, experiment processes.
3. **When the work is done** (level 2 complete and, if the user wanted it, level 3; every `[UT]` green or red only for
   a recorded defect): undeploy what the agent deployed and is not
   in the baseline (`boomi-undeploy.sh --by-component <file>`; a component that only travels inside a process package
   has no deployment of its own). A baseline component that the agent redeployed with a new version stays deployed:
   tell the user that the version on the environment changed.
4. **Long chain of sessions**: when more development-test-improvement rounds are expected (open work, the user said
   so, the feature is only partly built), ask the user before undeploying: keep the test deployments for the next
   session, or remove them now. Kept deployments are listed in the final answer, so the next session can clean them.
   After an undeploy, the next session deploys the `[UT]`s again before running them (the extension values stay on
   the environment; the declarations come back with the deploy).
5. **Check**: query the active deployments of the environment again and compare them with the baseline.
6. **Extension values stay**: the test values on the unit-test environment are not reverted (the next tests need
   them).
7. **Final answer of the session**, always:
   - the extension values left: environment, connection, fields and values;
   - every `[S]` and component changed, with its new version, the processes that bundle it (by name: `--related-to`
     gives the ids, `ComponentMetadata/query` the names) and where the old version still runs (its release is the
     user's);
   - the components to delete by hand (experiment processes): undeployed, but the scripts cannot delete components;
   - the `[UT]`s that are order-dependent or left red, and why;
   - the coverage gaps: the failure paths with no `[UT]` (for example technical failures that the mock cannot
     cause), and why;
   - for unit tests written before the first DEV run: what DEV must still verify (SQL text and semantics, real types,
     constraints, connection settings), with the findings "found by review".

## Fixing the processes (level 3)

This section is the loop and its reports only. How to change, push and deploy a process, and what to do with an
unknown connector or platform behaviour, is the Companion's (`bc-integration:boomi-integration`, including its
problem-solving guide).

**Report and ask.** When level 2 is complete, report every defect of the defect list: `[S]`, failing `[UT]`, expected
vs actual, cause, proposed fix and the components it touches. Then ask the user with AskUserQuestion:

- **track them in a bug tracker?** Only when the session has one: look first at the connectors and MCP servers
  available (Jira, GitHub issues, Azure DevOps...). None: do not propose it, the defect list is the record. Create
  nothing before the yes: it is a write to an external system;
- **may the agent fix them?** all of them, some of them, or none (the `[UT]`s stay red and document them).

**A project that already has a tracker**: before the first issue, interview the user (AskUserQuestion, a few
questions at a time) to fit its standards, and read a few existing issues to check the answers: project, issue type,
mandatory fields, components and labels, title and description format, workflow states and their meaning, who is
assignee and reporter, how a fix is linked (comment, field, link to a version), when an issue may be closed. Record the
answers in `.boomi-unit-testing` (`tracker.*` lines) so the next sessions follow them without asking again.

**Keep the tracker up to date** for every issue: move it through the workflow as the work goes (for example "in
progress" when the fix starts, "resolved" or the state the project uses when its tests are green), and comment the
fix applied (components, versions, tests that prove it) or, when the agent cannot fix it, why and what is needed.
Never move an issue to a state the interview reserved to people (for example "closed" after a review).

**The loop**, for each defect the user let the agent fix:

1. **Fix** the `[S]` (Companion for the XML), push it, deploy it **only to the unit-test environment** (redeploy the
   `[UT]`s that bundle it). When there are several ways to fix it, prefer the one that keeps the expectations of the
   tests; when the fix itself changes an expected value, say so in the defect record.
2. **Run** its failing `[UT]`: it must turn green. When it now fails on another check, that is the next defect
   (hidden by this one, or new): record it, with the evidence from the log, and go on with the loop.
3. **Add a non-regression `[UT]`** for the defect, when the failing test does not already pin it down:
   `[UT] <process> - regression <defect>` (with the issue key when there is one), the scenario that showed the defect.
4. **Run all the `[UT]`s** of that `[S]` and of the processes that call it: a fix must not break another test.
5. **Describe the fix** (what changed, which components, which versions, which tests prove it) in the issue of the
   tracker when there is one, and move it to the next state; otherwise in the defect list.
6. Next defect. New defects found by these runs go into the defect list and into the same loop (they are new: ask
   the user before fixing them only if the earlier answer did not cover them).

A defect is **not fixable by the agent** when the fix needs information or a decision the agent does not have (an
unclear requirement, the behaviour of an external system, a change to a shared component), or when three or four
attempts did not fix it (as in the Companion's problem-solving guide): record why (in the issue too, with a comment)
and go on with the others.

**Final report**, when no fixable defect is left: the defects fixed (fix, `[S]` versions, non-regression `[UT]`,
issue), the defects not fixed (why, what is needed from the user), and the items of "Final answer of the session"
(cleanup). Every fixed `[S]` is deployed only on the unit-test environment: its release is the user's.

## Common mistakes

| Mistake | Effect | Fix |
|---|---|---|
| Branch paths in the wrong order | mock data not yet set when the `[S]` runs, or check run before the `[S]` | path 1 arrange, path 2 Process Call, path 3 assert |
| A stub switch in the `[S]` (Decision on `PP_STUB` → stub subprocess instead of the connector) | test code shipped to production; the real connector step is never exercised | `[S]` unchanged, connection switched by extensions |
| Hand-written stub subprocesses that record what was "sent" | the connector step and its parameters are not tested | a mock behind the real connector (connector skill) |
| A change to the `[S]` made for the test without asking | the test no longer runs the production process unchanged | the question with three options (or the user's policy) first |
| Test "passes" by reading Notify output | needs a human, not repeatable | Decision + Exception |
| Extension field without `xpath` on a connector with its own settings (Database Legacy...) | the real system is used | copy the block from the connector skill or a pulled component (SDK connectors such as Database V2 have no `xpath`: that is fine) |
| Test values set on an environment shared with other processes | those processes switch to the mock too | choose the unit-test environment first (prerequisite) |
| Fields of the `[S]` response read without checking it exists | path 2 fails with a generic error, path 3 never runs | Decision "response returned?" right after the Process Call |
| A red `[UT]` "fixed" by changing the expected value | the defect of the `[S]` is hidden | prove the cause (experiment process), then the question with three options |
| `[UT] [S] Scarica fatture - ...` | double prefix | `[UT] Scarica fatture - ...` |
| A defect fixed during level 2 | the set of tests stays incomplete, the user never chose | record it and go on; fixes are level 3, after asking |
| Issues created in the bug tracker without asking | writes to an external system the user did not approve | ask first; with an existing project, interview the user on its standards |
| A bug tracker proposed with no connector or MCP for it in the session | the agent cannot keep it updated | propose it only when a tool for it is available |
| Issue left in its first state after the fix, or with no comment | the tracker no longer tells the truth | move it through the workflow and comment the fix, or why it could not be fixed |
| A fix verified only by its own `[UT]` | it can break another path of the `[S]` or a caller | run all the `[UT]`s of the `[S]` and of its callers |
| Only happy flows tested | the Exceptions and error paths of the `[S]` are never run | coverage of application and technical failures; a gap that cannot be tested goes in the final answer |
| A `[UT]` that expects an exception passes when none is raised, or when another one is raised | the failure path is not tested, the test is green by chance | Decision "exception raised?" and Decision on the expected message, each ending in an Exception |
| "None raised" Exception on the try path after the Process Call | the `[UT]`'s own Try/Catch catches it | set `PP_CAUGHT_MESSAGE` in the catch path, check it in path 3 |
| Unit tests written before DEV reported as a validation of the SQL | the user believes the SQL met the real database | say what DEV must still verify; SQL validation belongs to DEV |
