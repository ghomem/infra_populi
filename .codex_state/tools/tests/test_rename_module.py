"""The module rename and its proof (Phase 2 rename plan, mechanics 1; HQ review of the behaviour suite, ruling 8), on a
synthetic repository: rename_module.py applies the scope, rename_check.py proves the result independently."""
import json
import shutil
import subprocess
import sys

import pytest

from conftest import TOOLS

SCOPE = TOOLS.parent / "rules" / "rename_scope.txt"
SET = """\
class: a
checks:
# a comment naming puppet_infrastructure
- id: x
  derived_from:
  - path: manifests/a.pp
    lines: '1'
    text: class puppet_infrastructure::a {
  probe: test -f /etc/nginx/conf.d/puppet_infrastructure.conf
  expect:
    rc: 0
"""
FILES = {
    "manifests/a.pp": "class puppet_infrastructure::a {\n  file { '/etc/nginx/conf.d/puppet_infrastructure.conf': }\n"
                      "  Class['Puppet_infrastructure::b'] -> File['/opt/puppet-infrastructure/bin']\n}\n",
    "spec/behaviour/checks/a.yml": SET,
    ".codex_state/DESIGN_DECISIONS.md": "## history names puppet_infrastructure\n",
    "CLAUDE.md": "Upstream reference `~/work/puppet_infrastructure`; namespace `puppet_infrastructure::`.\n",
    "metadata.json": json.dumps({"name": "puppet_infrastructure", "version": "0.9.4",
                                 "source": "https://github.com/ghomem/puppet_infrastructure"}, indent=2) + "\n",
}


def git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), "-c", "user.email=p8test@example.invalid", "-c", "user.name=p8test",
                           *args], capture_output=True, text=True, check=True).stdout


@pytest.fixture
def repo(tmp_path):
    r = tmp_path / "repo"
    for path, text in FILES.items():
        (r / path).parent.mkdir(parents=True, exist_ok=True)
        (r / path).write_text(text)
    (r / ".codex_state" / "rules").mkdir(parents=True, exist_ok=True)
    shutil.copy(SCOPE, r / ".codex_state" / "rules" / "rename_scope.txt")
    (r / ".codex_state" / "tools").mkdir(parents=True, exist_ok=True)
    for tool in ("rename_module.py", "rename_check.py"):
        shutil.copy(TOOLS / tool, r / ".codex_state" / "tools" / tool)
    subprocess.run(["git", "init", "-q", str(r)], check=True)
    git(r, "add", "-A")
    git(r, "commit", "-q", "-m", "synthetic")
    git(r, "tag", "pre-rename")
    return r


def tool(repo, name, *args):
    return subprocess.run([sys.executable, str(repo / ".codex_state" / "tools" / name), *args], capture_output=True,
                          text=True)


def test_the_rename_changes_every_live_form_and_keeps_history_sources_and_quotations(repo):
    p = tool(repo, "rename_module.py", "apply", "infra_populi")
    assert p.returncode == 0, p.stdout + p.stderr
    assert "manifests/a.pp:1: class puppet_infrastructure::a {  =>  class infra_populi::a {" in p.stdout
    assert (repo / "manifests/a.pp").read_text() == (
        "class infra_populi::a {\n  file { '/etc/nginx/conf.d/infra_populi.conf': }\n"
        "  Class['Infra_populi::b'] -> File['/opt/infra-populi/bin']\n}\n")
    s = (repo / "spec/behaviour/checks/a.yml").read_text()
    assert "text: class puppet_infrastructure::a {" in s  # the baseline's quotation, kept
    assert "probe: test -f /etc/nginx/conf.d/infra_populi.conf" in s and "# a comment naming infra_populi" in s
    assert (repo / ".codex_state/DESIGN_DECISIONS.md").read_text() == FILES[".codex_state/DESIGN_DECISIONS.md"]
    assert (repo / "CLAUDE.md").read_text() == \
        "Upstream reference `~/work/puppet_infrastructure`; namespace `infra_populi::`.\n"
    meta = json.loads((repo / "metadata.json").read_text())
    assert meta == {"name": "infra_populi", "version": "0.9.10", "source": "https://github.com/ghomem/puppet_infrastructure"}
    c = tool(repo, "rename_check.py", "pre-rename", "infra_populi")
    assert c.returncode == 0 and "RENAME_CHECK PASS" in c.stdout, c.stdout


def test_plan_changes_nothing(repo):
    p = tool(repo, "rename_module.py", "plan", "infra_populi")
    assert "would change 4 files" in p.stdout
    assert git(repo, "status", "--porcelain") == ""


@pytest.mark.parametrize("tamper, problem", [
    (lambda r: r.joinpath("manifests/a.pp").write_text(r.joinpath("manifests/a.pp").read_text() + "# extra\n"),
     "manifests/a.pp: 5 lines before, 6 after"),
    (lambda r: r.joinpath("manifests/a.pp").write_text(
        r.joinpath("manifests/a.pp").read_text().replace("File[", "File [")), "manifests/a.pp:3: not the rename"),
    (lambda r: r.joinpath("spec/behaviour/checks/a.yml").write_text(
        r.joinpath("spec/behaviour/checks/a.yml").read_text().replace("text: class puppet_", "text: class infra_")
        .replace("infrastructure::a {", "populi::a {")), "derived_from) but changed"),
    (lambda r: r.joinpath(".codex_state/DESIGN_DECISIONS.md").write_text("## changed\n"), "excluded (kept as written)"),
    (lambda r: r.joinpath("manifests/a.pp").write_text(FILES["manifests/a.pp"]), "form(s) of the old name left"),
    (lambda r: (r.joinpath("extra.txt").write_text("x\n"), git(r, "add", "extra.txt")), "file added: extra.txt"),
])
def test_anything_but_the_rename_fails_the_check(repo, tamper, problem):
    assert tool(repo, "rename_module.py", "apply", "infra_populi").returncode == 0
    tamper(repo)
    c = tool(repo, "rename_check.py", "pre-rename", "infra_populi")
    assert c.returncode == 1 and "RENAME_CHECK FAIL" in c.stdout and problem in c.stdout, c.stdout


def test_bad_names_are_refused(repo):
    for name in ("puppet_infrastructure", "Infra-Populi", ""):
        assert tool(repo, "rename_module.py", "apply", name).returncode == 2
