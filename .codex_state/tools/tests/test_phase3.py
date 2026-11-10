"""Phase 3 runner (HQ batch-3 acceptance B): derived_from bound to the pinned baseline, probes on the node only,
negative controls that must fail on the clean node, JSON + JUnit output, reviewer spot-check and verdict."""

import copy
import json
import xml.etree.ElementTree as ET

import pytest
import yaml

from conftest import TOOLS

pytestmark = pytest.mark.slow  # stub-lab subprocess runs (HQ 2026-11-11 ruling 3: full suite only)

SCRIPT = str(TOOLS / "phase3.py")
CLS = "backup_rsnapshot"
REF_CONF = {"path": "manifests/backup_rsnapshot.pp", "lines": "5-11", "text": 'rsnapshot-${title}.conf'}
REF_CRON = {"path": "manifests/backup_rsnapshot.pp", "lines": "13-19", "text": 'cron { "cron_snapshot_${title}_backup":'}


def check(cid, probe, control="negative", **extra):
    c = {"id": cid, "what": f"{cid} holds", "control": control, "derived_from": [REF_CONF], "probe": probe,
         "expect": {"rc": 0}}
    c.update(extra)
    return copy.deepcopy(c)  # the REF_* templates are shared; tests mutate their copy


def check_set(*checks, **top):
    data = {"class": CLS, "baseline": "release-0.9.10 (cf477c6)", "fixture": "params",
            "authoring": {"minutes": 5}, "checks": list(checks)}
    data.update(top)
    return data


@pytest.fixture
def p3(tmp_path, lab):
    home = tmp_path / "home"
    params = home / ".config" / "infra_populi" / "params"
    params.mkdir(parents=True)
    (params / f"puppet_infrastructure::{CLS}.json").write_text("{}\n")
    checks = tmp_path / "checks"
    checks.mkdir()
    revert = tmp_path / "revert.sh"
    revert.write_text("#!/bin/sh\necho reverted >> \"$(dirname \"$0\")/log\"\n")
    harness = tmp_path / "harness.sh"
    harness.write_text("#!/bin/sh\necho \"harness $*\" >> \"$(dirname \"$0\")/log\"\n"
                       "echo 'NODE_FRESH: yes (boot x)'\necho 'GREEN: run 2 exited 0 with no change events (gate v2).'\n")
    for f in (revert, harness):
        f.chmod(0o755)
    lab.world["read_stdin"] = True

    class P3:
        dir = checks
        log = tmp_path / "log"

        def write(self, data):
            (checks / f"{CLS}.yml").write_text(yaml.safe_dump(data, sort_keys=False))

        def probe_rule(self, marker, clean, applied):
            """ssh answers for a probe containing `marker`: first call = clean phase, second = applied phase."""
            lab.world["ssh"].insert(0, {"match": marker, "outputs": [clean, applied]})

        def run(self, *args, **env):
            return lab.run(["python3", SCRIPT, *args], env={"P8_PARAMS_DIR": str(params), "P8_PHASE3_DIR": str(checks),
                                                            "P8_PHASE3_REVERT": str(revert),
                                                            "P8_PHASE3_HARNESS": str(harness), **env})

        def result(self, role="author"):
            (path,) = sorted((checks / "results" / CLS).glob(f"*-{role}.json"))[-1:]
            return json.loads(path.read_text()), ET.parse(path.with_suffix(".xml")).getroot()

    return P3()


FAIL = {"rc": 1, "stdout": ""}
OK = {"rc": 0, "stdout": "ok\n"}


# ------------------------------------------------------------------ validate

def test_a_set_bound_to_the_baseline_validates(p3):
    p3.write(check_set(check("conf", "test -f /etc/rsnapshot.d/x.conf"),
                       check("moduli", "true", control="invariant", why_invariant="x",
                             derived_from=[{"path": "files/ssh/moduli",
                                            "sha256": "01f903391abe367b549ae37822983bd3d5a8dd3d6465523f3b5f14729573b8b0"}])))
    proc = p3.run("validate", CLS)
    assert proc.returncode == 0, proc.stderr
    assert "VALID backup_rsnapshot: 2 checks (1 negative controls, 0 mutating), 2 baseline references at release-0.9.10" in proc.stdout


@pytest.mark.parametrize("mutate, message", [
    (lambda d: d["checks"][0]["derived_from"][0].update(text="no such text"), "is not in those lines at release-0.9.10"),
    (lambda d: d["checks"][0]["derived_from"][0].update(lines="400-401"), "not a range inside 1-21"),
    (lambda d: d["checks"][0]["derived_from"][0].update(path="manifests/nope.pp"), "does not exist at release-0.9.10"),
    (lambda d: d["checks"][0]["derived_from"][0].pop("text"), "`text` (an exact substring of those lines) is required"),
    (lambda d: d["checks"][0].update(derived_from=[]), "derived_from (baseline references) is required"),
    (lambda d: d["checks"][0]["derived_from"].append({"path": "files/ssh/moduli", "sha256": "0" * 64}),
     "sha256 differs from the file at release-0.9.10"),
    (lambda d: d.update(baseline="release-0.9.8"), "!= the class's baseline 'release-0.9.10 (cf477c6)'"),
    (lambda d: d["checks"][0].update(control="invariant", why_invariant="x"), "no negative control"),
    (lambda d: d["checks"].append(check("inv", "true", control="invariant")), "an invariant needs why_invariant"),
    (lambda d: d.update(authoring={}), "authoring.minutes"),
    (lambda d: d.update(fixture="defaults"), "fixture: defaults but"),
])
def test_invalid_sets_are_refused(p3, mutate, message):
    data = check_set(check("conf", "test -f /x"))
    mutate(data)
    p3.write(data)
    proc = p3.run("validate", CLS)
    assert proc.returncode == 2 and message in proc.stderr, proc.stderr


@pytest.mark.parametrize("probe, why", [
    ("/opt/puppetlabs/bin/puppet agent -t", "runs Puppet"),
    ("ssh puppet8master true", "names another lab host"),
    ("curl -s http://192.168.77.166:8140/", "names another lab host"),
    ("ssh -o BatchMode=yes git@github.com", "ssh to a host other than the node itself"),
    ("scp /etc/passwd x:", "copies to/from another host"),
    ("systemctl restart ssh", "changes a service"),
    ("apt-get -y install rsnapshot", "changes packages"),
    ("rm -f /etc/x", "changes files or accounts"),
    ("echo x > /etc/motd", "redirects into a file"),
])
def test_probes_test_the_node_only_and_change_nothing(p3, probe, why):
    p3.write(check_set(check("conf", probe)))
    proc = p3.run("validate", CLS)
    assert proc.returncode == 2 and why in proc.stderr, proc.stderr


@pytest.mark.parametrize("probe", ["sshd -T 2>&1 | grep -i kex", "test -f /x >/dev/null 2>&1",
                                   "ssh -o BatchMode=yes nobody@127.0.0.1 true 2>&1", "dpkg-query -W rsnapshot",
                                   "sha256sum /etc/ssh/moduli | cut -d' ' -f1"])
def test_read_only_node_probes_are_allowed(p3, probe):
    p3.write(check_set(check("conf", probe)))
    assert p3.run("validate", CLS).returncode == 0


# ------------------------------------------------------------------ run

def test_all_pass_writes_json_and_junit_and_probes_only_the_node(p3, lab):
    p3.write(check_set(check("conf", "probe-conf"), check("cron", "probe-cron", derived_from=[REF_CRON]),
                       check("rsync", "probe-rsync", control="invariant", why_invariant="rsync is in the baseline")))
    p3.probe_rule("probe-conf", FAIL, OK)
    p3.probe_rule("probe-cron", FAIL, OK)
    p3.probe_rule("probe-rsync", OK, OK)
    proc = p3.run("run", CLS)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    record, xml = p3.result()
    assert record["outcome"] == "ALL_PASS" and record["valid"] and record["findings"] == []
    assert [r["ok"] for r in record["clean"]] == [True, True, True] and record["apply"]["node_fresh"]
    assert [s.get("name") for s in xml.iter("testsuite")] == [f"phase3.{CLS}.clean", f"phase3.{CLS}.applied"]
    assert all(s.get("failures") == "0" for s in xml.iter("testsuite"))
    assert p3.log.read_text().splitlines() == ["reverted", f"harness puppet_infrastructure::{CLS}"]
    ssh = lab.calls("ssh")
    assert len(ssh) == 6 and all(c[-2:] == ["puppet8node", "sudo -n bash -s"] for c in ssh)


def test_a_negative_control_that_passes_on_the_clean_node_invalidates_the_set(p3):
    p3.write(check_set(check("conf", "probe-conf")))
    p3.probe_rule("probe-conf", OK, OK)  # already true before the class: proves nothing
    proc = p3.run("run", CLS)
    assert proc.returncode == 2 and "PHASE3 INVALID_SET" in proc.stdout
    record, xml = p3.result()
    assert "controls did not hold on the clean node: conf" in record["problems"][0]
    assert p3.log.read_text().splitlines() == ["reverted"]  # never applied
    failure = next(xml.iter("failure"))
    assert failure.get("message") == "negative control passed on the clean node"


def test_an_invariant_that_fails_on_the_clean_node_invalidates_the_set(p3):
    p3.write(check_set(check("conf", "probe-conf"), check("inv", "probe-inv", control="invariant", why_invariant="x")))
    p3.probe_rule("probe-conf", FAIL, OK)
    p3.probe_rule("probe-inv", FAIL, OK)
    proc = p3.run("run", CLS)
    assert proc.returncode == 2 and p3.result()[0]["outcome"] == "INVALID_SET"


def test_a_check_failing_after_apply_is_a_finding(p3):
    p3.write(check_set(check("conf", "probe-conf", expect={"rc": 0, "stdout": "^retain\\tdaily\\t7$"})))
    p3.probe_rule("probe-conf", FAIL, {"rc": 0, "stdout": "retain\tdaily\t9\n"})
    proc = p3.run("run", CLS)
    assert proc.returncode == 1 and "PHASE3 FINDINGS" in proc.stdout
    record, xml = p3.result()
    assert record["findings"] == ["conf"]
    assert any(f.get("message").startswith("check failed after the class was applied") for f in xml.iter("failure"))


def test_stdout_not_and_rc_expectations(p3):
    p3.write(check_set(check("listing", "probe-list", expect={"rc": 0, "stdout_not": "Index of /"})))
    p3.probe_rule("probe-list", {"rc": 7, "stdout": ""}, {"rc": 0, "stdout": "<h1>Index of /</h1>\n"})
    assert p3.run("run", CLS).returncode == 1


def test_a_red_harness_is_apply_failed_and_runs_no_applied_probes(p3, lab, tmp_path):
    p3.write(check_set(check("conf", "probe-conf")))
    p3.probe_rule("probe-conf", FAIL, OK)
    red = tmp_path / "red.sh"
    red.write_text("#!/bin/sh\necho 'ERROR: Run 2 still applied changes' >&2\nexit 1\n")
    red.chmod(0o755)
    proc = p3.run("run", CLS, P8_PHASE3_HARNESS=str(red))
    assert proc.returncode == 3
    record, xml = p3.result()
    assert record["outcome"] == "APPLY_FAILED" and record["applied"] == [] and len(lab.calls("ssh")) == 1
    assert next(xml.iter("skipped")).get("message") == "APPLY_FAILED"


def test_an_invalid_file_never_touches_the_node(p3, lab):
    p3.write(check_set(check("conf", "rm -rf /x")))
    assert p3.run("run", CLS).returncode == 2
    assert lab.calls("ssh") == [] and not p3.log.exists()


# ------------------------------------------------------------------ reviewer

def test_spot_prints_the_baseline_lines_read_from_the_pin(p3):
    p3.write(check_set(check("conf", "probe-conf"), check("cron", "probe-cron", derived_from=[REF_CRON])))
    proc = p3.run("spot", CLS, "--n", "2", "--seed", "7")
    assert proc.returncode == 0, proc.stderr
    assert "SPOT backup_rsnapshot: 2 of 2 references (seed 7)" in proc.stdout
    assert '  |   $myconffile = "/etc/rsnapshot.d/rsnapshot-${title}.conf"' in proc.stdout
    assert '  |     command => "/usr/bin/rsnapshot -c ${myconffile} daily",' in proc.stdout
    assert p3.run("spot", CLS, "--n", "1", "--seed", "7").stdout == p3.run("spot", CLS, "--n", "1", "--seed", "7").stdout


def run_both(p3, applied_for_reviewer=OK):
    p3.write(check_set(check("conf", "probe-conf")))
    p3.probe_rule("probe-conf", FAIL, OK)
    assert p3.run("run", CLS).returncode == 0
    p3.probe_rule("probe-conf", FAIL, applied_for_reviewer)
    p3.run("run", CLS, "--role", "reviewer")


def test_verdict_passes_when_the_reviewer_reproduces_the_author_run(p3):
    run_both(p3)
    proc = p3.run("verdict", CLS, "--derived", "ok", "--evidence", "conf: lines 5-11 declare the file")
    assert proc.returncode == 0 and proc.stdout.startswith("VERDICT PASS"), proc.stdout + proc.stderr
    (path,) = (p3.dir / "reviews" / CLS).glob("*.json")
    assert json.loads(path.read_text())["checks"] == {"reviewer_run": "ok", "author_run": "ok", "reproduced": "ok",
                                                      "derived_from": "ok"}


def test_verdict_fails_when_the_runs_differ_or_derivation_is_wrong(p3):
    run_both(p3, applied_for_reviewer=FAIL)
    proc = p3.run("verdict", CLS, "--derived", "ok", "--evidence", "x")
    assert proc.returncode == 1 and '"reproduced": "fail"' in proc.stdout
    proc = p3.run("verdict", CLS, "--derived", "fail", "--evidence", "cron check tests the wrong hour")
    assert proc.returncode == 1 and '"derived_from": "fail"' in proc.stdout


@pytest.mark.repo_state
@pytest.mark.parametrize("cls", ["backup_rsnapshot", "ssh_secure", "nginx_static_domain"])
def test_the_pilot_check_sets_validate(cls):
    import subprocess
    proc = subprocess.run(["python3", SCRIPT, "validate", cls], capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr


# HQ 2026-11-10: mutating probes — opt-in per check, declared change, after all read-only checks, evidence = effect.
def mutating(cid="backup-runs", action="act-backup; rm -f /tmp/x", effect="eff-backup",
             mutates="runs one rsnapshot daily snapshot into the snapshot root", **extra):
    return check(cid, action, mutates=mutates, effect=effect, **extra)


def test_a_mutating_check_validates_with_a_declared_change_and_a_read_only_effect(p3):
    p3.write(check_set(check("conf", "probe-conf"), mutating()))
    proc = p3.run("validate", CLS)
    assert proc.returncode == 0, proc.stderr
    assert "(2 negative controls, 1 mutating)" in proc.stdout


@pytest.mark.parametrize("bad, message", [
    (mutating(action="/opt/puppetlabs/bin/puppet agent -t"), "runs Puppet"),
    (mutating(action="ssh puppet8master true"), "names another lab host"),
    (mutating(effect="rm -f /x"), "effect probe changes files or accounts"),
    (mutating(effect=""), "needs a read-only `effect` probe"),
    (mutating(mutates="x"), "mutates must declare what the action changes"),
    (mutating(control="invariant", why_invariant="x"), "a mutating check is a negative control"),
    (check("conf2", "probe", effect="eff"), "`effect` without `mutates`"),
    (check("conf2", "rm -f /x"), "changes files or accounts"),  # without opt-in, still read-only
])
def test_mutating_checks_keep_the_host_rules_and_need_the_opt_in(p3, bad, message):
    p3.write(check_set(check("conf", "probe-conf"), bad))
    proc = p3.run("validate", CLS)
    assert proc.returncode == 2 and message in proc.stderr, proc.stderr


def test_the_action_runs_only_after_apply_after_every_read_only_check_and_is_judged_on_its_effect(p3, lab):
    p3.write(check_set(mutating(), check("conf", "probe-conf")))  # mutating listed first, still runs last
    p3.probe_rule("probe-conf", FAIL, OK)
    lab.world["ssh"].insert(0, {"match": "act-backup", "outputs": [{"rc": 3, "stdout": "rsnapshot said no\n"}]})
    p3.probe_rule("eff-backup", FAIL, OK)
    proc = p3.run("run", CLS)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    record, _ = p3.result()
    clean = {r["id"]: r for r in record["clean"]}
    assert clean["backup-runs"]["action"] is None and clean["backup-runs"]["ok"]  # effect only, action never ran
    assert [r["id"] for r in record["applied"]] == ["conf", "backup-runs"]
    applied = record["applied"][1]
    assert applied["passed"] and applied["action"]["rc"] == 3  # evidence is the effect, the action's rc is recorded
    assert applied["action"]["mutates"].startswith("runs one rsnapshot")
    ssh = lab.calls("ssh")
    assert len(ssh) == 5 and all(c[-2:] == ["puppet8node", "sudo -n bash -s"] for c in ssh)  # 2 clean + 3 applied
    out = proc.stdout
    assert out.index("pass conf") < out.index("pass backup-runs (mutating")


def test_a_failed_read_only_check_skips_every_mutating_action(p3, lab):
    p3.write(check_set(check("conf", "probe-conf"), mutating()))
    p3.probe_rule("probe-conf", FAIL, FAIL)
    lab.world["ssh"].insert(0, {"match": "act-backup", "stdout": "", "rc": 0})
    p3.probe_rule("eff-backup", FAIL, OK)
    proc = p3.run("run", CLS)
    assert proc.returncode == 1 and "SKIP backup-runs (mutating; not run: read-only checks failed (conf))" in proc.stdout
    record, xml = p3.result()
    assert record["findings"] == ["conf"] and record["not_run"] == ["backup-runs"]
    assert not any("act-backup" in " ".join(c) for c in lab.calls("ssh"))
    assert len(lab.calls("ssh")) == 3  # 2 clean (probe + effect) + 1 applied read-only; the action never sent
    assert any(s.get("message", "").startswith("not run: read-only checks failed") for s in xml.iter("skipped"))
