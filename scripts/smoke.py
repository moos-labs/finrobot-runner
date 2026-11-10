#!/usr/bin/env python3
"""Smoke test for FinRobot (AI4Finance-Foundation/FinRobot).

SMOKE ONLY: imports the installed `finrobot` package (the V0 / AutoGen
package, whose source lives in upstream `finrobot_autogen/finrobot` and
whose import name is `finrobot`) and one or two submodules, and records
exactly what imported. No LLM calls, no API keys, no analysis.

Writes:
  results/smoke.json  {"ok": bool, "imports": [...], ...}
  results/smoke.md    human-readable evidence
"""
import importlib
import importlib.metadata
import json
import os
import sys
import traceback

RESULTS = os.path.join(os.getcwd(), "results")
os.makedirs(RESULTS, exist_ok=True)

# Top-level `finrobot/__init__.py` is empty upstream, so also probe
# submodules with real code.
TARGETS = ["finrobot", "finrobot.data_source", "finrobot.functional"]

imports = []
errors = {}
for name in TARGETS:
    try:
        mod = importlib.import_module(name)
        entry = {
            "module": name,
            "ok": True,
            "file": getattr(mod, "__file__", None),
        }
        imports.append(entry)
        print(f"IMPORT OK: {name} -> {entry['file']}")
    except Exception as exc:  # record, do not hide
        errors[name] = f"{type(exc).__name__}: {exc}"
        imports.append({"module": name, "ok": False, "error": errors[name]})
        print(f"IMPORT FAILED: {name}: {type(exc).__name__}: {exc}")
        traceback.print_exc()

version = None
for dist in ("FinRobot", "finrobot"):
    try:
        version = importlib.metadata.version(dist)
        break
    except importlib.metadata.PackageNotFoundError:
        continue
print(f"finrobot distribution version: {version}")

imported_names = [e["module"] for e in imports if e["ok"]]
# ok = the top-level package itself imported (that is what this smoke
# proves). Submodule failures are reported verbatim, not hidden.
ok = "finrobot" in imported_names

payload = {
    "ok": ok,
    "tool": "FinRobot",
    "upstream": "https://github.com/AI4Finance-Foundation/FinRobot",
    "package": "finrobot",
    "version": version,
    "python": sys.version,
    "imports": imports,
    "imported": imported_names,
    "errors": errors,
}

with open(os.path.join(RESULTS, "smoke.json"), "w") as f:
    json.dump(payload, f, indent=2)

lines = [
    "# FinRobot smoke test",
    "",
    f"- ok: **{ok}**",
    f"- package: `finrobot`",
    f"- distribution version: `{version}`",
    f"- python: `{sys.version.split()[0]}`",
    "",
    "## Imports",
    "",
]
for e in imports:
    if e["ok"]:
        lines.append(f"- OK `{e['module']}` -> `{e.get('file')}`")
    else:
        lines.append(f"- FAILED `{e['module']}`: `{e['error']}`")
lines += [
    "",
    "Smoke only: no LLM calls were made and no API keys were used.",
    "",
]
with open(os.path.join(RESULTS, "smoke.md"), "w") as f:
    f.write("\n".join(lines))

print(json.dumps(payload, indent=2))
sys.exit(0 if ok else 1)
