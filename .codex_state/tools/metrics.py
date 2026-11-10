#!/usr/bin/env python3
"""Per-attempt run metrics (step 3.4, diagnosis F.9). Tools append EVENTS while a class is worked on; `close`
folds them into one tracked record per attempt in .codex_state/runs/metrics.jsonl (append-only history,
P2-exempt) and commits it as `P8: record metrics after <class>` (own commit type; never part of a review).

  metrics.py event <class> <kind> [JSON]     append an event (untracked .codex_state/logs/metrics/events.jsonl)
  metrics.py codex-usage <since-epoch>       JSON: tokens, tool calls, model of the codex exec sessions since then
  metrics.py agent-summary                   JSON from last_run_summary.yaml on stdin (`puppet` YAML subset)
  metrics.py close <class> --outcome GREEN|PASS|FAIL|BLOCKED|FAILED|ESCALATED [--path P]
                   [--interventions codex=N,advisor=N,human=N] [--note TEXT] [--no-commit]
  metrics.py summary                         medians/rates over the tracked records
  metrics.py batch-report <class>...         markdown table of the latest attempt per class: wall = dispatch→verdict,
                                             phases prep/pregate/harness/codex/record/review/wait, run-2 expectations

Event kinds written by the tools: path (classify_path), pregate (pregate.py, class mode), revert (harness --revert-first, wrapper), harness
(test_class.sh, every exit), codex (wrapper), record (record_green.sh), review (review_class.py verdict).
The reviewer never reads .codex_state/runs/ (reviewer.md): these records name the generation path.
P8_METRICS_DIR / P8_RUNS_FILE redirect the event log / tracked file (tests).

Interventions (HQ batch-3 acceptance item 3) — three counters per attempt. Each counts EPISODES after dispatch in
which the nominal flow stopped or was overstepped (one episode may hold several edits); prep before dispatch is not one.
  codex    Codex stopped and handed the class back (MISSING_PREREQUISITE, a reported block, a refused record), repaired
           its environment (VM start, module rollback), or acted beyond its authority (a plan/composites commit).
  advisor  the advisor stepped in: a fix after dispatch or after a RED (plan, fixture, harness capability, composite
           expectation, header), recording a GREEN on Codex's behalf, a second Codex dispatch.
  human    Salatiel/HQ acted for this attempt (a ruling mid-attempt, a host or VM action by hand).
Schema-1 records (batches 1–3) carry a single `human_interventions` count, used in practice for advisor actions. Their
three counters come from `.codex_state/runs/interventions_backfill.jsonl` (append-only; each line cites its basis,
human 0 per HQ); a schema-1 record without a backfill line reads codex/advisor unknown (None), human 0.
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


# ------------------------------------------------------------------ phases (HQ 2026-11-11 ruling 1)

PHASE_PRIORITY = ("review", "codex", "record", "harness", "pregate", "prep")


def _ts(value: str) -> float:
    return dt.datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()


def event_interval(e: dict) -> tuple[str, float, float] | None:
    """(phase, start, end) of one event; every event's ts is its END."""
    d, end = e.get("data") or {}, _ts(e["ts"])
    kind = e["kind"]
    if kind == "review":
        start = _ts(d["check_started"]) if d.get("check_started") else end - float(d.get("check_s") or 0)
        return "review", start, end
    seconds = {"path": d.get("duration_s"), "pregate": d.get("duration_s"), "harness": d.get("duration_s"),
               "codex": d.get("codex_s"), "record": d.get("duration_s"), "revert": d.get("total_s")}.get(kind)
    if seconds is None:
        return None
    phase = {"path": "prep", "revert": "harness"}.get(kind, kind)
    return phase, end - float(seconds), end


def phases(events: list[dict], closed_at: float) -> dict:
    """Wall = dispatch (first harness/Codex/revert start) -> verdict (last review end); every second of the wall is
    attributed to the highest-priority phase covering it, uncovered seconds are `wait`. Prep = first event -> dispatch
    (it includes pregate/classification before dispatch; pregate_s is also reported in full)."""
    intervals = [iv for iv in (event_interval(e) for e in events) if iv]
    if not intervals:
        return {}
    opened = min(start for _, start, _ in intervals)
    dispatch = min((start for ph, start, _ in intervals if ph in ("harness", "codex")), default=None)
    reviews = [end for ph, _, end in intervals if ph == "review"]
    verdict = max(reviews) if reviews else closed_at
    out = {"prep_s": round((dispatch - opened) if dispatch else 0.0, 1),
           "pregate_s": round(sum(end - start for ph, start, end in intervals if ph == "pregate"), 1)}
    if dispatch is None or verdict <= dispatch:
        return {**out, "wall_s": None}
    cuts = sorted({dispatch, verdict, *[t for _, a, b in intervals for t in (a, b) if dispatch < t < verdict]})
    spent = {ph: 0.0 for ph in ("harness", "codex", "record", "review", "wait")}
    for a, b in zip(cuts, cuts[1:]):
        covering = [ph for ph, start, end in intervals if start <= a and end >= b and ph in spent]
        ph = min(covering, key=PHASE_PRIORITY.index) if covering else "wait"
        spent[ph] += b - a
    return {**out, **{f"{k}_s": round(v, 1) for k, v in spent.items()}, "wall_s": round(verdict - dispatch, 1),
            "dispatch_at": dt.datetime.fromtimestamp(dispatch, dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "verdict_at": dt.datetime.fromtimestamp(verdict, dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}


# ------------------------------------------------------------------ close / summary

ACTORS = ("codex", "advisor", "human")


def parse_interventions(text: str | None) -> dict:
    counts = dict.fromkeys(ACTORS, 0)
    for part in (text or "").split(","):
        if not part.strip():
            continue
        actor, _, n = part.partition("=")
        if actor.strip() not in ACTORS or not n.strip().isdigit():
            raise SystemExit(f"ERROR: --interventions takes codex=N,advisor=N,human=N (got {text!r}); "
                             "say whose action it was")
        counts[actor.strip()] = int(n)
    return counts


def backfill_path() -> Path:
    return runs_path().with_name("interventions_backfill.jsonl")


def interventions(record: dict) -> dict:
    """The three counters of any record: its own (schema 2) or the backfill line for a schema-1 attempt."""
    if "interventions" in record:
        return record["interventions"]
    lines = [b for b in read_jsonl(backfill_path())
             if (b["class"], b["attempt"]) == (record["class"], record["attempt"])]
    if lines:
        return {a: lines[-1][a] for a in ACTORS}
    return {"codex": None, "advisor": None, "human": 0}


def fold(cls: str, events: list[dict], records: list[dict], outcome: str, path: str | None,
         counts: dict, note: str) -> dict:
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
        "schema": 2, "class": cls, "attempt": 1 + sum(1 for r in records if r["class"] == cls),
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
        # HQ 2026-11-11 ruling 6: run-2 expectations stated explicitly per harness run (own vs inherited via base)
        "run2_expected": [h["run2_expected"] for h in harness if h.get("run2_expected")],
        "pregate": [{k: g.get(k) for k in ("status", "findings")} for g in pregates],
        "commits": [c for e in kinds("record") for c in e.get("commits", [])],
        "interventions": counts, "note": note or None,
    }
    record["phases"] = phases(mine, _ts(record["closed_at"]))
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
    record = fold(cls, read_jsonl(events_path()), records, outcome, opt("--path"),
                  parse_interventions(opt("--interventions")), opt("--note", ""))
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
    print(f"- all paths: interventions {intervention_text(records)}")
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
              f"reviewer FAIL rate {f'{fails}/{len(reviews)}' if reviews else None}, "
              f"interventions {intervention_text(rs)}")
    return 0


def intervention_text(records: list[dict]) -> str:
    """codex/advisor/human totals; `?` where a schema-1 record did not count that actor."""
    out = []
    for actor in ACTORS:
        values = [interventions(r)[actor] for r in records]
        known = sum(v for v in values if v is not None)
        out.append(f"{actor} {known}{'+?' if None in values else ''}")
    return ", ".join(out)


def run2_text(record: dict) -> str:
    seen = [r for r in record.get("run2_expected", []) if r]
    if not seen:
        return "none"
    r = seen[-1]
    parts = [f"own {', '.join(r['own'])}"] if r.get("own") else []
    parts += [f"inherited {', '.join(refs)} via {cls}" for cls, refs in sorted(r.get("inherited", {}).items())]
    return "; ".join(parts) + f" ({r.get('hits', 0)} event(s) on the green run)"


def cmd_batch_report(classes: list[str]) -> int:
    records = read_jsonl(runs_path())
    latest = {r["class"]: r for r in records}
    rows, missing = [], [c for c in classes if c not in latest]
    m = lambda v: "–" if v is None else (f"{v / 60:.1f} min" if v >= 60 else f"{v:.0f} s")  # noqa: E731
    print("| class | path | wall (dispatch→verdict) | prep | pregate | harness | codex | record | review | wait | "
          "Codex runs (s, uncached tok, calls) | reverts (median s) | interventions codex/advisor/human | reviewer | "
          "expected run-2 events |")
    print("|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---|---|---|")
    for c in classes:
        if c not in latest:
            continue
        r = latest[c]
        ph = r.get("phases") or {}
        reviews = r.get("reviews") or []
        codex = (f"{r['codex_runs']} ({', '.join(str(round(x)) for x in r['codex_s'])}; "
                 f"{r.get('codex_tokens_uncached', 0):,}; {r['codex_tool_calls']})") if r["codex_runs"] else "0"
        rs = [x for x in r["revert_s"] if isinstance(x, (int, float))]
        rows.append(r)
        print(f"| {c} | {r.get('path')} | {m(ph.get('wall_s'))} | {m(ph.get('prep_s'))} | {m(ph.get('pregate_s'))} | "
              f"{m(ph.get('harness_s'))} | {m(ph.get('codex_s'))} | {m(ph.get('record_s'))} | {m(ph.get('review_s'))} | "
              f"{m(ph.get('wait_s'))} | {codex} | {len(rs)} ({median(rs)}) | "
              f"{'/'.join('?' if v is None else str(v) for v in interventions(r).values())} | "
              f"{reviews[-1]['verdict'] if reviews else '–'} | {run2_text(r)} |")
    greens = [r for r in rows if r["outcome"] in ("GREEN", "PASS")]
    walls = [r["phases"]["wall_s"] for r in rows if (r.get("phases") or {}).get("wall_s")]
    print(f"\n{len(rows)} attempts, {len(greens)} green/pass; Codex runs per green "
          f"{round(sum(r['codex_runs'] for r in rows) / len(greens), 2) if greens else None}; median wall "
          f"{m(median(walls)) if walls else '–'}; reverts {sum(len(r['revert_s']) for r in rows)} "
          f"(median {median([x for r in rows for x in r['revert_s']])} s); interventions {intervention_text(rows)}")
    if missing:
        print(f"no record for: {', '.join(missing)}")
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
    if len(argv) >= 2 and argv[0] == "batch-report":
        return cmd_batch_report([short(c) for c in argv[1:]])
    print(__doc__.strip(), file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
