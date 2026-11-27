"""The reviewer's rename mode (HQ review of the behaviour suite, ruling 9), on a synthetic repository: the class's diff
is the rename only, its run after the rename is green and identical check for check to the run reviewed before, and
the re-run selection is every class whose node-visible names change plus a seeded 15% of the rest."""
import json
import shutil
import subprocess
import sys

import pytest

from conftest import TOOLS

MANIFESTS = {
    "a": "class puppet_infrastructure::a {\n  include puppet_infrastructure::b\n}\n",  # references only
    "b": "class puppet_infrastructure::b {\n  file { '/etc/p8test/puppet_infrastructure.conf': ensure => file }\n}\n",
    "c": "class puppet_infrastructure::c (\n  $localdir = lookup('filesystem::localdir'),\n) {\n}\n",
}


def git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), "-c", "user.email=p8test@example.invalid", "-c",
                           "user.name=p8test", *args], capture_output=True, text=True, check=True).stdout


def result(at, role, passed=True, green=True):
    return {"class": "a", "role": role, "at": at, "valid": True, "outcome": "ALL_PASS" if passed else "FINDINGS",
            "apply": {"green": green}, "clean": [{"id": "x", "ok": True}],
            "applied": [{"id": "x", "passed": passed}]}


@pytest.fixture
def repo(tmp_path):
    r = tmp_path / "repo"
    (r / "manifests").mkdir(parents=True)
    for c, text in MANIFESTS.items():
        (r / "manifests" / f"{c}.pp").write_text(text)
    (r / "spec" / "behaviour" / "checks").mkdir(parents=True)
    for c in MANIFESTS:
        (r / "spec" / "behaviour" / "checks" / f"{c}.yml").write_text(f"class: {c}\nchecks: []\n")
    (r / "spec" / "behaviour" / "probe_helpers.sh").write_text("")
    (r / "metadata.json").write_text(json.dumps({"name": "puppet_infrastructure", "version": "0.9.4"}) + "\n")
    (r / ".codex_state" / "rules").mkdir(parents=True)
    shutil.copy(TOOLS.parent / "rules" / "rename_scope.txt", r / ".codex_state" / "rules")
    (r / ".codex_state" / "tools").mkdir()
    for t in ("rename_module.py", "rename_check.py", "rename_review.py", "behaviour_sample.py"):
        shutil.copy(TOOLS / t, r / ".codex_state" / "tools")
    subprocess.run(["git", "init", "-q", str(r)], check=True)
    git(r, "add", "-A")
    git(r, "commit", "-q", "-m", "before")
    git(r, "tag", "pre-rename")
    return r


def renamed(r, extra=None):
    subprocess.run([sys.executable, str(r / ".codex_state/tools/rename_module.py"), "apply", "infra_populi"],
                   check=True, capture_output=True)
    if extra:
        extra(r)
    git(r, "add", "-A")
    git(r, "commit", "-q", "-m", "P2: rename module to infra_populi")


def write(r, run):
    d = r / ".codex_state" / "checks" / "results" / "a"
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{run['at']}-{run['role']}.json").write_text(json.dumps(run))


def review(r, *args):
    return subprocess.run([sys.executable, str(r / ".codex_state/tools/rename_review.py"), *args],
                          capture_output=True, text=True)


def test_selection_is_every_node_visible_class(repo):
    renamed(repo)
    out = review(repo, "selection").stdout
    assert "node-visible (2): b c" in out and "random 15% of the rest (0):" in out


def test_a_renamed_class_reverified_identically_passes(repo):
    renamed(repo)
    write(repo, result("20000101T000000Z", "reviewer"))
    write(repo, result("29990101T000000Z", "author"))
    p = review(repo, "verdict", "a", "--evidence", "diff renamed only; run identical")
    assert p.returncode == 0 and "VERDICT PASS" in p.stdout, p.stdout + p.stderr
    rec = json.loads(next((repo / ".codex_state" / "reviews" / "rename" / "a").glob("*.json")).read_text())
    assert rec["checks"] == {"rename_only": "ok", "reverified": "ok"} and rec["selected"] is None


def test_a_change_beyond_the_rename_fails(repo):
    renamed(repo, lambda r: (r / "manifests" / "a.pp").write_text((r / "manifests" / "a.pp").read_text() + "# x\n"))
    write(repo, result("20000101T000000Z", "reviewer"))
    write(repo, result("29990101T000000Z", "author"))
    out = review(repo, "check", "a").stdout
    assert "rename_only: fail" in out and "manifests/a.pp: not the rename of its old content" in out


@pytest.mark.parametrize("after, why", [
    (result("29990101T000000Z", "author", passed=False), "applied x: before True, after False"),
    (result("29990101T000000Z", "author", green=False), "apply NOT green"),
])
def test_a_reverification_that_differs_or_is_not_green_fails(repo, after, why):
    renamed(repo)
    write(repo, result("20000101T000000Z", "reviewer"))
    write(repo, after)
    out = review(repo, "check", "a").stdout
    assert "reverified: fail" in out and why in out, out


def test_no_run_after_the_rename_fails(repo):
    renamed(repo)
    write(repo, result("20000101T000000Z", "reviewer"))
    assert "no author run after the rename" in review(repo, "check", "a").stdout
