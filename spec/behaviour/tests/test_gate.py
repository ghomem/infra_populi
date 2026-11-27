"""The apply gate, one code path for the runner and any harness that calls it (`python3 -m behaviour.gate`)."""
import json
import subprocess
import sys
from pathlib import Path

SUITE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SUITE / "lib"))
from behaviour import gate as g  # noqa: E402

APPLIED = "Notice: Applied catalog in 3.10 seconds\n"
CHANGE = "Notice: /Stage[main]/X/File[/etc/p8test]/ensure: created\n"


def cli(runs, expected=()):
    p = subprocess.run([sys.executable, "-m", "behaviour.gate"], cwd=SUITE / "lib", capture_output=True, text=True,
                       input=json.dumps({"runs": [{"rc": rc, "out": out} for rc, out in runs],
                                         "expected": list(expected)}))
    return p.returncode, json.loads(p.stdout)


def test_a_clean_second_run_is_green():
    rc, v = cli([(2, CHANGE + APPLIED), (0, APPLIED)])
    assert rc == 0 and v["green"] and v["reason"] == "" and v["expected_hits"] == 0


def test_an_error_in_either_run_fails_even_with_exit_0():
    err = "\x1b[1;31mError: /Stage[main]/X/Exec[e]/unless: Check \"x\" exceeded timeout\x1b[0m\n"
    for runs in ([(2, err + CHANGE + APPLIED), (0, APPLIED)], [(2, CHANGE + APPLIED), (0, err + APPLIED)]):
        rc, v = cli(runs)
        assert rc == 1 and v["reason"] == "a run logged an error" and v["errors"]


def test_a_change_only_the_report_shows_is_an_event():
    rc, v = cli([(2, CHANGE), (2, APPLIED + "CHANGED Notify[debug note]\n")])
    assert rc == 1 and v["unexpected"] == [g.SILENT + "Notify[debug note]"]
    rc, v = cli([(2, CHANGE), (2, APPLIED + "CHANGED Notify[debug note]\n")], ["Notify[debug *]"])
    assert rc == 0 and v["expected_hits"] == 1


def test_a_change_on_the_console_and_in_the_report_counts_once():
    apt = "Notice: /Stage[main]/Apt::Update/Exec[apt_update]/returns: executed successfully\n"
    rc, v = cli([(2, CHANGE), (2, apt + APPLIED + "CHANGED Exec[apt_update]\n")], ["Exec[apt_update]"])
    assert rc == 0 and v["expected_hits"] == 1


def test_a_plugin_file_changed_outside_the_catalog_still_counts():
    plug = "Notice: /File[/opt/puppetlabs/puppet/cache/lib/facter/x.rb]/content: defined content as '{sha256}ab'\n"
    rc, v = cli([(2, CHANGE), (2, plug + APPLIED)])
    assert rc == 1 and v["unexpected"]


def test_exit_2_needs_an_expected_event_and_other_exits_fail():
    assert cli([(2, CHANGE), (2, APPLIED)])[1]["reason"].startswith("run 2 exited 2 with no change event")
    assert cli([(2, CHANGE), (6, APPLIED)])[1]["reason"].startswith("run 2 exited 6")
    assert cli([(4, CHANGE), (0, APPLIED)])[1]["reason"] == "run 1 failed (exit 4)"


def test_bad_input_is_exit_2():
    p = subprocess.run([sys.executable, "-m", "behaviour.gate"], cwd=SUITE / "lib", capture_output=True, text=True,
                       input="{}")
    assert p.returncode == 2 and not json.loads(p.stdout)["green"]
