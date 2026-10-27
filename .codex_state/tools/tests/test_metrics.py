"""Per-attempt metrics (step 3.4): events fold into one tracked record per attempt."""

import importlib.util
import json
import os
import sys
import time

import pytest

from conftest import TOOLS

spec = importlib.util.spec_from_file_location("metrics", TOOLS / "metrics.py")
metrics = importlib.util.module_from_spec(spec)
sys.modules["metrics"] = metrics
spec.loader.exec_module(metrics)

SUMMARY = """---
version:
  config: 1793073395
  puppet: 8.24.2
resources:
  changed: 9
  corrective_change: 0
  failed: 0
  total: 26
time:
  config_retrieval: 0.38
  catalog_application: 1.5
  total: 10.4
events:
  failure: 0
  success: 9
  total: 9
transaction_uuid: 36c7b658-542d-4c65-9f2f-e5b2071f410c
"""


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("P8_METRICS_DIR", str(tmp_path / "events"))
    monkeypatch.setenv("P8_RUNS_FILE", str(tmp_path / "runs" / "metrics.jsonl"))
    return tmp_path


def test_agent_summary_keeps_counts_times_and_uuid():
    s = metrics.agent_summary(SUMMARY)
    assert s["transaction_uuid"] == "36c7b658-542d-4c65-9f2f-e5b2071f410c"
    assert (s["res_total"], s["res_changed"], s["events"], s["t_total"]) == (26, 9, 9, 10.4)


def test_events_fold_into_one_attempt_record(env):
    metrics.add_event("backup", "path", {"path": "unchanged-validated"})
    metrics.add_event("backup", "revert", {"total_s": 33.0})
    metrics.add_event("backup", "harness", {"rc": 0, "revert_first": True, "run1_events": 9, "duration_s": 61.2,
                                            "agent_runs": [metrics.agent_summary(SUMMARY)]})
    metrics.add_event("other", "harness", {"rc": 1})
    metrics.add_event("backup", "record", {"commits": ["abc1234"]})
    metrics.add_event("backup", "review", {"verdict": "PASS", "failed_checks": [], "check_s": 140.0})
    assert metrics.main(["close", "backup", "--outcome", "PASS", "--no-commit"]) == 0
    (record,) = metrics.read_jsonl(metrics.runs_path())
    assert record["class"] == "backup" and record["attempt"] == 1 and record["outcome"] == "PASS"
    assert record["path"] == "unchanged-validated" and record["codex_runs"] == 0 and record["executor"] is None
    assert record["revert_s"] == [33.0] and record["harness_runs"] == 1 and record["harness_green"] == 1
    assert record["agent_runs"][0]["res_changed"] == 9 and record["commits"] == ["abc1234"]
    assert record["reviews"][0]["verdict"] == "PASS"


def test_second_close_counts_only_new_events_and_increments_attempt(env):
    metrics.add_event("x", "harness", {"rc": 1})
    metrics.main(["close", "x", "--outcome", "FAILED", "--no-commit"])
    metrics.add_event("x", "harness", {"rc": 0})
    metrics.main(["close", "x", "--outcome", "GREEN", "--no-commit", "--interventions", "1", "--note", "fixture"])
    first, second = metrics.read_jsonl(metrics.runs_path())
    assert (first["attempt"], second["attempt"]) == (1, 2)
    assert second["harness_runs"] == 1 and second["harness_green"] == 1
    assert second["human_interventions"] == 1 and second["note"] == "fixture"


def test_close_rejects_unknown_outcome(env):
    with pytest.raises(SystemExit):
        metrics.main(["close", "x", "--outcome", "MAYBE", "--no-commit"])


def write_rollout(path, cwd, started, tokens, calls, originator="codex_exec"):
    lines = [{"type": "session_meta", "payload": {"timestamp": started, "cwd": cwd, "originator": originator,
                                                   "cli_version": "0.159.2", "creator_user_id": "user-SECRET"}},
             {"type": "turn_context", "payload": {"model": "gpt-6.1-sol", "effort": "xhigh"}}]
    lines += [{"type": "response_item", "payload": {"type": "custom_tool_call"}}] * calls
    lines.append({"type": "event_msg", "payload": {"type": "token_count", "info": {"total_token_usage":
                  {"input_tokens": tokens - 100, "output_tokens": 100, "total_tokens": tokens}}}})
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(l) for l in lines) + "\n")


def test_codex_usage_sums_this_repos_exec_sessions_since_start_and_drops_account_ids(tmp_path):
    since = time.time() - 5
    iso = lambda t: time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime(t))  # noqa: E731
    write_rollout(tmp_path / "s/2026/10/27/rollout-a.jsonl", "/repo", iso(since + 1), 48000, 16)
    write_rollout(tmp_path / "s/2026/10/27/rollout-b.jsonl", "/other", iso(since + 1), 999, 1)
    write_rollout(tmp_path / "s/2026/10/27/rollout-c.jsonl", "/repo", iso(since - 3600), 777, 1)
    write_rollout(tmp_path / "s/2026/10/27/rollout-d.jsonl", "/repo", iso(since + 1), 555, 1, originator="codex_tui")
    usage = metrics.codex_usage(since, tmp_path / "s", "/repo")
    assert usage["sessions"] == 1 and usage["total_tokens"] == 48000 and usage["tool_calls"] == 16
    assert (usage["model"], usage["effort"], usage["cli_version"]) == ("gpt-6.1-sol", "xhigh", "0.159.2")
    assert "SECRET" not in json.dumps(usage)


def test_summary_runs(env, capsys):
    metrics.add_event("x", "codex", {"rc": 0, "codex_s": 200.0, "usage": {"total_tokens": 50000, "tool_calls": 12,
                                                                          "model": "m", "cli_version": "v", "effort": "e"}})
    metrics.main(["close", "x", "--outcome", "PASS", "--path", "syntax-work", "--no-commit"])
    assert metrics.main(["summary"]) == 0
    out = capsys.readouterr().out
    assert "syntax-work: 1 attempts, 1 green/pass" in out and "codex runs/green 1.0" in out
