---
name: boomi-coding-conventions
description: Use when creating, naming or modifying Boomi components - processes, subprocesses, unit test processes, Set Properties steps, dynamic process properties or dynamic document properties - and when Boomi Companion (boomi-integration) examples suggest DPP_ or DDP_ names.
---

# Boomi coding conventions

## Overview

House naming rules for Boomi components. They **override the defaults of the Boomi Companion skill**
(`bc-integration:boomi-integration`), whose references and examples use `DPP_` / `DDP_`: when you copy an
example from there, rename it with the prefixes below.

## Quick reference

| Element | Convention | Example | Not |
|---|---|---|---|
| Dynamic Process Property | prefix `PP_` | `PP_BATCH_ID` | `DPP_BATCH_ID` |
| Dynamic Document Property | prefix `D_` | `D_CUSTOMER_SEGMENT` | `DDP_CUSTOMER_SEGMENT` |
| Subprocess (called by a Process Call, passthrough start) | name starts with `[S] ` | `[S] Load customer orders` | `Load customer orders - Sub` |
| Unit test process | name starts with `[UT] ` | `[UT] Load customer orders - inserts order` | `TEST Load customer orders` |
| Main / listener / scheduled process | no prefix | `Orders JMS listener` | |
| Folder of unit tests | `Unit test`, inside the folder of the processes under test; `Unit test - <description>` if there are several in the same folder | `Orders/Unit test`, `Orders/Unit test - customers` | `Test`, `[UT] Tests`, a global `Tests` folder |

After the prefix the property name stays in `UPPERCASE_WITH_UNDERSCORES`. Process prefixes are followed by one space.

## In the XML

The prefix is part of the property name everywhere the name appears:

```xml
<!-- Set Properties: dynamic process property -->
<documentproperty name="Dynamic Process Property - PP_BATCH_ID" persist="false"
                  propertyId="process.PP_BATCH_ID" ...>

<!-- Set Properties: dynamic document property -->
<documentproperty name="Dynamic Document Property - D_CUSTOMER_SEGMENT" persist="false"
                  propertyId="dynamicdocument.D_CUSTOMER_SEGMENT" ...>

<!-- Reading them (Decision, Notify, Message, Map parameters...) -->
<processparameter processproperty="PP_BATCH_ID" processpropertydefaultvalue=""/>
<trackparameter defaultValue="" propertyId="dynamicdocument.D_CUSTOMER_SEGMENT"
                propertyName="Dynamic Document Property - D_CUSTOMER_SEGMENT"/>
```

The same applies to scripts (`ExecutionUtil.getDynamicProcessProperty("PP_BATCH_ID")`,
`props.getProperty("document.dynamic.userdefined.D_CUSTOMER_SEGMENT")`) and to extensions (DPP overrides
declared in `processOverrides` use the `PP_` name).

Companion patterns translate directly: `DPP_FROM_WRAPPER` becomes `PP_FROM_WRAPPER`.

## Which process is `[S]`

- `[S]`: any process whose start shape is passthrough (Data Passthrough) and that exists to be called by a
  Process Call, including the "business logic" subprocess of a listener wrapper.
- `[UT]`: a process that exists only to test another process (see `boomi-unit-testing`). It is never deployed to
  production environments.
- A `[UT]` process is not also `[S]`: one prefix per process.
- Put the `[UT]` processes in a `Unit test` folder created **inside the folder of the processes they test** (tests
  stay with the code they cover). Several groups in the same folder: `Unit test - <description>`. The folder has no
  `[UT]` prefix, and `Test` alone is too generic.

## Names you do not rename

- Names fixed by something outside your component keep their spelling: properties read by a library or driver
  (e.g. mockjdbc reads `mockjdbc_<query id or table>` and writes `mockjdbc_<query id or table>_params`), Boomi built-in properties
  (`meta.*`, `connector.*`, `mime.*`), names agreed with another team.
- Existing components pulled from the account: new properties follow the convention; rename existing `DPP_` / `DDP_`
  properties only when asked, and then in every component that reads or writes them (a property name is a string,
  a missed reader silently gets an empty value).

## The naming guard

The plugin's hook refuses a Write/Edit of a component XML (or a `boomi-component-create.sh`) that introduces a
`DPP_` / `DDP_` property or a passthrough subprocess without `[S] `. When it does, rename as the message says, in
every occurrence, and retry. Add a name to `.boomi-naming-allow` (workspace directory, one per line) only when the user
explicitly asks to keep it.

## Check before push

```bash
# new or changed components must not introduce DPP_/DDP_ names
grep -rnoE '\b(DPP|DDP)_[A-Z0-9_]+' active-development --include='*.xml'
# list process names: passthrough-start subprocesses need "[S] ", test processes "[UT] "
grep -oE '<bns:Component [^>]*type="process"[^>]*' active-development/process/*.xml | grep -oE ' name="[^"]*"'
```

## Common mistakes

| Mistake | Fix |
|---|---|
| Copying a Companion example with `DPP_X` / `DDP_X` as is | Rename to `PP_X` / `D_X` in every occurrence (set and read) |
| Renaming only the Set Properties step | The name also appears in Decision, Notify, Map functions, scripts, extensions |
| `[S]` on a listener wrapper | The wrapper is the main process: no prefix; its called logic is `[S]` |
| `[UT]`/`[S]` without the space, or as a suffix | `[UT] Name`, `[S] Name` |
| `[UT]` processes in a generic `Test` folder, or in a central folder far from the code | `Unit test` folder inside the folder of the tested processes |
| Prefixing `mockjdbc_*` properties with `PP_` | The driver reads only `mockjdbc_*`: keep the driver's name |
