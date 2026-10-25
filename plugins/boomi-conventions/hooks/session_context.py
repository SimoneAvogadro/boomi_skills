#!/usr/bin/env python3
"""SessionStart hook: in a Boomi workspace, state that the plugin's naming conventions win over the Companion's.

A directory is a Boomi workspace when it has active-development/ (Boomi Companion layout) or a
.env that defines BOOMI_ variables. Elsewhere the hook prints nothing.
"""
import json
import os
import sys

CONTEXT = (
    "The Boomi naming conventions of the boomi-conventions plugin (skill "
    "boomi-conventions:boomi-coding-conventions) take precedence over the naming used in the "
    "bc-integration:boomi-integration references and examples: "
    "PP_ for dynamic process properties (not DPP_), D_ for dynamic document properties (not DDP_), "
    "'[S] ' prefix for subprocesses, '[UT] ' prefix for unit test processes. Load that skill before "
    "creating or renaming Boomi components. A project or customer skill (or the workspace CLAUDE.md) with "
    "its own conventions wins over these."
)


def is_boomi_workspace(cwd):
    if os.path.isdir(os.path.join(cwd, "active-development")):
        return True
    try:
        with open(os.path.join(cwd, ".env"), encoding="utf-8") as f:
            return any(line.lstrip().startswith("BOOMI_") for line in f)
    except (OSError, UnicodeDecodeError):
        return False


def main():
    try:
        data = json.load(sys.stdin)
    except ValueError:
        data = {}
    if is_boomi_workspace(data.get("cwd") or os.getcwd()):
        json.dump({"hookSpecificOutput": {"hookEventName": "SessionStart",
                                          "additionalContext": CONTEXT}}, sys.stdout)
    return 0


if __name__ == "__main__":
    sys.exit(main())
