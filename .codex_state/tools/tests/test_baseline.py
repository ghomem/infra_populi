import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

sys.dont_write_bytecode = True
TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))


def load(name):
    spec = importlib.util.spec_from_file_location(name, TOOLS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


baseline = load("baseline")
reannotate = load("reannotate_baseline")


def git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True).stdout.strip()


@pytest.fixture
def upstream(tmp_path):
    """Two-commit upstream: v1 -> v2 changes only rsyslog_server and its template."""
    repo = tmp_path / "up"
    repo.mkdir()
    git(repo, "init", "-q")
    git(repo, "config", "user.email", "t@example.invalid")
    git(repo, "config", "user.name", "t")
    files = {
        "manifests/same.pp": "class same { file { '/x': content => template('puppet_infrastructure/same/a.erb') } }\n",
        "templates/same/a.erb": "a\n",
        "manifests/rsyslog_server.pp": "class r { file { '/y': content => epp('puppet_infrastructure/rsyslog/l.epp') } }\n",
        "templates/rsyslog/l.epp": "v1\n",
        "manifests/dyn.pp": "class dyn { file { '/z': source => \"puppet:///modules/puppet_infrastructure/dyn/${n}\" } }\n",
        "files/dyn/one": "1\n",
    }
    for path, content in files.items():
        (repo / path).parent.mkdir(parents=True, exist_ok=True)
        (repo / path).write_text(content)
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "v1")
    v1 = git(repo, "rev-parse", "HEAD")
    (repo / "templates/rsyslog/l.epp").write_text("v2\n")
    (repo / "files/dyn/two").write_text("2\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "v2")
    return repo, v1, git(repo, "rev-parse", "HEAD")


def test_referenced_paths_literal_and_prefix():
    manifest = ("content => template('puppet_infrastructure/a/b.erb')\n"
                "x => file('puppet_infrastructure/c/d')\n"
                "source => 'puppet:///modules/puppet_infrastructure/e/f.sh',\n"
                "y => template(\"puppet_infrastructure/sysmon/${p}.sh.erb\")\n")
    assert baseline.referenced_paths(manifest) == [
        ("files/c/d", False), ("files/e/f.sh", False),
        ("templates/a/b.erb", False), ("templates/sysmon/", True)]


def test_identity_detects_template_change(upstream):
    repo, v1, v2 = upstream
    assert baseline.identical_between("same", v1, v2, repo) == (True, [])
    same, differing = baseline.identical_between("rsyslog_server", v1, v2, repo)
    assert not same and differing == ["templates/rsyslog/l.epp"]


def test_identity_interpolated_source_counts_new_file(upstream):
    repo, v1, v2 = upstream
    same, differing = baseline.identical_between("dyn", v1, v2, repo)
    assert not same and differing == ["files/dyn/two"]


def test_plan_rewrites_only_identical_and_preserves_position():
    lines = ["a Done [from: old]", "Done b [from: old]", "c Done", "d Done [from: old]", "e"]
    verdict = {"a": (True, []), "b": (True, []), "d": (False, ["manifests/d.pp"])}
    out, decisions = reannotate.plan(lines, "old", "new", lambda c: verdict[c])
    assert out == ["a Done [from: new]", "Done b [from: new]", "c Done", "d Done [from: old]", "e"]
    assert [d[:2] for d in decisions] == [("a", "reannotate"), ("b", "reannotate"), ("d", "keep (content differs)")]


def test_plan_refuses_ambiguous_line():
    with pytest.raises(SystemExit):
        reannotate.plan(["a b Done [from: old]"], "old", "new", lambda c: (True, []))


def test_env_requires_full_commit(tmp_path):
    env = tmp_path / "b.env"
    env.write_text("BASELINE_NAME=release-x\nBASELINE_COMMIT=cf477c6\nUPSTREAM_REPO=/tmp\n")
    with pytest.raises(SystemExit):
        baseline.load(env)


def test_self_check_tolerates_kept_marker_and_catches_other_edits():
    before = "a Done [from: old]\nd Done [from: old]\n"
    assert reannotate.only_markers_changed(before, "a Done [from: new]\nd Done [from: old]\n", "old", "new")
    assert not reannotate.only_markers_changed(before, "a Done [from: new]\nd Done\n", "old", "new")
    assert not reannotate.only_markers_changed(before, "a Done [from: new]\nx Done [from: old]\n", "old", "new")
