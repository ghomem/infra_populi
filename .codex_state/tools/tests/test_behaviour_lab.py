"""The lab's hooks for the public runner: the apply hook applies only the manifest the runner built."""
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))
sys.path.insert(1, str(TOOLS.parent))
import behaviour_lab as bl  # noqa: E402

RENDERED = "# BEGIN CODEX MANAGED (do not edit by hand)\ninclude infra_populi::backup\n# END CODEX MANAGED\n"


def test_a_manifest_the_harness_would_not_apply_is_refused(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(bl.mc, "harness", lambda *a: (0, RENDERED))
    called = []
    monkeypatch.setattr(bl.subprocess, "run", lambda *a, **k: called.append(a))
    m = tmp_path / "m.pp"
    m.write_text("include infra_populi::backup\ninclude infra_populi::other\n")
    assert bl.harness(["backup", "puppet8node", "ubuntu", str(m)]) == 1
    assert "MANIFEST DIFFERS" in capsys.readouterr().out and not called


def test_the_same_manifest_goes_to_the_harness(tmp_path, monkeypatch):
    monkeypatch.setattr(bl.mc, "harness", lambda *a: (0, RENDERED))
    runs = []

    class Done:
        returncode, stdout, stderr = 0, "GREEN: run 2 exited 0 with no change events (gate v2).\n", ""
    monkeypatch.setattr(bl.subprocess, "run", lambda args, **k: runs.append(args) or Done())
    m = tmp_path / "m.pp"
    m.write_text("# a comment\ninclude infra_populi::backup\n")
    assert bl.harness(["backup", "puppet8node", "ubuntu", str(m)]) == 0
    assert runs[0][-1] == "infra_populi::backup" and "--node" not in runs[0]
