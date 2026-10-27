"""pregate: laptop-side scanners, remote-output parsing, lint inheritance, staged (pre-commit) mode."""

import importlib.util
import subprocess
import sys

import pytest

from conftest import TOOLS

sys.path.insert(0, str(TOOLS))
sys.path.insert(1, str(TOOLS.parent))
spec = importlib.util.spec_from_file_location("pregate", TOOLS / "pregate.py")
pregate = importlib.util.module_from_spec(spec)
sys.modules["pregate"] = pregate
spec.loader.exec_module(pregate)

UNGUARDED_OS = """class puppet_infrastructure::x {
  $v = $facts['os']['release']['major']
  exec { 'install-epel':
    command => "dnf install -y epel-release-${v}",
    unless  => 'rpm -q epel-release',
  }
}
"""
GUARDED_OS = """class puppet_infrastructure::y {
  case $facts['os']['family'] {
    'RedHat': {
      exec { 'dnf-makecache': command => '/usr/bin/dnf makecache', refreshonly => true }
    }
    default: {}
  }
}
"""


def findings(report, check=None):
    return [d for lvl, c, d in report.lines if lvl == "FINDING" and (check is None or c == check)]


def test_os_exec_outside_conditional_is_a_finding_even_if_file_mentions_os_facts():
    r = pregate.Report("x")
    pregate.scan_hazards(UNGUARDED_OS, None, r)
    assert findings(r, "hazard5-os-exec") == ["exec 'install-epel' runs an OS-specific command with no enclosing OS conditional"]
    assert findings(r, "hazard9-exec-guard") == []


def test_os_exec_inside_case_branch_is_guarded():
    r = pregate.Report("y")
    pregate.scan_hazards(GUARDED_OS, None, r)
    assert findings(r) == []


def test_unguarded_exec_is_a_finding():
    r = pregate.Report("z")
    pregate.scan_hazards("exec { 'p8test': command => '/bin/true' }\n", None, r)
    assert len(findings(r, "hazard9-exec-guard")) == 1


def test_connectivity_and_stdlib_findings():
    r = pregate.Report("f")
    pregate.scan_hazards("firewallchain { 'OUTPUT:filter:IPv4': policy => drop, purge => true }\n"
                         "if is_string($a) { validate_re($a, 'x') }\n", None, r)
    assert len(findings(r, "hazard2-connectivity")) == 2
    assert sorted(findings(r, "hazard6-stdlib")) == ["calls `is_string()`, removed in stdlib 9",
                                                     "calls `validate_re()`, removed in stdlib 9"]


def test_missing_module_types_and_classes_use_master_inventory():
    inv = {"modules": {"apt"}, "types": {"firewall"}, "defines": {"apt", "apt::source"}}
    manifest = ("include apt\ninclude ::ntp\nclass { 'nginx': }\n"
                "firewall { '100 x': }\nhtpasswd { $u: }\napt::source { 'a': }\nfile { '/x': }\n"
                "puppet_infrastructure::backup { 'b': }\n")
    r = pregate.Report("m")
    pregate.scan_hazards(manifest, inv, r)
    got = findings(r, "hazard1-types")
    assert any("`htpasswd`" in g for g in got) and any("`ntp`" in g for g in got) and any("`nginx`" in g for g in got)
    assert len(got) == 3


def test_method_call_before_a_block_is_not_a_resource_type():
    # node_base.pp:138 `if $ntp_servers.empty {` (found by the 3.3 path sweep: false hazard1 `empty`)
    manifest = "class x { if $ntp_servers.empty { notify { 'n': } } }"
    assert "empty" not in pregate.resource_types(manifest) and "notify" in pregate.resource_types(manifest)


def test_comments_are_not_code():
    r = pregate.Report("c")
    pregate.scan_hazards("# exec { 'old': command => 'dnf install x' }\n# validate_re($x)\n", None, r)
    assert findings(r) == []


def test_template_legacy_facts_skip_class_variables_and_count():
    r = pregate.Report("t")
    pregate.scan_template("templates/a/main.cf", "<%= @hostname %> <%= @hostname %> <%= @domain %> <%= @relayhost %>",
                          {"domain", "relayhost"}, r)
    assert findings(r) == ["templates/a/main.cf: `@hostname` x2 renders EMPTY on Puppet 8 (legacy fact)"]
    r = pregate.Report("e")
    pregate.scan_template("templates/a/x.epp", "<%= $::fqdn %> <%= $facts['os'] %>", set(), r)
    assert findings(r) == ["templates/a/x.epp: `$::fqdn` x1 top-scope/legacy fact"]


REMOTE_OUT = """@@VERSION puppet 8.24.2
@@VERSION puppet-lint 4.3.0
@@BEGIN parse local manifests/a.pp 1
Error: Could not parse for environment production: Syntax error at '}' (file: /tmp/x/local/manifests/a.pp, line: 3)
@@END
@@BEGIN lint local manifests/a.pp 1
[[{"kind":"warning","check":"legacy_facts","message":"legacy fact 'osfamily'","line":4},{"kind":"warning","check":"parameter_order","message":"optional parameter listed before required parameter","line":2}]]
@@END
@@BEGIN lint base manifests/a.pp 1
[[{"kind":"warning","check":"legacy_facts","message":"legacy fact 'osfamily'","line":9}]]
@@END
@@TYPE firewall
@@DEFINE apt::source
"""


def test_parse_remote_and_lint_inheritance():
    versions, results, inv = pregate.parse_remote(REMOTE_OUT)
    assert versions == {"puppet": "8.24.2", "puppet-lint": "4.3.0"}
    assert inv["types"] == {"firewall"} and inv["defines"] == {"apt::source"}
    r = pregate.Report("a")
    pregate.apply_remote(results, r, report_inherited=True)
    got = dict((c, d) for lvl, c, d in r.lines if lvl == "FINDING")
    assert "Syntax error" in got["parse"]
    assert got["lint:legacy_facts"].endswith("(also in baseline)")  # same finding, different line
    assert got["lint:parameter_order"].endswith("(NEW vs baseline)")
    r2 = pregate.Report("a")
    pregate.apply_remote(results, r2, report_inherited=False)
    assert [c for lvl, c, _ in r2.lines if lvl == "FINDING"] == ["parse", "lint:parameter_order"]


def test_identical_file_without_base_copy_counts_findings_as_inherited():
    out = REMOTE_OUT.split("@@BEGIN lint base")[0]
    _, results, _ = pregate.parse_remote(out)
    r = pregate.Report("a")
    pregate.apply_remote(results, r, report_inherited=False, identical_to_baseline=frozenset({"manifests/a.pp"}))
    assert [c for lvl, c, _ in r.lines if lvl == "FINDING"] == ["parse"]


def test_remote_script_never_fixes_and_base_side_is_lint_only():
    assert "--fix" not in pregate.REMOTE
    assert "base:*.pp) out=\"$($L --json" in pregate.REMOTE
    assert "base:templates" not in pregate.REMOTE


def test_status_and_exit_codes():
    r = pregate.Report("s")
    assert r.status == "CLEAN"
    r.add("WARN", "x", "y")
    assert r.status == "CLEAN"
    r.add("FINDING", "x", "y")
    assert r.status == "FINDINGS"
    r.add("ERROR", "x", "y")
    assert r.status == "ERROR"


def test_usage_errors():
    assert pregate.main([]) == 2
    assert pregate.main(["../etc"]) == 2


@pytest.fixture
def staged_repo(tmp_path, monkeypatch):
    """A scratch repo + scratch upstream; pregate.REPO and the baseline pin point at them."""
    def git(cwd, *a):
        return subprocess.run(["git", "-C", str(cwd), *a], check=True, capture_output=True, text=True).stdout.strip()
    up, repo = tmp_path / "up", tmp_path / "repo"
    for r in (up, repo):
        r.mkdir()
        git(r, "init", "-q")
        git(r, "config", "user.email", "t@example.invalid")
        git(r, "config", "user.name", "t")
    (up / "manifests").mkdir()
    (up / "manifests/a.pp").write_text("class a {}\n")
    git(up, "add", "-A")
    git(up, "commit", "-qm", "base")
    base = pregate.baseline.Baseline("release-test", git(up, "rev-parse", "HEAD"), up)
    monkeypatch.setattr(pregate.baseline, "load", lambda: base)
    monkeypatch.setattr(pregate, "REPO", repo)
    sent = []

    def fake_remote(tar_bytes, inventory):
        sent.append(tar_bytes)
        return fake_remote.output
    fake_remote.output = "@@VERSION puppet 8.24.2\n"
    monkeypatch.setattr(pregate, "run_remote", fake_remote)
    (repo / "manifests").mkdir()
    return repo, git, sent, fake_remote


def test_staged_verbatim_baseline_is_not_sent_to_the_master(staged_repo):
    repo, git, sent, _ = staged_repo
    (repo / "manifests/a.pp").write_text("class a {}\n")
    git(repo, "add", "manifests/a.pp")
    report = pregate.pregate_staged()
    assert report.status == "CLEAN" and sent == []
    assert report.lines[0][1] == "baseline-verbatim"


def test_staged_changed_manifest_with_parse_error_blocks(staged_repo):
    repo, git, sent, remote = staged_repo
    (repo / "manifests/a.pp").write_text("class a { \n")
    git(repo, "add", "manifests/a.pp")
    remote.output = ("@@VERSION puppet 8.24.2\n@@BEGIN parse local manifests/a.pp 1\nError: Syntax error\n@@END\n"
                     "@@BEGIN lint local manifests/a.pp 0\n[]\n@@END\n")
    report = pregate.pregate_staged()
    assert report.status == "FINDINGS" and len(sent) == 1


@pytest.mark.parametrize("output, problem", [
    ("", "no puppet version line"),
    ("@@VERSION puppet 8.24.2\n", "no parse result for manifests/a.pp"),
    ("@@VERSION puppet 8.24.2\n@@BEGIN parse local manifests/a.pp 0\n\n@@END\n", "no lint result"),
    ("@@VERSION puppet 8.24.2\n@@BEGIN parse local manifests/a.pp 0\n\n@@END\n"
     "@@BEGIN lint local manifests/a.pp 127\n\n@@END\n", "puppet-lint exited 127"),
])
def test_staged_incomplete_master_batch_fails_closed(staged_repo, output, problem):
    repo, git, _, remote = staged_repo
    (repo / "manifests/a.pp").write_text("class a { notify { 'x': } }\n")
    git(repo, "add", "manifests/a.pp")
    remote.output = output
    report = pregate.pregate_staged()
    assert report.status == "ERROR"
    assert any(problem in d for lvl, c, d in report.lines if lvl == "ERROR")


def test_staged_unreachable_master_blocks(staged_repo, monkeypatch):
    repo, git, _, _ = staged_repo
    (repo / "manifests/a.pp").write_text("class a { notify { 'x': } }\n")
    git(repo, "add", "manifests/a.pp")
    def boom(*a, **k):
        raise RuntimeError("ssh: connect to host puppet8master: No route to host")
    monkeypatch.setattr(pregate, "run_remote", boom)
    assert pregate.pregate_staged().status == "ERROR"


def test_staged_ignores_non_puppet_files(staged_repo):
    repo, git, sent, _ = staged_repo
    (repo / "README.md").write_text("x\n")
    git(repo, "add", "README.md")
    assert pregate.pregate_staged().status == "CLEAN" and sent == []
