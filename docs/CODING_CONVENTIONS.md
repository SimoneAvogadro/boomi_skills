# Boomi coding conventions

This document explains, for people, the naming rules that the `boomi-coding-conventions` skill applies when
Claude Code builds Boomi components. The skill ([SKILL.md](../plugins/boomi-conventions/skills/boomi-coding-conventions/SKILL.md))
says the same things in a compact form for the agent; the plugin's hooks enforce the property and subprocess rules
automatically (see [How the conventions are enforced](#5-how-the-conventions-are-enforced)).

## Contents

1. [Dynamic properties](#1-dynamic-properties)
2. [Process names](#2-process-names)
3. [Names that are not renamed](#3-names-that-are-not-renamed)
4. [Relation with Boomi Companion](#4-relation-with-boomi-companion)
5. [How the conventions are enforced](#5-how-the-conventions-are-enforced)

## 1. Dynamic properties

| Kind | Prefix | Example | Instead of |
|---|---|---|---|
| Dynamic Process Property (one value for the whole execution, shared with subprocesses) | `PP_` | `PP_BATCH_ID` | `DPP_BATCH_ID` |
| Dynamic Document Property (one value per document, travels with it) | `D_` | `D_CUSTOMER_SEGMENT` | `DDP_CUSTOMER_SEGMENT` |

After the prefix the name is in `UPPERCASE_WITH_UNDERSCORES`.

**Why.** The prefix tells at a glance the scope of a value, which is the information that matters when reading a
Set Properties step, a Decision or a map function: process-wide (`PP_`) or per document (`D_`). The shorter prefixes
keep the names readable in the narrow fields of the Boomi GUI.

The prefix is part of the name, so it appears wherever the name does: the property set in a Set Properties step
(`process.PP_BATCH_ID`, `dynamicdocument.D_CUSTOMER_SEGMENT`), every step that reads it, scripts
(`ExecutionUtil.getDynamicProcessProperty("PP_BATCH_ID")`) and process extensions.

## 2. Process names

| Kind of process | Name | Example |
|---|---|---|
| Subprocess: Data Passthrough start, called with a Process Call | `[S] ` + name | `[S] Load customer orders` |
| Unit test process: exists only to test another process | `[UT] ` + name of the tested process + scenario | `[UT] Load customer orders - inserts order` |
| Main process: listener, scheduled, started by hand | name without prefix | `Orders JMS listener` |

**Why.** In the component explorer and in the Process Call picker the prefix separates what can be deployed and
started on its own from the building blocks and from the tests. `[UT]` processes are never deployed to production
environments; the prefix makes them easy to exclude from packaged deployments and to find for a test run. One prefix
per process: a unit test is `[UT]`, not `[UT][S]`.

### Folders of unit tests

The `[UT]` processes live in a folder named `Unit test`, created **inside the folder that holds the processes under
test**, next to them (self-containment: the tests travel, are reviewed and are excluded from a deployment together
with the code they cover). If one folder needs several groups of tests, each group is `Unit test - <description>`
(`Unit test - orders`, `Unit test - customers`). The folder name has no `[UT]` prefix: the prefix identifies
processes, which is where it is read.

**Why.** `Test` alone is too generic: it can mean a manual test, a test environment, a sandbox. `Unit test` says what
the folder holds. The suffix is used only when there is more than one, so the common case stays short.

A listener exposes its logic through a thin wrapper: the listener process (no prefix) only receives the message and
calls the `[S]` that does the work, so the logic can be tested (see the `boomi-unit-testing` skill).

## 3. Names that are not renamed

- **Names defined outside the component**: properties read or written by a library or a driver (mockjdbc uses
  `mockjdbc_<table>` and `mockjdbc_<table>_params`), Boomi built-in properties (`meta.*`, `connector.*`, `mime.*`),
  names agreed with another team or used by an existing integration.
- **Existing components**: new properties follow the convention. Existing `DPP_` / `DDP_` properties are renamed only on
  purpose, and then in every component that sets or reads them: a property name is a plain string, and a reader that
  still uses the old name silently gets an empty value.

## 4. Relation with Boomi Companion

The Boomi Companion skill (`bc-integration:boomi-integration`) is the reference for the XML of every Boomi component;
its documentation and examples use `DPP_` and `DDP_` and give no rule for process names. These conventions replace
only the naming: everything else in the Companion stays valid. When an example from the Companion is reused, its
names are translated (`DPP_FROM_WRAPPER` → `PP_FROM_WRAPPER`).

## 5. How the conventions are enforced

An agent can be told the rules in three ways, from the weakest to the strongest:

| Level | What it does | Limits |
|---|---|---|
| The skill | Claude loads `boomi-coding-conventions` when its description matches the task; the skill says that it overrides the Companion | The agent may not load it, or may follow a Companion example it has just read |
| Workspace instructions (`CLAUDE.md`) | Instructions in `CLAUDE.md` take precedence over skills | Must be added to each Boomi workspace (or to the Companion workspace template) |
| Plugin hooks (installed with the `boomi-conventions` plugin) | At session start, in a Boomi workspace, the agent is told that these conventions win. Before a Write/Edit of a component XML, or before `boomi-component-create.sh`, the call is refused when it introduces a `DPP_`/`DDP_` property or a passthrough subprocess without `[S] `; the agent gets the correct names and retries | Checks only what can be checked mechanically: `[UT]` names and the meaning of a name are left to the skill |

The hooks only look at names **introduced** by a change: names already in a pulled component are accepted. A name
that must stay as it is (for example `DPP_SHARED`, agreed with another team) goes in a file `.boomi-naming-allow` in
the workspace directory, one name per line (`#` for comments).

Suggested lines for the `CLAUDE.md` of a Boomi workspace (or of the Companion workspace template, see
`/bc-integration:configure-template-workspace`):

```markdown
## Boomi naming
Follow the `boomi-conventions:boomi-coding-conventions` skill for every name (PP_, D_, [S], [UT]): it takes
precedence over the naming of the `boomi-integration` references and examples.
```
