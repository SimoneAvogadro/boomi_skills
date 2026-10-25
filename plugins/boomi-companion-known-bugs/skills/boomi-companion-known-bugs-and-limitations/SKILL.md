---
name: boomi-companion-known-bugs-and-limitations
description: Use when working with the Boomi Companion skill (bc-integration:boomi-integration) - before writing a Database V2 UPDATE operation, before declaring process extensions (connection overrides), or when a Companion script is needed for environments, environment extensions on another environment, or deleting components. Lists known bugs and limitations of specific Companion versions, with the correction and a check to tell whether a newer version fixed them.
---

# Boomi Companion: known bugs and limitations

Bugs and limitations found in the Boomi Companion skill (`bc-integration:boomi-integration`) while using it, each
with the Companion versions where it was seen, the correction, and a check. The list is temporary: an entry goes
away when a Companion release fixes it.

## How to use an entry

1. **Installed version**: `cat <companion skill dir>/VERSION` (the skill dir is `.../bc-integration/<version>/skills/
   boomi-integration/`; the installed one is the `installPath` of `bc-integration@boomi-companion` in
   `~/.claude/plugins/installed_plugins.json`).
2. **Installed version not newer than "Last checked"**: the entry applies. Follow the correction instead of the
   Companion text.
3. **Installed version newer**: run the entry's **Check**.
   - Still there: apply the correction, and tell the user the entry is still valid in that version.
   - Gone: follow the Companion, and tell the user the entry looks fixed in that version, so it can be removed.

Priority: the Companion is the reference for everything else; for these entries only, the correction wins over the
Companion text (until a check shows the fix).

## Bugs

### CB-1. Database V2 Standard Update: the type field is `Type`, not `UpdateType`

- **Seen in**: 1.0.64, 1.0.76, 1.0.83, 1.0.87. **Last checked**: 1.0.87 (2026-10-23).
- **Companion text**: `references/components/databasev2_connector_operation_component.md`, "UPDATE/DELETE
  Operations": `UPDATE: <field id="UpdateType" type="string" value="Dynamic Update|Standard Update"/>`.
- **Symptom**: the operation is accepted by push, but every run fails before any SQL with
  `UnsupportedOperationException: This operation type is not supported:null` (in `createUpdateOperation`), also
  against the real database.
- **Correction**: `<field id="Type" type="string" value="Standard Update"/>` (verified on the platform: a Standard
  Update and an Update Commit By Rows with `Type` run). DELETE is right as documented: `DeleteType` works.
- **Check**: `grep -n 'UpdateType' <companion skill dir>/references/components/databasev2_connector_operation_component.md`
  still matches → still there.

### CB-2. Process extensions: SDK connectors have no `xpath`

- **Seen in**: 1.0.87. **Last checked**: 1.0.87 (2026-10-23).
- **Companion text**: `references/components/process_extensions.md`, "Connection Overrides": "Every `<field>` must
  carry the connector-specific `xpath` attribute ... A field without its `xpath` is declared but inert", and the
  advice to emit the block "each carrying its own `xpath`".
- **Symptom**: for a connector built on the Connector SDK (`GenericConnectionConfig`, for example Database V2), the
  block the GUI writes has **no** `xpath` on any field, and it works: the override is applied at run time. An agent
  following the Companion thinks the declaration is broken, or adds invented xpaths.
- **Correction**: the `xpath` rule holds for connectors with their own settings (Database Legacy
  `DatabaseConnectionSettings/@...`, HTTP Client `HttpSettings/@url`). For SDK connectors, use the block as the GUI
  writes it, without `xpath`:
  `<ConnectionOverride id="<connection id>"><field id="url" label="Connection URL" overrideable="true"/><field id="className" label="Class Name" overrideable="true"/></ConnectionOverride>`.
  (The Companion's REST Client row with `GenericConnectionConfig/field[@id='<fieldId>']/@value` was not checked.)
- **Check**: the "Connection Overrides" section still says that every field must carry an `xpath`, with no exception
  for SDK connectors → still there.

## Limitations

### CL-1. `boomi-extensions.sh` works only on `BOOMI_ENVIRONMENT_ID`

- **Seen in**: 1.0.87. **Last checked**: 1.0.87 (2026-10-23).
- **Limitation**: `get` and `set` take the environment from `.env`; there is no option for another environment.
- **Workaround**: to read another environment, `GET EnvironmentExtensions/<environmentId>` through `boomi_api` of
  `scripts/boomi-common.sh` (`load_env`, `build_api_url`). To write, change `BOOMI_ENVIRONMENT_ID` in `.env` with the
  user's consent.
- **Check**: `bash <companion skill dir>/scripts/boomi-extensions.sh --help` lists an environment option → fixed.

### CL-2. No script for environment and deployment queries

- **Seen in**: 1.0.87. **Last checked**: 1.0.87 (2026-10-23).
- **Limitation**: `boomi-deploy.sh --list-environments` lists only the name and id of each environment, not its
  classification (`TEST` / `PROD`); no script lists runtime attachments, active deployments of an environment, or the
  connection licensing report; the Companion asks to stop and discuss before crafting custom calls.
- **Workaround**: read-only calls through `boomi_api` (never writes). Bodies that work: `POST Environment/query` with
  `{"QueryFilter":{"expression":{"operator":"LIKE","property":"name","argument":["%"]}}}`;
  `POST DeployedPackage/query` with an `and` of `environmentId` and `active` = `true` (an empty `and` group is rejected
  with HTTP 400). `POST ConnectionLicensingReport` returns a download `url` on `platform.boomi.com`: `GET` it as it
  is, with the same credentials.
- **Check**: `ls <companion skill dir>/scripts/` shows a script for these queries, or `--list-environments` prints
  the classification → fixed.

### CL-3. Components cannot be deleted by script

- **Seen in**: 1.0.87. **Last checked**: 1.0.87 (2026-10-23).
- **Limitation**: there is no delete script; `boomi-undeploy.sh` removes deployments only.
- **Workaround**: undeploy, then ask the user to delete the component in the GUI, and list it in the final answer.
- **Check**: `ls <companion skill dir>/scripts/ | grep -i delete` → fixed if it finds one.

### CL-4. A pull to another folder writes sync state into the workspace

- **Seen in**: 1.0.87 (reported by an agent, not reproduced). **Last checked**: 1.0.87 (2026-10-23).
- **Limitation**: `boomi-component-pull.sh --target-path <dir outside the workspace>` still writes entries into the
  workspace `active-development/.sync-state`, which point at the other folder.
- **Workaround**: after such a pull, remove those `.sync-state` entries.
- **Check**: pull one component with `--target-path` to a temporary folder and look for a new `.sync-state` entry.

## Adding an entry

Add a bug or limitation only when it was seen on the platform or in the Companion files, with: the Companion text it
contradicts (file and section), the versions where it was seen, the date of the last check, the symptom, the
correction verified on the platform, and a check that a newer version can be tested against. Remove it when a check
shows the fix.
