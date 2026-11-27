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
    proc = lab.run([HARNESS, "--compile-only", "--no-expand", "infra_populi::puppet_backup"])
    assert proc.returncode == 1 and "COMPILE FAILED (debian)" in proc.stderr
    assert not any("agent -t" in " ".join(c) for c in lab.calls("ssh"))
    assert lab.calls("VBoxManage") == []


def test_compile_only_ok(lab):
    lab.world["ssh"].insert(0, {"match": r"puppet facts show", "stdout": "{}"})
    lab.world["ssh"].insert(0, {"match": r"run\.sh", "stdout": "COMPILE_COVERAGE x: 2 concrete\n"})
    proc = lab.run([HARNESS, "--compile-only", "--facts", "redhat", "infra_populi::puppet_backup"])
    assert proc.returncode == 0, proc.stderr
    assert "COMPILE OK (redhat)" in proc.stdout


def test_compile_only_rejects_unknown_facts_variant(lab):
    assert lab.run([HARNESS, "--compile-only", "--facts", "suse", "infra_populi::x"]).returncode == 1


def test_compile_only_file_digest_ships_the_titles_to_the_master(lab):
    # HQ 2026-11-18 ruling A1: rendered nginx.conf byte-identical before/after; the titles travel in the work tarball.
    lab.world["read_stdin"] = True
    lab.world["ssh"].insert(0, {"match": r"puppet facts show", "stdout": "{}"})
    lab.world["ssh"].insert(0, {"match": r"run\.sh.*digest_paths.*/etc/nginx/nginx\.conf",
                                "stdout": "FILE_DIGEST /etc/nginx/nginx.conf: sha256:ab bytes:1\n"})
    proc = lab.run([HARNESS, "--compile-only", "--file-digest", "/etc/nginx/nginx.conf",
                    "infra_populi::puppet_backup"])
    assert proc.returncode == 0, proc.stderr
    assert "FILE_DIGEST /etc/nginx/nginx.conf: sha256:ab" in proc.stdout


def test_compile_only_file_digest_needs_an_absolute_title(lab):
    proc = lab.run([HARNESS, "--compile-only", "--file-digest", "nginx.conf", "infra_populi::x"])
    assert proc.returncode == 1 and "absolute File title" in proc.stderr


LAB = pytest.mark.skipif(not os.environ.get("P8_LAB_TESTS"), reason="needs puppet8master (set P8_LAB_TESTS=1)")
SECRET = "P8TEST-SECRET-MARKER"


def run_filter(stdin: str, *targets: str, digest: str = "") -> subprocess.CompletedProcess:
    import base64
    script = base64.b64encode((TOOLS / "compile" / "filter.rb").read_bytes()).decode()
    paths = f'echo {base64.b64encode(digest.encode()).decode()} | base64 -d > "$d/digest_paths" && ' if digest else ""
    cmd = (f'd=$(mktemp -d) && echo {script} | base64 -d > "$d/f.rb" && {paths}cat > "$d/in" && '
           f'/opt/puppetlabs/puppet/bin/ruby "$d/f.rb" {" ".join(targets)} < "$d/in"; rc=$?; rm -rf "$d"; exit $rc')
    return subprocess.run(["ssh", "-T", "puppet8master", cmd], input=stdin, capture_output=True, text=True, timeout=60)


@LAB
def test_filter_prints_titles_never_parameters_on_the_master():
    catalog = {"tags": [], "classes": ["infra_populi::a", "passwd_common"], "resources": [
        {"type": "File", "title": "/x", "tags": ["infra_populi::a"], "parameters": {"content": SECRET}},
        {"type": "User", "title": "p8user", "tags": ["passwd_common"], "parameters": {"password": SECRET}}]}
    proc = run_filter("Notice: Compiled catalog\n" + json.dumps(catalog), "infra_populi::a")
    assert proc.returncode == 0, proc.stderr
    assert "COMPILE_COVERAGE infra_populi::a: 1 concrete" in proc.stdout and "File[/x]" in proc.stdout
    assert "PASSWD_COMMON: 1 resources" in proc.stdout
    assert SECRET not in proc.stdout + proc.stderr


@LAB
def test_filter_withholds_unparseable_input_on_the_master():
    proc = run_filter('Notice: x\n{"tags": [ broken ' + SECRET, "infra_populi::a")
    assert proc.returncode == 4
    assert SECRET not in proc.stdout + proc.stderr


@LAB
def test_filter_file_digest_hashes_never_prints_content_on_the_master():
    import hashlib
    catalog = {"tags": [], "classes": ["infra_populi::a"], "resources": [
        {"type": "File", "title": "/etc/a.conf", "tags": ["infra_populi::a"], "parameters": {"content": SECRET}},
        {"type": "File", "title": "/etc/dir", "tags": ["infra_populi::a"], "parameters": {"ensure": "directory"}},
        {"type": "File", "title": "/etc/pw", "tags": ["passwd_common"], "parameters": {"content": SECRET}}]}
    proc = run_filter(json.dumps(catalog), "infra_populi::a", digest="/etc/a.conf\n/etc/dir\n/etc/pw\n/etc/none\n")
    assert proc.returncode == 0, proc.stderr
    want = hashlib.sha256(SECRET.encode()).hexdigest()
    assert f"FILE_DIGEST /etc/a.conf: sha256:{want} bytes:{len(SECRET)}" in proc.stdout
    assert "FILE_DIGEST /etc/dir: no content parameter" in proc.stdout
    assert "FILE_DIGEST /etc/pw: withheld (passwd_common" in proc.stdout
    assert "FILE_DIGEST /etc/none: not in the catalog" in proc.stdout
    assert SECRET not in proc.stdout + proc.stderr


@LAB
def test_filter_empty_target_exit_code_on_the_master():
    proc = run_filter(json.dumps({"tags": [], "classes": [], "resources": []}), "infra_populi::a")
    assert proc.returncode == 3


def test_composites_compile_on_the_default_node_whatever_the_classes_lab_nodes(monkeypatch):
    # 2026-11-17: user_kde_lock_screen moved to kubuntu; the meaningful_desktop composite mixes it with default-node
    # classes. The facts are synthetic, so the compile names the inventory's default node explicitly.
    seen = {}

    def fake_run(argv, **kw):
        seen["argv"] = argv
        return subprocess.CompletedProcess(argv, 0, "COMPILE OK\n", "")
    monkeypatch.setattr(cc.subprocess, "run", fake_run)
    cc.compile_only(["user_kde_lock_screen", "packages_base"], "debian")
    argv = seen["argv"]
    assert argv[1:3] == ["--node", "ubuntu"] and argv[3] == "--compile-only"
    assert argv[-2:] == ["infra_populi::user_kde_lock_screen", "infra_populi::packages_base"]


def test_composites_report_the_environment_when_the_default_node_is_down(monkeypatch, capsys):
    monkeypatch.setattr(cc, "default_node_answers", lambda: (False, "puppet8node"))
    monkeypatch.setattr(cc, "compile_only", lambda *a, **k: pytest.fail("no compile without the node's facts"))
    assert cc.run_composites() == 3
    assert "COMPOSITES: ENVIRONMENT — the default node puppet8node does not answer" in capsys.readouterr().out
