#!/usr/bin/env python3
"""PreToolUse guard for the Boomi naming conventions of the boomi-conventions plugin.

Denies a tool call that would introduce, in a Boomi component XML:
  - a dynamic process / document property named DPP_* / DDP_* (convention: PP_* / D_*);
  - a passthrough-start process (subprocess) whose name does not start with "[S] " or "[UT] ".

Only names *introduced* by the call are checked: names already present in the file on disk are
left alone, so pulled components keep working. Names listed in .boomi-naming-allow (one per line,
in the project directory) are always accepted.

Reads the hook JSON from stdin; prints a deny decision as JSON on stdout, nothing otherwise.
"""
import json
import os
import re
import shlex
import sys

PROPERTY_RE = re.compile(r"\b(DPP|DDP)_[A-Za-z0-9_]+")
COMPONENT_RE = re.compile(r"<(?:bns:)?Component\b[^>]*>", re.S)
ATTR_RE = r'\b{}="([^"]*)"'
CREATE_SCRIPTS = ("boomi-component-create.sh",)
ALLOW_FILE = ".boomi-naming-allow"
FIX = {"DPP": "PP", "DDP": "D"}


def read_text(path):
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except (OSError, UnicodeDecodeError):
        return ""


def allowed_names(cwd):
    text = read_text(os.path.join(cwd or ".", ALLOW_FILE))
    return {line.strip() for line in text.splitlines() if line.strip() and not line.startswith("#")}


def property_names(text):
    return {m.group(0) for m in PROPERTY_RE.finditer(text)}


def component_attr(text, name):
    m = COMPONENT_RE.search(text)
    if not m:
        return None
    a = re.search(ATTR_RE.format(name), m.group(0))
    return a.group(1) if a else None


def is_subprocess(text):
    return component_attr(text, "type") == "process" and "<passthroughaction" in text


def problems(new_text, old_text, allow):
    """Return the list of violations introduced by new_text compared with old_text."""
    found = []
    for name in sorted(property_names(new_text) - property_names(old_text) - allow):
        prefix, rest = name.split("_", 1)
        found.append(f"property {name}: use {FIX[prefix]}_{rest}")
    name = component_attr(new_text, "name")
    if (name is not None and is_subprocess(new_text) and name not in allow
            and not name.startswith(("[S] ", "[UT] "))
            and name != component_attr(old_text, "name")):
        found.append(f'subprocess "{name}" (passthrough start): name it "[S] {name}"')
    return found


def candidate_texts(tool, tool_input, cwd):
    """Yield (path, new_text, old_text) for the XML the call writes or creates."""
    if tool in ("Write", "Edit", "MultiEdit"):
        path = tool_input.get("file_path", "")
        if not path.endswith(".xml"):
            return
        old = read_text(path)
        if tool == "Write":
            yield path, tool_input.get("content", ""), old
            return
        edits = tool_input.get("edits") or [tool_input]
        new = old
        for e in edits:
            o, n = e.get("old_string", ""), e.get("new_string", "")
            new = new.replace(o, n) if e.get("replace_all") else new.replace(o, n, 1)
        yield path, new, old
    elif tool == "Bash":
        command = tool_input.get("command", "")
        if not any(s in command for s in CREATE_SCRIPTS):
            return
        try:
            tokens = shlex.split(command)
        except ValueError:
            tokens = command.split()
        for tok in tokens:
            if tok.endswith(".xml"):
                path = tok if os.path.isabs(tok) else os.path.join(cwd or ".", tok)
                yield path, read_text(path), ""   # a created component is new as a whole


def main():
    try:
        data = json.load(sys.stdin)
    except ValueError:
        return 0
    cwd = data.get("cwd") or os.getcwd()
    allow = allowed_names(cwd)
    issues = []
    for path, new, old in candidate_texts(data.get("tool_name", ""), data.get("tool_input") or {}, cwd):
        issues += [f"{os.path.basename(path)}: {p}" for p in problems(new, old, allow)]
    if issues:
        reason = ("Boomi naming conventions (skill boomi-coding-conventions, they override the DPP_/DDP_ "
                  "names of the Boomi Companion examples):\n- " + "\n- ".join(issues) +
                  "\nRename every occurrence (set and read) and retry. Only if the user explicitly asks to "
                  f"keep a name, add it to {ALLOW_FILE} in the project directory.")
        json.dump({"hookSpecificOutput": {"hookEventName": "PreToolUse",
                                          "permissionDecision": "deny",
                                          "permissionDecisionReason": reason}}, sys.stdout)
    return 0


if __name__ == "__main__":
    sys.exit(main())
