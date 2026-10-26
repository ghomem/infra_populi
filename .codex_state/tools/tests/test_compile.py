"""Step 2.2: compile-only mode, facts rewrite, composite expectations, and the master-side filter."""

import importlib.util
import json
import os
import subprocess
import sys

import pytest

from conftest import TOOLS

sys.dont_write_bytecode = True


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


facts = load("facts", TOOLS / "compile" / "facts.py")
cc = load("composite_compile", TOOLS / "composite_compile.py")
HARNESS = str(TOOLS / "test_class.sh")


def test_redhat_facts_rewrite_only_os_family_fields():
    node = {"os": {"family": "Debian", "name": "Ubuntu", "release": {"major": "24.04"}, "distro": {"codename": "noble"},
                   "architecture": "amd64"}, "networking": {"fqdn": "puppet8node"}}
    out = facts.transform(node, "redhat")
    assert out["os"]["family"] == "RedHat" and out["os"]["release"]["major"] == "9"
    assert "distro" not in out["os"] and out["os"]["architecture"] == "amd64"
    assert out["networking"] == node["networking"] and node["os"]["family"] == "Debian"
    assert facts.transform(node, "debian") is node


def test_facts_yaml_document_shape():
    text = facts.to_yaml({"a": "b"})
    assert text.startswith("--- !ruby/object:Puppet::Node::Facts\nname: puppet8node\nvalues: ")
    assert json.loads(text.split("values: ", 1)[1]) == {"a": "b"}


def test_composites_file_parses_and_rejects_bad_rows():
    rows = cc.parse_composites((TOOLS / "compile" / "composites.txt").read_text())
    assert {r["name"] for r in rows} >= {"node_base_debian", "node_base_redhat", "meaningful_desktop"}
    with pytest.raises(SystemExit):
        cc.parse_composites("x | suse | pass | a\n")


def test_judge_matches_expectations():
    assert cc.judge("pass", 0, "COMPILE OK") == (True, "pass")
    ok, outcome = cc.judge("fail:Could not find class ::ntp", 1, "Error: Could not find class ::ntp for x\n")
    assert ok and outcome.startswith("fail: Error: Could not find class ::ntp")
    assert cc.judge("fail:Could not find class ::ntp", 0, "")[0] is False  # unexpectedly fixed -> DIFF
    assert cc.judge("pass", 1, "Error: Duplicate declaration\n")[0] is False


def test_first_error_joins_continuation_lines():
    out = "Warning: w\nError: Evaluation Error: Class[X]:\n  expects a value for parameter 'ip'\nCOMPILE_FAILED\n"
    assert cc.first_error(out) == "Error: Evaluation Error: Class[X]: expects a value for parameter 'ip'"


def test_compile_only_never_runs_the_agent_and_maps_exit_codes(lab):
    lab.world["ssh"].insert(0, {"match": r"puppet facts show", "stdout": json.dumps({"os": {"family": "Debian"}})})
    lab.world["ssh"].insert(0, {"match": r"run\.sh", "rc": 5, "stdout": "Error: boom\nCOMPILE_FAILED: x\n"})
    proc = lab.run([HARNESS, "--compile-only", "--no-expand", "puppet_infrastructure::puppet_backup"])
    assert proc.returncode == 1 and "COMPILE FAILED (debian)" in proc.stderr
    assert not any("agent -t" in " ".join(c) for c in lab.calls("ssh"))
    assert lab.calls("VBoxManage") == []


def test_compile_only_ok(lab):
    lab.world["ssh"].insert(0, {"match": r"puppet facts show", "stdout": "{}"})
    lab.world["ssh"].insert(0, {"match": r"run\.sh", "stdout": "COMPILE_COVERAGE x: 2 concrete\n"})
    proc = lab.run([HARNESS, "--compile-only", "--facts", "redhat", "puppet_infrastructure::puppet_backup"])
    assert proc.returncode == 0, proc.stderr
    assert "COMPILE OK (redhat)" in proc.stdout


def test_compile_only_rejects_unknown_facts_variant(lab):
    assert lab.run([HARNESS, "--compile-only", "--facts", "suse", "puppet_infrastructure::x"]).returncode == 1


LAB = pytest.mark.skipif(not os.environ.get("P8_LAB_TESTS"), reason="needs puppet8master (set P8_LAB_TESTS=1)")
SECRET = "P8TEST-SECRET-MARKER"


def run_filter(stdin: str, *targets: str) -> subprocess.CompletedProcess:
    import base64
    script = base64.b64encode((TOOLS / "compile" / "filter.rb").read_bytes()).decode()
    cmd = (f'd=$(mktemp -d) && echo {script} | base64 -d > "$d/f.rb" && cat > "$d/in" && '
           f'/opt/puppetlabs/puppet/bin/ruby "$d/f.rb" {" ".join(targets)} < "$d/in"; rc=$?; rm -rf "$d"; exit $rc')
    return subprocess.run(["ssh", "-T", "puppet8master", cmd], input=stdin, capture_output=True, text=True, timeout=60)


@LAB
def test_filter_prints_titles_never_parameters_on_the_master():
    catalog = {"tags": [], "classes": ["puppet_infrastructure::a", "passwd_common"], "resources": [
        {"type": "File", "title": "/x", "tags": ["puppet_infrastructure::a"], "parameters": {"content": SECRET}},
        {"type": "User", "title": "p8user", "tags": ["passwd_common"], "parameters": {"password": SECRET}}]}
    proc = run_filter("Notice: Compiled catalog\n" + json.dumps(catalog), "puppet_infrastructure::a")
    assert proc.returncode == 0, proc.stderr
    assert "COMPILE_COVERAGE puppet_infrastructure::a: 1 concrete" in proc.stdout and "File[/x]" in proc.stdout
    assert "PASSWD_COMMON: 1 resources" in proc.stdout
    assert SECRET not in proc.stdout + proc.stderr


@LAB
def test_filter_withholds_unparseable_input_on_the_master():
    proc = run_filter('Notice: x\n{"tags": [ broken ' + SECRET, "puppet_infrastructure::a")
    assert proc.returncode == 4
    assert SECRET not in proc.stdout + proc.stderr


@LAB
def test_filter_empty_target_exit_code_on_the_master():
    proc = run_filter(json.dumps({"tags": [], "classes": [], "resources": []}), "puppet_infrastructure::a")
    assert proc.returncode == 3
