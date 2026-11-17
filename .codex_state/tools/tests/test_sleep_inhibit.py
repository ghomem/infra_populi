"""Lab runs hold a logind sleep/idle inhibitor (2026-11-17: KDE's idle suspend paused the VMs mid-run and
linux_policies_user's run 2 failed after hanging 557 s on the master connection)."""

import importlib.util
import sys

import pytest

from conftest import TOOLS

pytestmark = pytest.mark.slow  # stub-lab harness runs


def inhibit_calls(lab):
    log = lab.root / "inhibit.log"
    return log.read_text().splitlines() if log.exists() else []


def test_a_harness_run_holds_one_sleep_inhibitor_for_its_lifetime(lab):
    lab.world["ssh"].insert(0, {"match": r"agent -t", "outputs": [{"rc": 2, "stdout": ""}, {"rc": 0, "stdout": ""}]})
    lab.run([str(TOOLS / "test_class.sh"), "--revert-first", "--fixture", "guarded_exec"])
    held = [c for c in inhibit_calls(lab) if "--why=lab run: test_class.sh" in c]
    assert len(held) == 1 and "--what=sleep:idle" in held[0]
    assert "test_class.sh --revert-first --fixture guarded_exec" in held[0]


@pytest.mark.parametrize("argv, env", [(["--render-only", "puppet_infrastructure::dns_client"], {}),
                                       (["--fixture", "guarded_exec"], {"P8_NO_SLEEP_INHIBIT": "1"})])
def test_no_inhibitor_for_render_only_or_when_disabled(lab, argv, env):
    lab.run([str(TOOLS / "test_class.sh"), *argv], env=env)
    assert not [c for c in inhibit_calls(lab) if "lab run" in c]


@pytest.fixture
def phase3(monkeypatch):
    spec = importlib.util.spec_from_file_location("phase3_inhibit", TOOLS / "phase3.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["phase3_inhibit"] = module
    spec.loader.exec_module(module)
    monkeypatch.delenv("P8_SLEEP_INHIBITED", raising=False)
    monkeypatch.delenv("P8_NO_SLEEP_INHIBIT", raising=False)
    return module


class Execd(Exception):
    pass


def test_phase3_run_reexecutes_under_an_inhibitor(phase3, monkeypatch):
    monkeypatch.setattr(phase3.subprocess, "run", lambda *a, **k: type("P", (), {"returncode": 0})())
    def fake_exec(file, args):
        raise Execd(args)
    monkeypatch.setattr(phase3.os, "execvp", fake_exec)
    with pytest.raises(Execd) as caught:
        phase3.inhibit_sleep(["run", "backup"])
    args = caught.value.args[0]
    assert args[:2] == ["systemd-inhibit", "--what=sleep:idle"] and args[-3:] == [phase3.__file__, "run", "backup"]


@pytest.mark.parametrize("env, rc", [({"P8_SLEEP_INHIBITED": "1"}, 0), ({"P8_NO_SLEEP_INHIBIT": "1"}, 0), ({}, 1)])
def test_phase3_runs_without_an_inhibitor_when_held_disabled_or_unavailable(phase3, monkeypatch, env, rc):
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    monkeypatch.setattr(phase3.subprocess, "run", lambda *a, **k: type("P", (), {"returncode": rc})())
    monkeypatch.setattr(phase3.os, "execvp", lambda *a: (_ for _ in ()).throw(Execd(a)))
    phase3.inhibit_sleep(["run", "backup"])  # returns: no re-exec
