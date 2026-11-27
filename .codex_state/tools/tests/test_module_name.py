"""The module's name, single source (metadata.json), and the engine's view of the baseline under it (Phase 2 rename
plan, mechanics 2; HQ review of the behaviour suite, ruling 8)."""
import json
import os
import subprocess
import sys
from pathlib import Path

from conftest import TOOLS

REPO = TOOLS.parents[1]
NEW = {"P8_MODULE_NAME": "infra_populi"}


def py(code: str, env: dict | None = None) -> str:
    p = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, cwd=TOOLS,
                       env={**os.environ, **(env or {})})
    assert p.returncode == 0, p.stderr
    return p.stdout


def test_the_name_is_metadata_json_s():
    name = json.loads((REPO / "metadata.json").read_text())["name"]
    assert py("import module_name; print(module_name.MODULE, module_name.PREFIX)").split() == [name, f"{name}::"]


def test_under_the_old_name_the_baseline_view_is_the_baseline_itself():
    out = py("import module_name as m; print(m.to_current('x puppet_infrastructure::a Puppet_infrastructure::B "
             "/opt/puppet-infrastructure'))", {"P8_MODULE_NAME": "puppet_infrastructure"})
    assert out.strip() == "x puppet_infrastructure::a Puppet_infrastructure::B /opt/puppet-infrastructure"


def test_under_a_new_name_every_form_of_the_old_one_reads_as_the_new_one():
    out = py("import module_name as m; print(m.to_current(b'include puppet_infrastructure::a\\n"
             "Class[Puppet_infrastructure::B]\\n/opt/puppet-infrastructure/bin\\n').decode(), end='');"
             "print(m.short('puppet_infrastructure::x'), m.short('infra_populi::y'), m.short('z'))", NEW)
    assert out.splitlines() == ["include infra_populi::a", "Class[Infra_populi::B]", "/opt/infra-populi/bin", "x y z"]


def test_a_renamed_class_is_identical_to_its_baseline_and_any_other_change_is_drift(tmp_path):
    # a copy of the repository's class files with the baseline content under the new name
    code = f"""
import sys; sys.path.insert(0, {str(TOOLS)!r})
from pathlib import Path
import baseline, module_name
base = baseline.for_class("backup_rsnapshot")
root = Path({str(tmp_path)!r})
for p in baseline.class_paths("backup_rsnapshot", base.commit, base.upstream):
    (root / p).parent.mkdir(parents=True, exist_ok=True)
    (root / p).write_bytes(module_name.to_current(baseline.git_show(base.upstream, base.commit, p)))
print("renamed", baseline.local_drift("backup_rsnapshot", base, repo=root))
m = root / "manifests" / "backup_rsnapshot.pp"
m.write_bytes(m.read_bytes() + b"# a change that is not the rename\\n")
print("changed", baseline.local_drift("backup_rsnapshot", base, repo=root))
"""
    out = py(code, NEW).splitlines()
    assert out[0] == "renamed []"
    assert out[1] == "changed ['manifests/backup_rsnapshot.pp']"
    assert b"infra_populi::" in (tmp_path / "manifests" / "backup_rsnapshot.pp").read_bytes()


def test_history_keeps_the_old_name_and_is_found_under_either(tmp_path, monkeypatch):
    log = "a1\tP8: migrate puppet_infrastructure::ssh_secure\nb2\tP8: migrate infra_populi::ssh_secure\n" \
          "c3\tP8: migrate infra_populi::ssh_secure_extra\n"
    out = py("import review_class as r; r.git = lambda *a, **k: " + repr(log) + "; "
             "print([c for c, _ in r.migrate_commits('ssh_secure')])", NEW)
    assert out.strip() == "['a1', 'b2']"
