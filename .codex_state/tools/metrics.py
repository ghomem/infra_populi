#!/usr/bin/env python3
"""Per-attempt run metrics (step 3.4, diagnosis F.9). Tools append EVENTS while a class is worked on; `close`
folds them into one tracked record per attempt in .codex_state/runs/metrics.jsonl (append-only history,
P2-exempt) and commits it as `P8: record metrics after <class>` (own commit type; never part of a review).

  metrics.py event <class> <kind> [JSON]     append an event (untracked .codex_state/logs/metrics/events.jsonl)
  metrics.py codex-usage <since-epoch>       JSON: tokens, tool calls, model of the codex exec sessions since then
  metrics.py agent-summary                   JSON from last_run_summary.yaml on stdin (`puppet` YAML subset)
  metrics.py close <class> --outcome GREEN|PASS|FAIL|BLOCKED|FAILED|ESCALATED [--path P] [--interventions N]
                   [--note TEXT] [--no-commit]
  metrics.py summary                         medians/rates over the tracked records

Event kinds written by the tools: path (classify_path), pregate (pregate.py, class mode), revert (harness --revert-first, wrapper), harness
(test_class.sh, every exit), codex (wrapper), record (record_green.sh), review (review_class.py verdict).
The reviewer never reads .codex_state/runs/ (reviewer.md): these records name the generation path.
P8_METRICS_DIR / P8_RUNS_FILE redirect the event log / tracked file (tests).
"""

from __future__ import annotations

import datetime as dt
import json
import os
import re
import statistics
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True
TOOLS = Path(__file__).resolve().parent
REPO = TOOLS.parents[1]
CODEX_SESSIONS = Path.home() / ".codex" / "sessions"
OUTCOMES = ("GREEN", "PASS", "FAIL", "BLOCKED", "FAILED", "ESCALATED")
ADVISOR = os.environ.get("P8_ADVISOR", "claude-opus-5-5")


def events_path() -> Path:
    return Path(os.environ.get("P8_METRICS_DIR") or REPO / ".codex_state" / "logs" / "metrics") / "events.jsonl"


def runs_path() -> Path:
    return Path(os.environ.get("P8_RUNS_FILE") or REPO / ".codex_state" / "runs" / "metrics.jsonl")


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def short(name: str) -> str:
    name = name.removeprefix("puppet_infrastructure::")
    if not re.fullmatch(r"[a-z][a-z0-9_]*", name):
        raise SystemExit(f"ERROR: invalid class name {name!r}")
    return name


def add_event(cls: str, kind: str, data: dict) -> None:
    path = events_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"ts": now(), "class": cls, "kind": kind, "data": data}) + "\n")


def read_jsonl(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


# ------------------------------------------------------------------ sources

def codex_usage(since: float, sessions: Path = CODEX_SESSIONS, cwd: str = str(REPO)) -> dict:
    """Sum the codex exec sessions started at/after `since` in this repo. Never copies account ids."""
    total = {"sessions": 0, "input_tokens": 0, "cached_input_tokens": 0, "output_tokens": 0,
             "reasoning_output_tokens": 0, "total_tokens": 0, "tool_calls": 0, "model": None, "effort": None,
             "cli_version": None}
    for path in sorted(sessions.rglob("rollout-*.jsonl")) if sessions.is_dir() else []:
        if path.stat().st_mtime < since:
            continue
        meta, usage, calls, ctx = None, None, 0, {}
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                item = json.loads(line)
            except ValueError:
                continue
            payload = item.get("payload") or {}
            if item.get("type") == "session_meta":
                meta = payload
            elif item.get("type") == "turn_context":
                ctx = payload
            elif item.get("type") == "event_msg" and payload.get("type") == "token_count" and payload.get("info"):
                usage = payload["info"].get("total_token_usage")
            elif item.get("type") == "response_item" and payload.get("type") in ("custom_tool_call", "function_call"):
                calls += 1
        if not meta or meta.get("cwd") != cwd or meta.get("originator") != "codex_exec":
            continue
        started = dt.datetime.fromisoformat(meta["timestamp"].replace("Z", "+00:00")).timestamp()
        if started < since:
            continue
        total["sessions"] += 1
        for key in ("input_tokens", "cached_input_tokens", "output_tokens", "reasoning_output_tokens", "total_tokens"):
            total[key] += int((usage or {}).get(key, 0))
        total["tool_calls"] += calls
        total["model"] = ctx.get("model") or total["model"]
        total["effort"] = ctx.get("effort") or total["effort"]
        total["cli_version"] = meta.get("cli_version") or total["cli_version"]
    return total


def agent_summary(text: str) -> dict:
    """The fields we keep from last_run_summary.yaml (+ a `transaction_uuid:` line appended by the caller).
    A tiny indentation parser: the file is a flat two-level YAML mapping of scalars."""
    tree: dict = {}
    section = None
    for line in text.splitlines():
        if not line.strip() or line.startswith("---"):
            continue
        m = re.match(r"^(\s*)([A-Za-z_]+):\s*(.*)$", line)
        if not m:
            continue
        indent, key, value = m.groups()
        if not indent:
            section = key
            tree[key] = value.strip() if value.strip() else {}
        elif isinstance(tree.get(section), dict):
            tree[section][key] = value.strip()

    def num(section: str, key: str):
        try:
            return float(tree.get(section, {}).get(key))
        except (TypeError, ValueError, AttributeError):
            return None
    res = tree.get("resources") or {}
    return {"transaction_uuid": tree.get("transaction_uuid") or None,
            "config_version": (tree.get("version") or {}).get("config"),
            "res_total": int(num("resources", "total") or 0), "res_changed": int(num("resources", "changed") or 0),
            "res_failed": int(num("resources", "failed") or 0),
            "res_corrective": int(num("resources", "corrective_change") or 0) if isinstance(res, dict) else 0,
            "events": int(num("events", "total") or 0), "t_total": num("time", "total"),
            "t_catalog": num("time", "config_retrieval"), "t_apply": num("time", "catalog_application")}


# ------------------------------------------------------------------ close / summary

def fold(cls: str, events: list[dict], records: list[dict], outcome: str, path: str | None,
         interventions: int, note: str) -> dict:
    mine = [e for e in events if e["class"] == cls]
    # events since this class's previous close
    last_close = max((r["closed_at"] for r in records if r["class"] == cls), default="")
    mine = [e for e in mine if e["ts"] > last_close] if last_close else mine
    kinds = lambda k: [e["data"] for e in mine if e["kind"] == k]  # noqa: E731
    reverts = kinds("revert")
    harness = kinds("harness")
    codex = kinds("codex")
    reviews = kinds("review")
    paths = kinds("path")
    pregates = kinds("pregate")
    usage = [c.get("usage") or {} for c in codex]
    record = {
        "schema": 1, "class": cls, "attempt": 1 + sum(1 for r in records if r["class"] == cls),
        "opened_at": mine[0]["ts"] if mine else None, "closed_at": now(), "outcome": outcome,
        "path": path or (paths[-1].get("path") if paths else None),
        "advisor": ADVISOR,
        "executor": (" ".join(str(usage[-1].get(k)) for k in ("cli_version", "model", "effort"))
                     if usage and usage[-1].get("model") else None),
        "reverts": len(reverts), "revert_s": [r.get("total_s") for r in reverts],
        "harness_runs": len(harness), "harness_green": sum(1 for h in harness if h.get("rc") == 0),
        "harness": [{k: h.get(k) for k in ("rc", "revert_first", "run1_events", "duration_s", "reason")} for h in harness],
        "agent_runs": [a for h in harness for a in h.get("agent_runs", [])],
        "codex_runs": len(codex), "codex_s": [c.get("codex_s") for c in codex],
        "codex_rc": [c.get("rc") for c in codex],
        "codex_tokens": sum(int(u.get("total_tokens", 0)) for u in usage),
        # total_tokens counts cached input again on every turn; uncached = fresh input + output
        "codex_tokens_uncached": sum(int(u.get("input_tokens", 0)) - int(u.get("cached_input_tokens", 0))
                                     + int(u.get("output_tokens", 0)) for u in usage),
        "codex_tool_calls": sum(int(u.get("tool_calls", 0)) for u in usage),
        "reviews": [{k: r.get(k) for k in ("verdict", "failed_checks", "check_s", "file")} for r in reviews],
        "pregate": [{k: g.get(k) for k in ("status", "findings")} for g in pregates],
        "commits": [c for e in kinds("record") for c in e.get("commits", [])],
        "human_interventions": interventions, "note": note or None,
    }
    return record


def commit_record(cls: str) -> None:
    rel = runs_path().relative_to(REPO)
    dirty = [l[3:] for l in subprocess.run(["git", "-C", str(REPO), "status", "--porcelain", "--untracked-files=all"], capture_output=True,
                                            text=True, check=True).stdout.splitlines()]
    if any(path != str(rel) for path in dirty):
        raise SystemExit(f"ERROR: worktree holds other changes {dirty[:5]}; metrics commit refused")
    subprocess.run(["git", "-C", str(REPO), "add", "--", str(rel)], check=True)
    subprocess.run(["git", "-C", str(REPO), "commit", "-q", "-m", f"P8: record metrics after {cls}"], check=True)
    subprocess.run(["git", "-C", str(REPO), "push", "-q"], check=True)


def cmd_close(cls: str, argv: list[str]) -> int:
    def opt(name, default=None):
        return argv[argv.index(name) + 1] if name in argv else default
    outcome = opt("--outcome")
    if outcome not in OUTCOMES:
        raise SystemExit(f"ERROR: --outcome must be one of {', '.join(OUTCOMES)}")
    records = read_jsonl(runs_path())
    record = fold(cls, read_jsonl(events_path()), records, outcome, opt("--path"), int(opt("--interventions", "0")),
                  opt("--note", ""))
    runs_path().parent.mkdir(parents=True, exist_ok=True)
    with runs_path().open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, sort_keys=False) + "\n")
    print("METRICS " + json.dumps(record))
    if "--no-commit" not in argv:
        commit_record(cls)
    return 0


def median(values: list) -> float | None:
    values = [v for v in values if isinstance(v, (int, float))]
    return round(statistics.median(values), 1) if values else None


def cmd_summary() -> int:
    records = read_jsonl(runs_path())
    print(f"{len(records)} attempt records in {runs_path().relative_to(REPO) if runs_path().is_relative_to(REPO) else runs_path()}")
    by_path: dict[str, list[dict]] = {}
    for r in records:
        by_path.setdefault(r.get("path") or "unknown", []).append(r)
    for path, rs in sorted(by_path.items()):
        greens = [r for r in rs if r["outcome"] in ("GREEN", "PASS")]
        reviews = [v for r in rs for v in r.get("reviews", [])]
        fails = sum(1 for v in reviews if v.get("verdict") == "FAIL")
        print(f"- {path}: {len(rs)} attempts, {len(greens)} green/pass; "
              f"median revert_s {median([s for r in rs for s in r['revert_s']])}, "
              f"codex_s {median([s for r in rs for s in r['codex_s']])}, "
              f"codex uncached tokens/attempt {median([r.get('codex_tokens_uncached', 0) for r in rs if r['codex_runs']])} "
              f"(total incl. cached re-reads {median([r['codex_tokens'] for r in rs if r['codex_runs']])}), "
              f"pregate findings {sum(len(p.get('findings', [])) for r in rs for p in r.get('pregate', []))}, "
              f"codex runs/green {round(sum(r['codex_runs'] for r in rs) / len(greens), 2) if greens else None}, "
              f"reviewer FAIL rate {f'{fails}/{len(reviews)}' if reviews else None}")
    return 0


def main(argv: list[str]) -> int:
    if len(argv) >= 3 and argv[0] == "event":
        data = json.loads(argv[3]) if len(argv) > 3 else {}
        add_event(short(argv[1]), argv[2], data)
        return 0
    if len(argv) == 2 and argv[0] == "codex-usage":
        print(json.dumps(codex_usage(float(argv[1]))))
        return 0
    if argv == ["agent-summary"]:
        print(json.dumps(agent_summary(sys.stdin.read())))
        return 0
    if len(argv) >= 2 and argv[0] == "close":
        return cmd_close(short(argv[1]), argv[2:])
    if argv == ["summary"]:
        return cmd_summary()
    print(__doc__.strip(), file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
