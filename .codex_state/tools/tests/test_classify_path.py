"""classify_path (step 3.3): which generation path a pending class takes (ruling 3)."""

import importlib.util
import sys

import pytest

from conftest import TOOLS

sys.path.insert(0, str(TOOLS))
spec = importlib.util.spec_from_file_location("classify_path", TOOLS / "classify_path.py")
cp = importlib.util.module_from_spec(spec)
sys.modules["classify_path"] = cp
spec.loader.exec_module(cp)


def report(*lines):
    r = cp.pregate.Report("x")
    for line in lines:
        r.add(*line)
    return r


@pytest.fixture
def world(monkeypatch):
    state = {"drift": [], "report": report(("PASS", "drift", "identical")), "compile": ("ok", "COMPILE OK"),
             "compiled": []}
    monkeypatch.setattr(cp.baseline, "local_drift", lambda cls, base: state["drift"])
    monkeypatch.setattr(cp.pregate, "pregate_class", lambda cls: state["report"])

    def fake_compile(cls):
        state["compiled"].append(cls)
        return state["compile"]
    monkeypatch.setattr(cp, "compile_only", fake_compile)
    return state


def test_identical_clean_and_compiling_is_unchanged_validated(world):
    code, path, _ = cp.decide("x")
    assert (code, path) == (0, "unchanged-validated") and world["compiled"] == ["x"]


def test_drift_means_baseline_sync_first_and_nothing_else_runs(world):
    world["drift"] = ["manifests/x.pp"]
    code, path, reasons = cp.decide("x")
    assert (code, path) == (3, "baseline-sync first") and "manifests/x.pp" in reasons[0]
    assert world["compiled"] == []


def test_pregate_finding_means_syntax_work_without_compiling(world):
    world["report"] = report(("FINDING", "lint:legacy_facts", "manifests/x.pp:3: legacy fact"))
    code, path, reasons = cp.decide("x")
    assert (code, path) == (1, "syntax-work") and "legacy fact" in reasons[0]
    assert world["compiled"] == []


def test_compile_failure_means_syntax_work(world):
    world["compile"] = ("fail", "Error: no parameter named 'action'")
    code, path, reasons = cp.decide("x")
    assert (code, path) == (1, "syntax-work") and "action" in reasons[0]


@pytest.mark.parametrize("line", ["Error: Function lookup() did not find a value for the name 'sysmon::basedir'",
                                  "Error: Puppet_infrastructure::Sync[sync]: expects a value for parameter 'src'",
                                  "Error: Could not find resource 'File[/opt/puppet-infrastructure/bin]' in parameter "
                                  "'require' (file: sysmon_base.pp, line: 20)"])
def test_missing_hiera_key_param_or_required_base_is_a_context_gap(world, line):
    world["compile"] = ("fail", line)
    code, path, _ = cp.decide("x")
    assert (code, path) == (4, "context-gap")


@pytest.mark.parametrize("which", ["pregate", "compile"])
def test_a_check_that_cannot_run_decides_nothing(world, which):
    if which == "pregate":
        world["report"] = report(("ERROR", "master", "ssh failed"))
    else:
        world["compile"] = ("error", "ERROR: Could not read facts")
    code, path, _ = cp.decide("x")
    assert (code, path) == (2, "ERROR")


def test_usage(capsys):
    assert cp.main([]) == 2 and cp.main(["../x"]) == 2
