"""The apply gate: a class applied twice on a fresh node applies cleanly and then changes nothing.

One code path for every caller: the runner's own apply modes use `verdict()`, and a harness outside this package calls
the same function through this module's command line, so the two can never differ.

  python3 -m behaviour.gate < runs.json
      runs.json: {"runs": [{"rc": <exit code>, "out": <the run's output>}, {...}], "expected": [<resource ref>, ...]}
      Each `out` is the run's console output followed by one `CHANGED <resource ref>` line per resource Puppet's own
      last-run report marks changed (the runner's CHANGED script prints them). Prints the verdict as JSON; exit 0 when
      green, 1 when not, 2 on bad input.

The rules:
  - run 1 exits 0 or 2 (Puppet's detailed exit codes: 2 = changes applied);
  - neither run logged an `Error:` line (Puppet logs an exec check that timed out as an error, takes the exec as in sync
    and exits 0);
  - every run-2 event is one of the class's expected run-2 events (`*` in an expected ref matches any text); an event is
    a line that reports a change, or a resource the last-run report marks changed that no such line shows (a change
    logged below notice);
  - run 2 exits 0, or exits 2 with at least one event, every one of them expected.
"""

from __future__ import annotations

import json
import re
import sys

# A line that reports a change: any resource notice of the catalog, and the change forms Puppet prints wherever they
# appear (a plugin file outside Stage[main], a Resource API type's "defined '<attr>' as", a scheduled refresh).
EVENT = re.compile(r"Notice: /Stage\[main\]/|Notice: .*changed|Notice: .*created|Notice: .*defined content as"
                   r"|Notice: .*defined '[^']+' as|Notice: .*executed successfully|Notice: .*removed"
                   r"|Info: .*Scheduling refresh of")
ERROR = re.compile(r"^(?:\x1b\[[0-9;]*m)?Error: ", re.M)
CHANGED = "CHANGED "
SILENT = "Run-2 report, changed with no console event (log level below notice): "


def agent_result(rc: int, out: str, err: str = "") -> dict:
    """One run: its exit code (an `AGENT_RC=<n>` line in the output wins), its events and the errors it logged."""
    m = re.search(r"AGENT_RC=(\d+)", out)
    lines = out.splitlines()
    logged = [line.strip() for line in lines if EVENT.search(line) and not line.startswith(CHANGED)]
    changed = [line[len(CHANGED):].strip() for line in lines if line.startswith(CHANGED)]
    # a changed resource whose change no log line shows is an event of its own
    silent = [f"{CHANGED}{ref}" for ref in changed if not any(f"/{ref}/" in l or f"/{ref}:" in l for l in logged)]
    return {"rc": int(m.group(1)) if m else rc, "events": logged + silent,
            "errors": [line.strip()[:300] for line in lines if ERROR.match(line)],
            "tail": (out + err)[-1500:]}


def _matcher(expected: list[str]):
    refs = [re.compile(".*".join(re.escape(part) for part in ref.split("*"))) for ref in expected if ref]
    return lambda line: any(r.search(line) for r in refs)


def verdict(first: dict, second: dict, expected: list[str]) -> dict:
    """The gate over two runs (each from agent_result). `reason` names the first rule that failed."""
    is_expected = _matcher(expected)
    unexpected = [e for e in second["events"] if not is_expected(e)]
    hits = len(second["events"]) - len(unexpected)
    errors = (first.get("errors") or []) + (second.get("errors") or [])
    reason = ""
    if first["rc"] not in (0, 2):
        reason = f"run 1 failed (exit {first['rc']})"
    elif errors:
        reason = "a run logged an error"
    elif unexpected:
        reason = "run 2 still applied changes (not idempotent)"
    elif second["rc"] == 2 and not hits:
        reason = "run 2 exited 2 with no change event; green requires exit 0 (no changes, no failures)"
    elif second["rc"] not in (0, 2):
        reason = f"run 2 exited {second['rc']}; only exit 2 caused solely by expected run-2 events is accepted"
    return {"green": not reason, "reason": reason, "errors": errors,
            "unexpected": [SILENT + e[len(CHANGED):] if e.startswith(CHANGED) else e for e in unexpected],
            "expected_hits": hits}


def gate(first: dict, second: dict, expected: list[str]) -> bool:
    return verdict(first, second, expected)["green"]


def main() -> int:
    try:
        data = json.load(sys.stdin)
        first, second = (agent_result(int(r["rc"]), r["out"]) for r in data["runs"])
        expected = list(data.get("expected") or [])
    except (ValueError, KeyError, TypeError) as exc:
        print(json.dumps({"green": False, "reason": f"bad gate input: {exc}"}))
        return 2
    v = verdict(first, second, expected)
    print(json.dumps(v))
    return 0 if v["green"] else 1


if __name__ == "__main__":
    sys.exit(main())
