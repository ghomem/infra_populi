"""The public runner against a simulated node (no machine needed)."""
import json
import sys
from pathlib import Path

import pytest

SUITE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SUITE / "lib"))
from behaviour import manifest as mf  # noqa: E402
from behaviour import results, runner, setfile  # noqa: E402

SET = SUITE / "checks" / "filesystem_lib64.yml"


class FakeNode:
    """A node that has the class's link only after an apply, and the plugin only after the action installs it."""

    def __init__(self, run2_events=0, apply_rc=2):
        self.applied = self.installed = False
        self.runs = []
        self.run2_events, self.apply_rc = run2_events, apply_rc
        self.marked = False

    def run(self, m, script, timeout=120, prefix="", root=True):
        if "behaviour-suite/used" in script:
            out = "USED" if self.marked else ""
            self.marked = True
            return 0, out, ""
        if "boot_id" in script:
            return 0, "b00t\n", ""
        if script.startswith("hostname -s"):
            return 0, "p8test-node\n", ""
        if "SSH_CLIENT" in script:
            return 0, "203.0.113.9\n", ""
        if "facter" in script:
            return 0, "203.0.113.20\n", ""
        if "puppet agent -t" in script or "puppet apply" in script:
            self.runs.append(script)
            if len(self.runs) == 1:
                self.applied = True
                return 0, "Notice: /Stage[main]/X/File[/usr/lib64]/ensure: created\nAGENT_RC=2\n", ""
            ev = "Notice: /Stage[main]/X/File[/usr/lib64]/mode: changed\n" * self.run2_events
            return 0, f"{ev}AGENT_RC={2 if self.run2_events else 0}\n", ""
        if "apt-get" in script:
            self.installed = True
            return 0, "", ""
        if "readlink" in script:
            return (0, "directory root:root\n/usr/lib/nagios\n", "") if self.applied else (1, "", "no such file")
        if "check_disk" in script:
            return (0, "DISK OK\n", "") if self.applied and self.installed else (127, "", "not found")
        raise AssertionError(f"unexpected script: {script[:80]}")


def make(node: FakeNode, mode="agent"):
    shell = runner.Shell(["ssh"])
    shell.run = node.run
    provider = runner.Provider(shell, None, {"ubuntu": [runner.Machine("ubuntu", "p8test@node", "203.0.113.20")]})
    applier = runner.Applier(mode, shell, modulepath="/opt/p8test/modules")
    return runner.Run(SET, provider, applier, shell, {"name": "puppet.example.invalid", "addr": "203.0.113.10"},
                      "/opt/site")


def test_a_set_whose_class_does_its_work_passes():
    node = FakeNode()
    record = make(node).run("agent", None, say=lambda *_: None)
    assert record["outcome"] == "ALL_PASS", record["problems"]
    assert [r["ok"] for r in record["clean"]] == [True, True]
    assert record["applied"][1]["mutating"] and record["applied"][1]["action"]["rc"] == 0
    assert record["nodes"]["node"]["fresh"] is True
    assert len(node.runs) == 2


def test_a_second_run_that_changes_something_fails_the_gate():
    record = make(FakeNode(run2_events=1)).run("agent", None, say=lambda *_: None)
    assert record["outcome"] == "APPLY_FAILED"


def test_a_used_node_is_refused():
    node = FakeNode()
    node.marked = True
    record = make(node).run("agent", None, say=lambda *_: None)
    assert record["outcome"] == "ENVIRONMENT_FAILED" and "not fresh" in record["problems"][0]


def test_local_mode_applies_the_built_manifest_with_puppet_apply():
    node = FakeNode()
    record = make(node, "local").run("local", None, say=lambda *_: None)
    assert record["outcome"] == "ALL_PASS"
    assert all("puppet apply" in r and "/opt/p8test/modules" in r for r in node.runs)


def test_a_negative_control_that_holds_on_the_clean_node_makes_the_set_invalid():
    node = FakeNode()
    node.applied = True  # the node already has what the class makes
    record = make(node).run("agent", None, say=lambda *_: None)
    assert record["outcome"] == "INVALID_SET"


def test_the_manifest_follows_the_catalog_with_params_fixtures(tmp_path):
    (tmp_path / "for" / "x").mkdir(parents=True)
    (tmp_path / "for" / "x" / "b.json").write_text(json.dumps({"peer": "{{PEER_ADDR}}"}))
    (tmp_path / "x.json").write_text(json.dumps({"names": ["a'b"], "on": True}))
    data = {"class": "x", "apply": {"resource_type": "class", "node": "ubuntu", "catalog": {
        "Debian": [{"external": "stdlib"}, {"class": "a"}, {"class": "b"}, {"class": "x"}]}}}
    text = mf.build(data, "ubuntu", setfile.kinds(), [tmp_path], tmp_path,
                    render=lambda t: t.replace("{{PEER_ADDR}}", "203.0.113.5"))
    assert text.splitlines() == [
        "include stdlib", "include puppet_infrastructure::a",
        "class { 'puppet_infrastructure::b':", "  peer => '203.0.113.5',", "}",
        "class { 'puppet_infrastructure::x':", "  names => ['a\\'b'],", "  on => true,", "}"]


def test_a_define_without_params_fixture_cannot_be_built(tmp_path):
    data = {"class": "x", "apply": {"resource_type": "define", "title": "p8test0", "node": "ubuntu",
                                    "catalog": {"Debian": [{"class": "x"}]}}}
    with pytest.raises(FileNotFoundError):
        mf.build(data, "ubuntu", setfile.kinds(), [tmp_path], tmp_path)


def test_the_junit_report_counts_a_finding():
    rec = {"outcome": "FINDINGS", "clean": [{"id": "a", "control": "negative", "ok": True, "rc": 1, "stdout": "",
                                              "stderr": ""}],
           "applied": [{"id": "a", "control": "negative", "passed": False, "rc": 1, "stdout": "", "stderr": ""}]}
    xml = results.junit("x", rec).decode()
    assert 'name="behaviour.x.applied" tests="1" failures="1"' in xml


def test_the_worst_outcome_wins():
    assert results.combined(["ALL_PASS", "FINDINGS", "SKIPPED"]) == "FINDINGS"
    assert results.combined(["ALL_PASS", None]) == "ENVIRONMENT_FAILED"


def test_a_base_define_is_declared_with_its_title(tmp_path):
    (tmp_path / "user_base.json").write_text(json.dumps({"uid": 2001}))
    data = {"class": "x", "apply": {"resource_type": "class", "node": "ubuntu", "catalog": {
        "Debian": [{"class": "user_base", "define": "p8testuser"}, {"class": "x"}]}}}
    text = mf.build(data, "ubuntu", setfile.kinds(), [tmp_path], tmp_path)
    assert text.splitlines()[:3] == ["puppet_infrastructure::user_base { 'p8testuser':", "  uid => 2001,", "}"]


def test_a_node_fixture_is_rendered_with_the_run(tmp_path):
    (tmp_path / "node").mkdir()
    (tmp_path / "node" / "p8x.pp").write_text("# a fixture\nhost { 'peer': ip => '{{PEER_ADDR}}' }\n")
    data = {"class": "x", "apply": {"resource_type": "class", "node": "ubuntu", "node_fixture": "p8x",
                                    "catalog": {"Debian": [{"class": "x"}]}}}
    text = mf.build(data, "ubuntu", setfile.kinds(), [tmp_path], tmp_path,
                    render=lambda t: t.replace("{{PEER_ADDR}}", "203.0.113.5"))
    assert "host { 'peer': ip => '203.0.113.5' }" in text


def test_an_error_puppet_logs_without_failing_the_run_fails_the_gate():
    first = runner.agent_result(0, "Notice: /Stage[main]/X/Exec[e]/returns: executed successfully\nAGENT_RC=2\n", "")
    second = runner.agent_result(0, "Error: /Stage[main]/X/Exec[e]/unless: Check \"x\" exceeded timeout\n"
                                    "Notice: Applied catalog in 300.21 seconds\nAGENT_RC=0\n", "")
    assert second["rc"] == 0 and not second["events"] and second["errors"]
    assert runner.gate(first, second, []) is False
    clean = runner.agent_result(0, "Notice: Applied catalog in 3.1 seconds\nAGENT_RC=0\n", "")
    assert runner.gate(first, clean, []) is True


def test_an_expected_run2_event_may_carry_a_wildcard():
    first = runner.agent_result(0, "AGENT_RC=2\n", "")
    second = runner.agent_result(0, "Notice: /Stage[main]/X/Notify[sync p8test0]/message: defined 'message' as 'x'\n"
                                    "AGENT_RC=2\n", "")
    assert runner.gate(first, second, ["Notify[sync *]"]) is True
    assert runner.gate(first, second, ["Notify[other *]"]) is False


def test_a_change_no_log_line_shows_is_still_an_event():
    second = runner.agent_result(0, "Notice: Applied catalog in 0.96 seconds\nAGENT_RC=2\nCHANGED Exec[quiet]\n", "")
    assert second["events"] == ["CHANGED Exec[quiet]"]
    first = runner.agent_result(0, "AGENT_RC=2\n", "")
    assert runner.gate(first, second, []) is False
    assert runner.gate(first, second, ["Exec[quiet]"]) is True
    logged = runner.agent_result(0, "Notice: /Stage[main]/X/Exec[e]/returns: executed successfully\nAGENT_RC=2\n"
                                    "CHANGED Exec[e]\n", "")
    assert len(logged["events"]) == 1


def test_every_root_script_starts_with_the_helpers_and_node_scripts_get_the_peer_address_only_with_a_peer(monkeypatch):
    seen = []

    class Done:
        returncode, stdout, stderr = 0, "", ""
    monkeypatch.setattr(runner.subprocess, "run", lambda *a, **k: (seen.append(k["input"]), Done())[1])
    shell = runner.Shell(["ssh"])
    node = runner.Machine("ubuntu", "p8test@node", "203.0.113.20")
    run = runner.Run(SET, runner.Provider(shell, None, {}), runner.Applier("agent", shell), shell,
                     {"name": "puppet.example.invalid", "addr": "203.0.113.10"}, "/opt/site")
    run.on({"id": "x"}, "echo a", node, None, {"PEER_ADDR": "198.51.100.1"})
    run.data = {**run.data, "peer": {"kind": "ubuntu2"}}
    run.on({"id": "x"}, "echo b", node, None, {"PEER_ADDR": "203.0.113.24"})
    shell.run(node, "echo c", root=False)
    assert seen == [runner.HELPERS + "echo a", runner.HELPERS + "PEER_ADDR=203.0.113.24\necho b", "echo c"]
