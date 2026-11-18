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


PURPOSE = "keeps daily rsnapshot backups of a directory, restorable from the snapshot root"
COVERED = ("--purpose", "covered", "--purpose-evidence", "the checks back up and restore a file")


def check_set(*checks, **top):
    data = {"class": CLS, "baseline": "release-0.9.10 (cf477c6)", "fixture": "params",
            "authoring": {"minutes": 5}, "purpose": PURPOSE, "checks": list(checks)}
    data.update(top)
    return data


# revert_node.sh stand-in: `--node-state` prints a boot ID per kind (P8_BOOT_<kind> overrides it, to fake a reboot
# mid-run), anything else is logged as a revert.
REVERT_STUB = """#!/bin/sh
case "$*" in
  *--node-state*) kind=$2; eval "b=\\${{P8_BOOT_$kind:-boot-$kind}}"; echo "$b"; echo absent ;;
  *) echo "{log}" >> "$(dirname "$0")/log" ;;
esac
"""


@pytest.fixture
def p3(tmp_path, lab):
    home = tmp_path / "home"
    params = home / ".config" / "infra_populi" / "params"
    params.mkdir(parents=True)
    (params / f"puppet_infrastructure::{CLS}.json").write_text("{}\n")
    checks = tmp_path / "checks"
    checks.mkdir()
    revert = tmp_path / "revert.sh"
    revert.write_text(REVERT_STUB.format(log="reverted"))
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
    assert "VALID backup_rsnapshot: 2 checks (1 negative controls, 0 mutating, 0 mismatch), 2 baseline references at release-0.9.10" in proc.stdout


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
                                   "dpkg-query -W rsnapshot",
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
    proc = p3.run("verdict", CLS, *COVERED, "--derived", "ok", "--evidence", "conf: lines 5-11 declare the file")
    assert proc.returncode == 0 and proc.stdout.startswith("VERDICT PASS"), proc.stdout + proc.stderr
    (path,) = (p3.dir / "reviews" / CLS).glob("*.json")
    verdict = json.loads(path.read_text())
    assert verdict["checks"] == {"reviewer_run": "ok", "author_run": "ok", "reproduced": "ok", "derived_from": "ok",
                                 "nodes_fresh": "ok", "purpose": "ok"}
    assert verdict["nodes"]["node"]["boot_id"] == "boot-ubuntu" and verdict["nodes"]["node"]["fresh"] is True


def test_verdict_fails_when_the_reviewer_node_rebooted_during_its_run(p3, tmp_path):
    p3.write(check_set(check("conf", "probe-conf")))
    p3.probe_rule("probe-conf", FAIL, OK)
    assert p3.run("run", CLS).returncode == 0
    p3.probe_rule("probe-conf", FAIL, OK)
    # the boot ID read at the end differs from the one read after the revert: the stub answers per call count
    counter = tmp_path / "boots"
    (tmp_path / "revert.sh").write_text(
        "#!/bin/sh\ncase \"$*\" in *--node-state*) n=$(cat " + str(counter) + " 2>/dev/null || echo 0); "
        "echo $((n+1)) > " + str(counter) + "; echo boot-$n; echo absent ;; *) echo reverted >> \"$(dirname \"$0\")/log\" ;; esac\n")
    p3.run("run", CLS, "--role", "reviewer")
    record, _ = p3.result("reviewer")
    assert record["nodes"]["node"]["fresh"] is False
    proc = p3.run("verdict", CLS, *COVERED, "--derived", "ok", "--evidence", "x")
    assert proc.returncode == 1 and '"nodes_fresh": "fail"' in proc.stdout and "NOT FRESH" in proc.stdout


def test_verdict_fails_when_the_runs_differ_or_derivation_is_wrong(p3):
    run_both(p3, applied_for_reviewer=FAIL)
    proc = p3.run("verdict", CLS, *COVERED, "--derived", "ok", "--evidence", "x")
    assert proc.returncode == 1 and '"reproduced": "fail"' in proc.stdout
    proc = p3.run("verdict", CLS, *COVERED, "--derived", "fail", "--evidence", "cron check tests the wrong hour")
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
    assert "(2 negative controls, 1 mutating, 0 mismatch)" in proc.stdout


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
    assert len(lab.calls("ssh")) == 3  # 2 clean (probe + effect) + 1 applied read-only; the action never sent
    assert any(s.get("message", "").startswith("not run: read-only checks failed") for s in xml.iter("skipped"))



# HQ 2026-11-16: mismatch controls — the same probe with one value wrong must FAIL on the applied node.
MM = {"varies": "the hostname: wrong.example.org must fail verification", "probe": "probe-wrong"}


@pytest.mark.parametrize("probe", [
    "openssl s_client -connect 127.0.0.1:443 -servername p8test.example.com </dev/null",
    "curl -s -H 'Host: p8test.example.com' http://127.0.0.1/",
    "curl -sk --resolve p8test.example.com:443:127.0.0.1 https://p8test.example.com/",
    "ssh -o BatchMode=yes nobody@127.0.0.1 true 2>&1",
    "ssh -o BatchMode=yes -o Ciphers=aes256-ctr localhost true",
    "sudo -u www-data cat /x",
])
def test_a_tool_verdict_probe_without_a_mismatch_is_refused(p3, probe):
    p3.write(check_set(check("conf", probe)))
    proc = p3.run("validate", CLS)
    assert proc.returncode == 2 and "a `mismatch` control is mandatory" in proc.stderr, proc.stderr
    p3.write(check_set(check("conf", probe, mismatch=dict(MM))))
    assert p3.run("validate", CLS).returncode == 0


@pytest.mark.parametrize("probe", ["sshd -T 2>/dev/null | grep -E '^kexalgorithms '", "getent group ssh_in",
                                   "crontab -l -u root", "nginx -t 2>&1"])
def test_a_direct_state_read_needs_no_mismatch(p3, probe):
    p3.write(check_set(check("conf", probe)))
    assert p3.run("validate", CLS).returncode == 0


@pytest.mark.parametrize("mm, message", [
    ({"varies": "x", "probe": "p"}, "mismatch.varies must say which value is wrong"),
    ({"varies": "the hostname is wrong", "probe": "probe-conf"}, "mismatch.probe is identical to the probe"),
    ({"varies": "the hostname is wrong", "probe": "rm -f /x"}, "mismatch probe changes files or accounts"),
    ({"varies": "the hostname is wrong"}, "mismatch takes exactly `varies` and `probe`"),
])
def test_bad_mismatch_controls_are_refused(p3, mm, message):
    p3.write(check_set(check("conf", "probe-conf", mismatch=mm)))
    proc = p3.run("validate", CLS)
    assert proc.returncode == 2 and message in proc.stderr, proc.stderr


def test_a_mismatch_that_fails_as_required_keeps_the_set_valid(p3, lab):
    p3.write(check_set(check("conf", "probe-conf", mismatch=dict(MM)), mutating()))
    p3.probe_rule("probe-conf", FAIL, OK)
    lab.world["ssh"].insert(0, {"match": "probe-wrong", "stdout": "", "rc": 1})
    lab.world["ssh"].insert(0, {"match": "act-backup", "stdout": "", "rc": 0})
    p3.probe_rule("eff-backup", FAIL, OK)
    proc = p3.run("run", CLS)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    record, xml = p3.result()
    assert record["applied"][0]["mismatch"]["passed"] is False and "mismatch failed as required" in proc.stdout
    assert any(c.get("name") == "conf.mismatch" for c in xml.iter("testcase"))
    # probes travel on stdin, so count calls: clean 2 (probe, effect) + applied 4 (probe, mismatch, action, effect)
    assert len(lab.calls("ssh")) == 6


def test_a_mismatch_that_passes_invalidates_the_set_and_skips_mutating_actions(p3, lab):
    p3.write(check_set(check("conf", "probe-conf", mismatch=dict(MM)), mutating()))
    p3.probe_rule("probe-conf", FAIL, OK)
    lab.world["ssh"].insert(0, {"match": "probe-wrong", "stdout": "ok\n", "rc": 0})  # same verdict for a wrong value
    lab.world["ssh"].insert(0, {"match": "act-backup", "stdout": "", "rc": 0})
    p3.probe_rule("eff-backup", FAIL, OK)
    proc = p3.run("run", CLS)
    assert proc.returncode == 2 and "PHASE3 INVALID_SET" in proc.stdout
    record, xml = p3.result()
    assert record["valid"] is False and "do not discriminate): conf" in record["problems"][-1]
    assert record["applied"][1]["not_run"] == "not run: the set is invalid"
    assert len(lab.calls("ssh")) == 4  # clean 2 + applied probe and mismatch; the action and its effect never ran
    assert any("does not discriminate" in f.get("message", "") for f in xml.iter("failure"))


def test_no_mismatch_run_when_the_check_itself_fails(p3, lab):
    p3.write(check_set(check("conf", "probe-conf", mismatch=dict(MM))))
    p3.probe_rule("probe-conf", FAIL, FAIL)
    proc = p3.run("run", CLS)
    assert proc.returncode == 1
    record, _ = p3.result()
    assert record["applied"][0]["mismatch"] == {"varies": MM["varies"], "not_run": "the check itself failed"}
    assert len(lab.calls("ssh")) == 2  # clean + applied probe; no mismatch call


# HQ 2026-11-16 item 2: behaviour state (derived) and deferrals.
DEFERRED = {"class": CLS, "baseline": "release-0.9.10 (cf477c6)", "authoring": {"minutes": 2}, "purpose": PURPOSE,
            "deferred": {"needs": "second-node", "why": "the cron pushes to a remote backup host that the lab lacks",
                         "lifted_by": "ubuntu2"},
            "derived_from": [REF_CRON]}


def state_of(p3, *classes):
    proc = p3.run("state", *classes)
    assert proc.returncode == 0, proc.stderr
    row = next(l for l in proc.stdout.splitlines() if l.startswith(f"| {CLS} |"))
    return [c.strip() for c in row.strip("|").split("|")]


def test_a_deferral_validates_runs_nothing_and_is_the_state(p3, lab):
    p3.write(dict(DEFERRED))
    proc = p3.run("validate", CLS)
    assert proc.returncode == 0 and "DEFERRED (needs second-node, lifted by ubuntu2)" in proc.stdout
    assert p3.run("run", CLS).returncode == 2 and lab.calls("ssh") == [] and not p3.log.exists()
    assert state_of(p3, CLS)[1] == "unreviewed"  # a deferral counts only once the reviewer judged it


@pytest.mark.parametrize("mutate, message", [
    (lambda d: d["deferred"].update(needs="patience"), "deferred needs `needs`"),
    (lambda d: d["deferred"].update(why="short"), "a `why` of at least 20 characters"),
    (lambda d: d.update(derived_from=[]), "cites the baseline lines"),
    (lambda d: d.update(checks=[check("conf", "probe-conf")]), "a deferred set has no checks"),
])
def test_bad_deferrals_are_refused(p3, mutate, message):
    data = copy.deepcopy(DEFERRED)
    mutate(data)
    p3.write(data)
    proc = p3.run("validate", CLS)
    assert proc.returncode == 2 and message in proc.stderr, proc.stderr


def test_state_moves_from_none_to_unreviewed_to_pass_to_stale(p3):
    assert state_of(p3, CLS)[1] == "none"
    run_both(p3)
    assert state_of(p3, CLS)[1] == "unreviewed"
    record, _ = p3.result()
    assert record["duration_s"] >= 0 and record["authoring_minutes"] == 5
    assert p3.run("verdict", CLS, *COVERED, "--derived", "ok", "--evidence", "e").returncode == 0
    (review,) = (p3.dir / "reviews" / CLS).glob("*.json")
    assert json.loads(review.read_text())["review_s"] is not None
    row = state_of(p3, CLS)
    assert row[1] == "pass" and row[3] == "5 min"
    data = yaml.safe_load((p3.dir / f"{CLS}.yml").read_text())
    data["checks"][0]["what"] = "edited after the review"
    p3.write(data)
    assert state_of(p3, CLS)[1:3] == ["stale", "the check file changed after its review"]


def test_a_reproduced_finding_is_the_state_and_flags_a_missing_escalation(p3):
    run_both(p3, applied_for_reviewer=FAIL)  # the reviewer reproduces nothing yet: author passed, reviewer failed
    p3.probe_rule("probe-conf", FAIL, FAIL)  # both runs see the failure now
    p3.run("run", CLS)
    p3.probe_rule("probe-conf", FAIL, FAIL)
    p3.run("run", CLS, "--role", "reviewer")
    proc = p3.run("verdict", CLS, *COVERED, "--derived", "ok", "--evidence", "finding conf: x")
    assert proc.returncode == 0 and "write .codex_state/escalations/backup_rsnapshot.behaviour.md" in proc.stdout
    row = state_of(p3, CLS)
    assert row[1] == "finding" and row[2] == "conf — NO ESCALATION FILE"


def test_a_failed_review_is_the_state(p3):
    run_both(p3, applied_for_reviewer=FAIL)
    p3.run("verdict", CLS, *COVERED, "--derived", "ok", "--evidence", "e")
    assert state_of(p3, CLS)[1:3] == ["review-failed", "reproduced"]


def test_a_run_is_refused_while_another_lab_run_holds_the_lock(p3, lab):
    import subprocess
    holder = subprocess.Popen(["sleep", "60"])
    try:
        assert lab.run([str(TOOLS / "lab_lock.sh"), "take", str(holder.pid), "reviewer harness"]).returncode == 0
        p3.write(check_set(check("conf", "probe-conf")))
        proc = p3.run("run", CLS)
        assert proc.returncode == 3 and "another lab run holds the lab lock" in proc.stderr
        assert lab.calls("ssh") == [] and not p3.log.exists()  # no revert, no probe, no apply
    finally:
        holder.kill()


def test_malformed_yaml_is_invalid_not_a_crash(p3):
    (p3.dir / f"{CLS}.yml").write_text("class: backup_rsnapshot\nchecks:\n  - what: the line `root: ` breaks yaml\n")
    proc = p3.run("validate", CLS)
    assert proc.returncode != 0 and "is not valid YAML" in proc.stderr and "Traceback" not in proc.stderr


def test_a_failed_revert_records_its_reason(p3, tmp_path):
    bad = tmp_path / "bad_revert.sh"
    bad.write_text("#!/bin/sh\necho 'ERROR: The node has no IPv4 default route after 60s' >&2\nexit 1\n")
    bad.chmod(0o755)
    p3.write(check_set(check("conf", "probe-conf")))
    proc = p3.run("run", CLS, P8_PHASE3_REVERT=str(bad))
    assert proc.returncode == 3
    record, _ = p3.result()
    assert record["problems"] == ["node revert failed: ERROR: The node has no IPv4 default route after 60s"]


def test_probes_may_not_name_any_lab_node():
    """HQ 2026-11-16 item 2: the runner targets the class's own node; naming another lab VM is refused."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("phase3_nodes_t", TOOLS / "phase3.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert any("another lab host" in p for p in mod.probe_problems("ssh p8lab-rhel9 true"))
    assert any("another lab host" in p for p in mod.probe_problems("ping -c1 puppet8node"))



# HQ 2026-11-16 item 7: deferrals name the node kind that lifts them and are judged by the reviewer; `uncovered` notes.
@pytest.mark.parametrize("mutate, message", [
    (lambda d: d["deferred"].pop("lifted_by"), "lifted_by None is not a node kind"),
    (lambda d: d["deferred"].update(lifted_by="solaris"), "lifted_by 'solaris' is not a node kind"),
    (lambda d: d["deferred"].update(needs="desktop", lifted_by="ubuntu2"), "lacks the capability 'desktop'"),
    (lambda d: d["deferred"].update(needs="rhel", lifted_by="kubuntu"), "lacks the capability 'rhel-subscription'"),
])
def test_a_deferral_must_name_a_node_kind_that_lifts_it(p3, mutate, message):
    data = copy.deepcopy(DEFERRED)
    mutate(data)
    p3.write(data)
    proc = p3.run("validate", CLS)
    assert proc.returncode == 2 and message in proc.stderr, proc.stderr


def test_the_reviewer_judges_a_deferral_and_only_then_it_counts(p3):
    p3.write(dict(DEFERRED))
    spot = p3.run("spot", CLS)
    assert "DEFERRAL — needs second-node, lifted by node kind ubuntu2" in spot.stdout
    assert '  |     command => "/usr/bin/rsnapshot -c ${myconffile} daily",' in spot.stdout  # baseline lines, fresh
    proc = p3.run("verdict", CLS, *COVERED, "--derived", "ok", "--evidence", "lines 13-19: cron needs a remote host")
    assert proc.returncode == 0 and proc.stdout.startswith("VERDICT PASS")
    assert state_of(p3, CLS)[1:3] == ["deferred", "second-node, lifted by ubuntu2"]
    data = copy.deepcopy(DEFERRED)
    data["deferred"]["why"] += " (edited)"
    p3.write(data)
    assert state_of(p3, CLS)[1] == "unreviewed"
    p3.run("verdict", CLS, *COVERED, "--derived", "fail", "--evidence", "the reason does not follow from the lines")
    assert state_of(p3, CLS)[1:3] == ["review-failed", "deferral rejected"]


@pytest.mark.parametrize("uncovered, message", [
    ([{"what": "x", "why": "short", "lifted_by": "kubuntu"}], "uncovered[0] takes what, why"),
    ([{"what": "x", "why": "a long enough reason for the note", "lifted_by": "solaris"}], "is not a node kind"),
])
def test_uncovered_notes_are_validated(p3, uncovered, message):
    p3.write(check_set(check("conf", "probe-conf"), uncovered=uncovered))
    proc = p3.run("validate", CLS)
    assert proc.returncode == 2 and message in proc.stderr
    p3.write(check_set(check("conf", "probe-conf"),
                       uncovered=[{"what": "x", "why": "a long enough reason for the note", "lifted_by": "kubuntu"}]))
    assert p3.run("validate", CLS).returncode == 0


# ------------------------------------------------------------------ peer node (HQ 2026-11-17 ruling 1: the VPN client)
PEER = {"kind": "ubuntu2", "why": "the VPN client must be a second machine on the lab network", "files": ["/etc/x/ca.crt"]}


def test_a_peer_set_validates_and_peer_probes_may_name_only_the_class_node(p3):
    p3.write(check_set(check("conf", "probe-conf"),
                       check("client", "ping -c1 192.168.56.20 && ls /run/p8test-from-node/ca.crt", host="peer"),
                       peer=PEER))
    assert p3.run("validate", CLS).returncode == 0
    for probe, message in [("ping -c1 192.168.56.10", "names another lab host"),
                           ("ssh p8lab-ubuntu2 true", "names another lab host")]:
        p3.write(check_set(check("conf", "probe-conf"), check("client", probe, host="peer"), peer=PEER))
        proc = p3.run("validate", CLS)
        assert proc.returncode == 2 and message in proc.stderr, proc.stderr
    p3.write(check_set(check("conf", "ping -c1 192.168.56.20")))  # a node probe still names no lab host
    assert "names another lab host" in p3.run("validate", CLS).stderr


@pytest.mark.parametrize("top, on, message", [
    ({}, "peer", "host: peer needs the set's `peer` block"),
    ({"peer": {**PEER, "kind": "gnome"}}, "peer", "lacks the capability 'second-node'"),
    ({"peer": {**PEER, "kind": "ubuntu"}}, "peer", "the peer is the class's own node"),
    ({"peer": {**PEER, "files": ["relative/path"]}}, "peer", "peer.files is a list of absolute paths"),
    ({"peer": PEER}, "elsewhere", "host must be node|peer"),
])
def test_bad_peer_declarations_are_refused(p3, top, on, message):
    p3.write(check_set(check("conf", "probe-conf"), check("client", "probe-client", host=on), **top))
    proc = p3.run("validate", CLS)
    assert proc.returncode == 2 and message in proc.stderr, proc.stderr


def test_a_peer_run_reverts_both_nodes_hands_the_files_over_and_powers_the_peer_off(p3, lab, tmp_path):
    labvm = tmp_path / "labvm.sh"
    labvm.write_text("#!/bin/sh\necho \"labvm $*\" >> \"$(dirname \"$0\")/log\"\n")
    labvm.chmod(0o755)
    (tmp_path / "revert.sh").write_text(REVERT_STUB.format(log="reverted $*"))
    p3.write(check_set(check("conf", "probe-conf"), check("client", "probe-client", host="peer"), peer=PEER))
    p3.probe_rule("probe-conf", FAIL, OK)
    p3.probe_rule("probe-client", FAIL, OK)
    lab.world["ssh"].insert(0, {"match": "base64 -w0 /etc/x/ca.crt", "outputs": [{"rc": 0, "stdout": "\n"},
                                                                                 {"rc": 0, "stdout": "Q0EK\n"}]})
    proc = p3.run("run", CLS, P8_PHASE3_LABVM=str(labvm))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    record, _ = p3.result()
    assert record["outcome"] == "ALL_PASS" and record["peer"] == "ubuntu2"
    assert [r.get("host") for r in record["applied"]] == [None, "peer"]
    assert p3.log.read_text().splitlines() == ["reverted --node ubuntu", "reverted --node ubuntu2",
                                               f"harness puppet_infrastructure::{CLS}", "labvm stop p8lab-ubuntu2"]
    peer_calls = [c for c in lab.calls("ssh") if c[-2] == "p8lab-ubuntu2"]
    assert len(peer_calls) == 2  # clean + applied
    # both nodes fresh, both recorded (HQ 2026-11-17 batch-8 ruling 3)
    assert {k: (v["kind"], v["boot_id"], v["fresh"]) for k, v in record["nodes"].items()} == \
        {"node": ("ubuntu", "boot-ubuntu", True), "peer": ("ubuntu2", "boot-ubuntu2", True)}
    stdin = [c for c in lab.calls("ssh") if c[-2] == "p8lab-ubuntu2"]
    assert all(c[-1] == "sudo -n bash -s" for c in stdin)



def test_a_bare_yaml_on_key_cannot_select_the_peer(p3):
    # YAML 1.1 reads `on:` as the boolean true: the field is `host`, and a written `on: peer` stays a node probe
    (p3.dir / f"{CLS}.yml").write_text(yaml.safe_dump(check_set(check("conf", "probe-conf")), sort_keys=False)
                                       .replace("  probe: probe-conf", "  on: peer\n  probe: probe-conf"))
    assert yaml.safe_load((p3.dir / f"{CLS}.yml").read_text())["checks"][0].get(True) == "peer"
    proc = p3.run("validate", CLS)
    assert proc.returncode == 2 and "a key read as a boolean" in proc.stderr


# ------------------------------------------------------------------ desktop session (2026-11-17, HQ batch-8 ruling 5)

SESSION = {"user": "p8testuser", "desktop": "plasma", "why": "the exec applies only while the user is logged in"}
KDE = {"P8_NODE": "kubuntu"}  # the real inventory: kubuntu is active with the kde capability


def session_lab(p3, lab, login="SESSION_UP\n", runs=("Notice: /Stage[main]/X/Exec[configure p8testuser]/returns: "
                                                     "executed successfully\nAGENT_RC=2\n", "AGENT_RC=0\n")):
    p3.write(check_set(check("conf", "probe-conf"), session=SESSION))
    p3.probe_rule("probe-conf", FAIL, OK)
    lab.world["ssh"].insert(0, {"match": "zz-p8test-autologin", "stdout": login})
    lab.world["ssh"].insert(0, {"match": r"puppet agent -t --detailed-exitcodes",
                                "outputs": [{"rc": 0, "stdout": out} for out in runs]})


def test_a_session_set_needs_a_kde_node_and_a_fixture_user(p3):
    p3.write(check_set(check("conf", "probe-conf"), session=SESSION))
    assert p3.run("validate", CLS, **KDE).returncode == 0
    proc = p3.run("validate", CLS)  # the default node, ubuntu, has no kde
    assert proc.returncode == 2 and "lacks the capability 'kde'" in proc.stderr
    for bad, message in [({**SESSION, "user": "salatiel"}, "p8test* fixture account"),
                         ({**SESSION, "desktop": "gnome"}, "must be plasma"),
                         ({"user": "p8testuser"}, "session takes user, desktop and why")]:
        p3.write(check_set(check("conf", "probe-conf"), session=bad))
        proc = p3.run("validate", CLS, **KDE)
        assert proc.returncode == 2 and message in proc.stderr, proc.stderr


def test_a_session_run_logs_the_user_in_after_the_apply_then_makes_two_agent_runs(p3, lab):
    session_lab(p3, lab)
    proc = p3.run("run", CLS, **KDE)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    record, _ = p3.result()
    s = record["session"]
    assert s["user"] == "p8testuser" and s["up"] is True
    assert [r["rc"] for r in s["runs"]] == [2, 0] and len(s["runs"][0]["events"]) == 1 and s["runs"][1]["events"] == []
    sent = [json.loads(l) for l in (lab.calls_path.parent / "calls.jsonl.stdin").read_text().splitlines()]
    login = next(i for i, s in enumerate(sent) if "zz-p8test-autologin" in s[2])
    agents = [i for i, s in enumerate(sent) if "puppet agent -t --detailed-exitcodes" in s[2]]
    probes = [i for i, s in enumerate(sent) if "probe-conf" in s[2]]
    assert probes[0] < login < agents[0] < agents[1] < probes[-1] and len(agents) == 2  # clean, login, 2 runs, APPLIED
    assert all(s[1].endswith("p8lab-kubuntu sudo -n bash -s") for s in sent if "zz-p8test" in s[2] or "puppet" in s[2])
    assert p3.log.read_text().splitlines()[-1].startswith("harness ")  # the harness applied before the login


def test_a_session_that_does_not_come_up_is_an_environment_failure(p3, lab):
    session_lab(p3, lab, login="SESSION_DOWN\n")
    proc = p3.run("run", CLS, **KDE)
    record, _ = p3.result()
    assert proc.returncode == 3 and record["outcome"] == "ENVIRONMENT_FAILED"
    assert "session did not come up" in record["problems"][-1]
    assert not [c for c in lab.calls("ssh") if "puppet agent" in " ".join(c)]


def test_a_second_run_with_changes_fails_the_apply(p3, lab):
    changed = "Notice: /Stage[main]/X/Exec[configure p8testuser]/returns: executed successfully\nAGENT_RC=2\n"
    session_lab(p3, lab, runs=(changed, changed))
    proc = p3.run("run", CLS, **KDE)
    record, _ = p3.result()
    assert proc.returncode == 3 and record["outcome"] == "APPLY_FAILED"
    assert "not applied cleanly and idempotently" in record["problems"][-1]


def test_the_login_and_agent_runs_stay_out_of_probes():
    import sys
    sys.path.insert(0, str(TOOLS))
    import phase3
    assert phase3.probe_problems("timeout 900 /opt/puppetlabs/bin/puppet agent -t")  # probes keep the Puppet ban


# ------------------------------------------------------------------ peer agent run (2026-11-18, HQ ruling C2: Hashman)

MASTER_ROLE = {"P8_NODE": "puppetserver"}  # the real inventory: the master-role node, capability puppet-server
PEER_AGENT = {"after": "user-changes-password", "certname": "p8test-hashman-client",
              "why": "the user record reaches another machine only through its agent run against the server"}


def peer_agent_set(**over):
    return check_set(check("page", "probe-page"),
                     mutating("user-changes-password", action="act-change", effect="eff-change",
                              mutates="changes the fixture user's password in the web page", host="peer"),
                     mutating("new-password-accepted", action="act-login", effect="eff-login",
                              mutates="authenticates the fixture user with PAM", host="peer"),
                     peer={"kind": "ubuntu2", "why": "the browser and the agent of another machine run there"},
                     peer_agent={**PEER_AGENT, **over})


def test_a_peer_agent_set_needs_a_puppet_server_node_a_fixture_identity_and_a_mutating_anchor(p3):
    p3.write(peer_agent_set())
    assert p3.run("validate", CLS, **MASTER_ROLE).returncode == 0
    proc = p3.run("validate", CLS)  # the default node, ubuntu, is no Puppet server
    assert proc.returncode == 2 and "lacks the capability 'puppet-server'" in proc.stderr
    for over, message in [({"certname": "salatiel"}, "p8test* fixture identity"),
                          ({"after": "page"}, "must name a mutating check"),
                          ({"why": "short"}, "peer_agent takes after, certname and why")]:
        p3.write(peer_agent_set(**over))
        proc = p3.run("validate", CLS, **MASTER_ROLE)
        assert proc.returncode == 2 and message in proc.stderr, proc.stderr
    data = peer_agent_set()
    del data["peer"]
    for c in data["checks"]:
        c.pop("host", None)
    p3.write(data)
    proc = p3.run("validate", CLS, **MASTER_ROLE)
    assert proc.returncode == 2 and "needs the set's `peer` block" in proc.stderr


def test_the_peer_agent_run_follows_its_anchor_against_the_class_node_from_its_own_confdir(p3, lab, tmp_path):
    labvm = tmp_path / "labvm.sh"
    labvm.write_text("#!/bin/sh\necho \"labvm $*\" >> \"$(dirname \"$0\")/log\"\n")
    labvm.chmod(0o755)
    p3.write(peer_agent_set())
    p3.probe_rule("probe-page", FAIL, OK)
    lab.world["read_stdin"] = True
    for marker in ("act-change", "act-login"):
        lab.world["ssh"].insert(0, {"match": marker, "stdout": "", "rc": 0})
    p3.probe_rule("eff-change", FAIL, OK)
    p3.probe_rule("eff-login", FAIL, OK)
    lab.world["ssh"].insert(0, {"match": r"/etc/p8test-agent/p8test-hashman-client", "stdout":
                                "Notice: /Stage[main]/Main/Node[p8test-hashman-client]/Puppet_infrastructure::User"
                                "[p8hashuser]/User[p8hashuser]/password: changed [redacted] to [redacted]\nAGENT_RC=2\n"})
    proc = p3.run("run", CLS, P8_PHASE3_LABVM=str(labvm), **MASTER_ROLE)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    record, _ = p3.result()
    run = record["peer_agent"]
    assert run["certname"] == "p8test-hashman-client" and run["server"] == "p8lab-puppetserver"
    assert run["rc"] == 2 and len(run["events"]) == 1
    sent = [json.loads(l) for l in (lab.calls_path.parent / "calls.jsonl.stdin").read_text().splitlines()]
    order = [i for i, s in enumerate(sent) if any(m in s[2] for m in ("act-change", "eff-change", "p8test-agent",
                                                                       "act-login"))]
    kinds = ["agent" if "p8test-agent" in sent[i][2] else sent[i][2].strip().split()[-1] for i in order]
    # clean: the effect only; applied: action, effect, then the agent run, then the next mutating check
    assert kinds == ["eff-change", "act-change", "eff-change", "agent", "act-login"]
    agent = next(s for s in sent if "p8test-agent" in s[2])
    assert agent[1].endswith("p8lab-ubuntu2 sudo -n bash -s")  # on the peer, never on the node
    assert '--confdir "$d"' in agent[2] and "server = %s" in agent[2] and "p8lab-puppetserver" in agent[2]
    assert "echo '192.168.56.26 p8lab-puppetserver' >> /etc/hosts" in agent[2]


def test_the_peer_agent_run_stays_out_of_probes():
    import sys
    sys.path.insert(0, str(TOOLS))
    import phase3
    assert phase3.probe_problems("timeout 900 /opt/puppetlabs/bin/puppet agent -t --confdir /etc/p8test-agent/x")


def test_a_file_a_node_action_writes_reaches_the_next_peer_check(p3, lab, tmp_path):
    # 2026-11-18 (hashman): the admin's action on the node writes the initial password; the peer's browser needs it
    labvm = tmp_path / "labvm.sh"
    labvm.write_text("#!/bin/sh\necho \"labvm $*\" >> \"$(dirname \"$0\")/log\"\n")
    labvm.chmod(0o755)
    p3.write(check_set(check("conf", "probe-conf"),
                       mutating("admin-adds", action="act-admin", effect="eff-admin", mutates="adds the fixture user"),
                       mutating("peer-uses", action="act-peer", effect="eff-peer", host="peer",
                                mutates="logs the fixture user in from the peer"),
                       peer={**PEER, "files": ["/run/p8test-x/initial"]}))
    p3.probe_rule("probe-conf", FAIL, OK)
    lab.world["read_stdin"] = True
    lab.world["ssh"].insert(0, {"match": "act-admin", "stdout": "", "rc": 0})
    lab.world["ssh"].insert(0, {"match": "act-peer", "stdout": "", "rc": 0})
    p3.probe_rule("eff-admin", FAIL, OK)
    p3.probe_rule("eff-peer", FAIL, OK)
    # clean phase, before the applied phase, before the peer check: empty, empty, then written by the node action
    lab.world["ssh"].insert(0, {"match": "base64 -w0 /run/p8test-x/initial", "outputs": [
        {"rc": 0, "stdout": "\n"}, {"rc": 0, "stdout": "\n"}, {"rc": 0, "stdout": "aW5pdGlhbAo=\n"}]})
    proc = p3.run("run", CLS, P8_PHASE3_LABVM=str(labvm))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    sent = [json.loads(l) for l in (lab.calls_path.parent / "calls.jsonl.stdin").read_text().splitlines()]
    act_peer = next(s for s in sent if "act-peer" in s[2])
    assert "aW5pdGlhbAo=" in act_peer[2] and "/run/p8test-from-node/initial" in act_peer[2]



# ------------------------------------------------------------------ purpose coverage (HQ 2026-11-18 ruling C1)

def test_a_set_must_state_the_class_purpose(p3):
    data = check_set(check("conf", "probe-conf"))
    del data["purpose"]
    p3.write(data)
    proc = p3.run("validate", CLS)
    assert proc.returncode == 2 and "purpose: the class's purpose" in proc.stderr
    assert state_of(p3, CLS)[1:3] == ["unjudged", "the set states no purpose yet"]


def test_the_verdict_needs_a_purpose_judgement_and_a_gap_fails_it(p3):
    run_both(p3)
    proc = p3.run("verdict", CLS, "--derived", "ok", "--evidence", "conf: lines 5-11 declare the file")
    assert proc.returncode != 0 and "--purpose covered|gap" in proc.stderr
    proc = p3.run("verdict", CLS, "--purpose", "gap", "--purpose-evidence", "nothing restores a file from a snapshot",
                  "--derived", "ok", "--evidence", "conf: lines 5-11 declare the file")
    assert proc.returncode == 1 and proc.stdout.startswith("VERDICT FAIL") and '"purpose": "fail"' in proc.stdout
    assert "evidence purpose gap: nothing restores a file" in proc.stdout
    assert state_of(p3, CLS)[1:3] == ["review-failed", "purpose"]


def test_a_review_before_the_purpose_judgement_leaves_the_set_unjudged(p3):
    run_both(p3)
    assert p3.run("verdict", CLS, *COVERED, "--derived", "ok", "--evidence", "e").returncode == 0
    (path,) = (p3.dir / "reviews" / CLS).glob("*.json")
    old = json.loads(path.read_text())
    del old["checks"]["purpose"]  # as every review before 2026-11-18 was written
    path.write_text(json.dumps(old))
    assert state_of(p3, CLS)[1:3] == ["unjudged", "the review predates the purpose judgement"]


# ------------------------------------------------------------------ node agent run (2026-11-18: drift correction)

def test_a_node_agent_run_follows_its_anchor_and_is_recorded(p3, lab):
    p3.write(check_set(check("conf", "probe-conf"),
                       mutating("rogue-rule", action="act-rogue", effect="eff-rogue", mutates="adds an unmanaged rule"),
                       mutating("rogue-purged", action="true", effect="eff-purged", mutates="none beyond reading"),
                       node_agent={"after": "rogue-rule", "why": "the class purges what it does not manage on its run"}))
    p3.probe_rule("probe-conf", FAIL, OK)
    lab.world["read_stdin"] = True
    lab.world["ssh"].insert(0, {"match": "act-rogue", "stdout": "", "rc": 0})
    p3.probe_rule("eff-rogue", FAIL, OK)
    p3.probe_rule("eff-purged", FAIL, OK)
    lab.world["ssh"].insert(0, {"match": r"puppet agent -t --detailed-exitcodes", "stdout":
                                "Notice: /Stage[main]/X/Firewall[9999 rogue]/ensure: removed\nAGENT_RC=2\n"})
    proc = p3.run("run", CLS)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    record, _ = p3.result()
    assert record["node_agent"]["rc"] == 2 and len(record["node_agent"]["events"]) == 1
    sent = [json.loads(l) for l in (lab.calls_path.parent / "calls.jsonl.stdin").read_text().splitlines()]
    order = [("agent" if "puppet agent" in s[2] else next(m for m in ("act-rogue", "eff-rogue", "eff-purged") if m in s[2]))
             for s in sent if any(m in s[2] for m in ("act-rogue", "eff-rogue", "eff-purged", "puppet agent"))]
    assert order == ["eff-rogue", "eff-purged", "act-rogue", "eff-rogue", "agent", "eff-purged"]


def test_a_node_agent_needs_a_mutating_anchor(p3):
    p3.write(check_set(check("conf", "probe-conf"), node_agent={"after": "conf", "why": "x" * 25}))
    proc = p3.run("validate", CLS)
    assert proc.returncode == 2 and "node_agent.after must name a mutating check" in proc.stderr


def test_only_a_mutating_action_may_take_a_longer_timeout(p3):
    p3.write(check_set(check("conf", "probe-conf"), mutating(timeout=300)))
    assert p3.run("validate", CLS).returncode == 0
    for bad in (check("conf2", "probe", timeout=300), mutating("m2", timeout=900), mutating("m3", timeout="5")):
        p3.write(check_set(check("conf", "probe-conf"), bad))
        proc = p3.run("validate", CLS)
        assert proc.returncode == 2 and "timeout (seconds, 1-600)" in proc.stderr, proc.stderr
