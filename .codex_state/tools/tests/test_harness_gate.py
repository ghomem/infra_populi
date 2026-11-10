"""Gate v2 (step 1.1): run 2 must exit 0, exec/removed events fail, agent runs time out."""

from conftest import TOOLS
import pytest

pytestmark = pytest.mark.slow  # excluded from the per-commit fast subset (HQ 2026-11-11 ruling 3)

SCRIPT = str(TOOLS / "test_class.sh")
AGENT = r"puppet8node sudo /opt/puppetlabs/bin/puppet agent -t"
EXEC_EVENT = "Notice: /Stage[main]/Main/Node[puppet8node]/Exec[p8test unguarded exec]/returns: executed successfully\n"
PLUGINSYNC = "\x1b[mNotice: /File[/opt/puppetlabs/puppet/cache/lib/facter/apt_updates.rb]/ensure: defined content as '{sha256}f8'\x1b[0m\n"
APPLIED = "Notice: Applied catalog in 1.02 seconds\n"


def agent_runs(lab, *runs):
    lab.world["ssh"].insert(0, {"match": AGENT, "outputs": list(runs)})


def harness(lab, **env):
    return lab.run([SCRIPT, "--fixture", "unguarded_exec"], env={k: str(v) for k, v in env.items()})


def test_unguarded_exec_is_red(lab):
    agent_runs(lab, {"rc": 2, "stdout": EXEC_EVENT + APPLIED}, {"rc": 2, "stdout": EXEC_EVENT + APPLIED})
    proc = harness(lab)
    assert proc.returncode == 1
    assert "not idempotent" in proc.stderr and "executed successfully" in proc.stderr
    assert "GREEN" not in proc.stdout


def test_run2_exit_2_without_matching_text_is_red(lab):
    agent_runs(lab, {"rc": 2, "stdout": APPLIED}, {"rc": 2, "stdout": "Warning: something\n" + APPLIED})
    proc = harness(lab)
    assert proc.returncode == 1
    assert "Run 2 exited 2" in proc.stderr


def test_removed_on_run2_is_red_even_with_exit_0(lab):
    agent_runs(lab, {"rc": 2, "stdout": APPLIED},
               {"rc": 0, "stdout": "Notice: /Firewall[999 drop]/ensure: removed\n" + APPLIED})
    assert harness(lab).returncode == 1


def test_clean_run2_is_green(lab):
    agent_runs(lab, {"rc": 2, "stdout": EXEC_EVENT + APPLIED}, {"rc": 0, "stdout": APPLIED})
    proc = harness(lab)
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip().endswith("GREEN: run 2 exited 0 with no change events (gate v2).")


def test_run1_failure_is_reported_with_exit_code(lab):
    agent_runs(lab, {"rc": 4, "stdout": "Error: boom\n"})
    proc = harness(lab)
    assert proc.returncode == 1
    assert "Agent run 1 failed (exit 4)" in proc.stderr


def test_hung_agent_run_times_out(lab):
    agent_runs(lab, {"rc": 0, "sleep": 5, "stdout": APPLIED})
    proc = harness(lab, AGENT_TIMEOUT_SECONDS=1)
    assert proc.returncode == 1
    assert "Agent run 1 timed out after 1s" in proc.stderr


def test_exactly_two_agent_runs(lab):
    agent_runs(lab, {"rc": 2, "stdout": APPLIED}, {"rc": 0, "stdout": APPLIED})
    assert harness(lab).returncode == 0
    agent_calls = [c for c in lab.calls("ssh") if "agent -t" in " ".join(c)]
    assert len(agent_calls) == 2


def test_fixture_name_is_validated(lab):
    proc = lab.run([SCRIPT, "--fixture", "../etc/passwd"])
    assert proc.returncode == 1 and "Invalid fixture name" in proc.stderr


def test_revert_first_restores_before_deploy_and_counts_run1_events(lab):
    agent_runs(lab, {"rc": 2, "stdout": EXEC_EVENT + EXEC_EVENT + APPLIED}, {"rc": 0, "stdout": APPLIED})
    proc = lab.run([SCRIPT, "--revert-first", "--fixture", "guarded_exec"])
    assert proc.returncode == 0, proc.stderr
    calls = lab.calls()
    restore = calls.index(["VBoxManage", "snapshot", "ubuntu24-puppet8-Node", "restore", "P8NODE_BASELINE_GREEN_v2"])
    first_rsync = next(i for i, c in enumerate(calls) if c[0] == "rsync")
    assert restore < first_rsync
    assert "RUN1_EVENTS: 2 catalog, 0 pluginsync (rc 2; node reverted first)" in proc.stdout


def test_revert_first_with_no_run1_events_warns(lab):
    agent_runs(lab, {"rc": 0, "stdout": APPLIED}, {"rc": 0, "stdout": APPLIED})
    proc = lab.run([SCRIPT, "--revert-first", "--fixture", "guarded_exec"])
    assert proc.returncode == 0
    assert "applied nothing" in proc.stderr


def test_failed_revert_stops_before_deploy(lab):
    lab.world["vms"]["ubuntu24-puppet8-Node"]["state"] = "restoring"
    proc = lab.run([SCRIPT, "--revert-first", "--fixture", "guarded_exec"])
    assert proc.returncode == 1 and "Node revert failed" in proc.stderr
    assert lab.calls("rsync") == []


def test_revert_first_rejects_render_only(lab):
    proc = lab.run([SCRIPT, "--revert-first", "--render-only", "puppet_infrastructure::dns_client"])
    assert proc.returncode == 1


def test_pluginsync_is_not_counted_as_class_events(lab):
    # Real shape from puppet_backup on 2026-10-26: 116 pluginsync lines, 9 catalog events.
    agent_runs(lab, {"rc": 2, "stdout": PLUGINSYNC * 3 + APPLIED}, {"rc": 0, "stdout": APPLIED})
    proc = lab.run([SCRIPT, "--revert-first", "--fixture", "guarded_exec"])
    assert "RUN1_EVENTS: 0 catalog, 3 pluginsync" in proc.stdout
    assert "applied nothing" in proc.stderr


COVERAGE_CALL = r"sudo -n python3 - puppet_infrastructure::puppet_backup$"
CLEAN = [{"rc": 2, "stdout": APPLIED}, {"rc": 0, "stdout": APPLIED}]


def test_coverage_lists_target_resources_and_is_green(lab):
    real = TOOLS.parent / "logs" / "green" / "puppet_backup.json"
    before = real.stat().st_mtime_ns if real.exists() else None
    agent_runs(lab, *CLEAN)
    lab.world["ssh"].insert(0, {"match": COVERAGE_CALL, "stdout":
        "COVERAGE puppet_infrastructure::puppet_backup: 2 concrete resources (+1 defined-type instances)\n"
        "  Cron[cron_puppet_backup]\n"})
    proc = lab.run([SCRIPT, "puppet_infrastructure::puppet_backup"])
    assert proc.returncode == 0, proc.stderr
    assert "COVERAGE puppet_infrastructure::puppet_backup: 2 concrete" in proc.stdout
    coverage_calls = [c for c in lab.calls("ssh") if "python3 -" in " ".join(c)]
    assert len(coverage_calls) == 1
    assert "filesystem_base" not in " ".join(coverage_calls[0])  # required base is not a target
    # a stub GREEN stamps into the test's own dir, never the real repo's logs (record_green.sh trusts those)
    assert (lab.root / "green" / "puppet_backup.json").is_file()
    assert (real.stat().st_mtime_ns if real.exists() else None) == before


def test_zero_coverage_is_red(lab):
    agent_runs(lab, *CLEAN)
    lab.world["ssh"].insert(0, {"match": COVERAGE_CALL, "rc": 3, "stdout":
        "COVERAGE puppet_infrastructure::puppet_backup: 0 concrete resources (+0 defined-type instances)\n"})
    proc = lab.run([SCRIPT, "puppet_infrastructure::puppet_backup"])
    assert proc.returncode == 1
    assert "no concrete resources" in proc.stderr and "GREEN" not in proc.stdout


def test_unreadable_catalog_is_red(lab):
    agent_runs(lab, *CLEAN)
    lab.world["ssh"].insert(0, {"match": COVERAGE_CALL, "rc": 1})
    proc = lab.run([SCRIPT, "puppet_infrastructure::puppet_backup"])
    assert proc.returncode == 1 and "could not read" in proc.stderr


RESOURCE_API_CREATE = ("Notice: /Stage[main]/Puppet_infrastructure::Firewall_addon_caching_nameserver/"
                       "Firewall[1301 accept nameserver]/ensure: defined 'ensure' as 'present'\n")


def test_resource_api_creation_counts_on_run1(lab):
    # Real line from puppetlabs-firewall 8.3.0 on 2026-10-27 (sweep: counted as 0 before the fix).
    agent_runs(lab, {"rc": 2, "stdout": RESOURCE_API_CREATE + APPLIED}, {"rc": 0, "stdout": APPLIED})
    proc = lab.run([SCRIPT, "--revert-first", "--fixture", "guarded_exec"])
    assert "RUN1_EVENTS: 1 catalog" in proc.stdout


def test_resource_api_creation_on_run2_is_red(lab):
    agent_runs(lab, {"rc": 2, "stdout": RESOURCE_API_CREATE + APPLIED}, {"rc": 0, "stdout": RESOURCE_API_CREATE + APPLIED})
    proc = harness(lab)
    assert proc.returncode == 1 and "not idempotent" in proc.stderr


def test_harness_writes_revert_and_harness_metrics_events_on_green_and_red(lab):
    import json
    agent_runs(lab, {"rc": 2, "stdout": APPLIED}, {"rc": 0, "stdout": APPLIED})
    lab.world["ssh"].insert(0, {"match": COVERAGE_CALL, "stdout":
        "COVERAGE puppet_infrastructure::puppet_backup: 2 concrete resources (+1 defined-type instances)\n"})
    lab.world["ssh"].insert(0, {"match": "last_run_summary.yaml", "stdout":
        "resources:\n  changed: 9\n  total: 26\ntime:\n  total: 10.4\ntransaction_uuid: u-1\n"})
    assert lab.run([SCRIPT, "--revert-first", "puppet_infrastructure::puppet_backup"]).returncode == 0
    events = [json.loads(l) for l in (lab.root / "metrics" / "events.jsonl").read_text().splitlines()]
    assert [e["kind"] for e in events] == ["revert", "harness"]
    assert events[0]["data"]["snapshot"] == "P8NODE_BASELINE_GREEN_v2"
    h = events[1]["data"]
    assert h["rc"] == 0 and h["revert_first"] is True and h["run1_events"] == 0 and h["reason"] is None
    assert [r["transaction_uuid"] for r in h["agent_runs"]] == ["u-1", "u-1"] and h["agent_runs"][0]["res_changed"] == 9

    agent_runs(lab, {"rc": 4, "stdout": "Error: boom\n"})
    assert lab.run([SCRIPT, "puppet_infrastructure::puppet_backup"]).returncode == 1
    last = json.loads((lab.root / "metrics" / "events.jsonl").read_text().splitlines()[-1])
    assert last["kind"] == "harness" and last["data"]["rc"] == 1 and "Agent run 1 failed" in last["data"]["reason"]


def test_fixture_runs_write_no_metrics(lab):
    agent_runs(lab, {"rc": 2, "stdout": APPLIED}, {"rc": 0, "stdout": APPLIED})
    assert harness(lab).returncode == 0
    assert not (lab.root / "metrics" / "events.jsonl").exists()


# --- HQ 2026-11-10 ruling 1: plan expected_run2_events (packages_base: Exec[apt_update])
APT_EVENT = "Notice: /Stage[main]/Apt::Update/Exec[apt_update]/returns: executed successfully\n"
PKG_COVERAGE = {"match": r"python3 - puppet_infrastructure::packages_base$", "stdout":
                "COVERAGE puppet_infrastructure::packages_base: 7 concrete resources (+0 defined-type instances)\n"}


def test_expected_run2_event_only_is_green(lab):
    agent_runs(lab, {"rc": 2, "stdout": APT_EVENT + APPLIED}, {"rc": 2, "stdout": APT_EVENT + APPLIED})
    lab.world["ssh"].insert(0, PKG_COVERAGE)
    proc = lab.run([SCRIPT, "puppet_infrastructure::packages_base"])
    assert proc.returncode == 0, proc.stderr
    assert "RUN2_EXPECTED_EVENTS: 1 from Exec[apt_update]" in proc.stdout
    assert "GREEN: run 2 events limited to the plan's expected_run2_events (Exec[apt_update])" in proc.stdout


def test_an_unexpected_event_beside_an_expected_one_is_red(lab):
    other = "Notice: /Stage[main]/Puppet_infrastructure::Packages_base/Package[vim]/ensure: created\n"
    agent_runs(lab, {"rc": 2, "stdout": APPLIED}, {"rc": 2, "stdout": APT_EVENT + other + APPLIED})
    lab.world["ssh"].insert(0, PKG_COVERAGE)
    proc = lab.run([SCRIPT, "puppet_infrastructure::packages_base"])
    assert proc.returncode == 1 and "Package[vim]" in proc.stderr and "not idempotent" in proc.stderr


def test_expected_events_do_not_excuse_a_failed_run2(lab):
    agent_runs(lab, {"rc": 2, "stdout": APPLIED}, {"rc": 6, "stdout": APT_EVENT + "Error: boom\n"})
    lab.world["ssh"].insert(0, PKG_COVERAGE)
    proc = lab.run([SCRIPT, "puppet_infrastructure::packages_base"])
    assert proc.returncode == 1


def test_class_without_expected_events_still_fails_on_the_same_event(lab):
    agent_runs(lab, {"rc": 2, "stdout": APPLIED}, {"rc": 2, "stdout": APT_EVENT + APPLIED})
    lab.world["ssh"].insert(0, {"match": COVERAGE_CALL, "stdout":
        "COVERAGE puppet_infrastructure::puppet_backup: 2 concrete resources (+1 defined-type instances)\n"})
    proc = lab.run([SCRIPT, "puppet_infrastructure::puppet_backup"])
    assert proc.returncode == 1 and "Exec[apt_update]" in proc.stderr


def test_inherited_expected_run2_is_named_in_output_and_metrics(lab):
    import json
    # sysmon_base's required_base includes packages_base, whose plan entry is Exec[apt_update]
    agent_runs(lab, {"rc": 2, "stdout": APPLIED}, {"rc": 2, "stdout": APT_EVENT + APPLIED})
    lab.world["ssh"].insert(0, {"match": r"python3 - puppet_infrastructure::sysmon_base$", "stdout":
                                "COVERAGE puppet_infrastructure::sysmon_base: 13 concrete resources (+0 defined-type instances)\n"})
    proc = lab.run([SCRIPT, "puppet_infrastructure::sysmon_base"])
    assert proc.returncode == 0, proc.stderr
    assert "[own: none; inherited: Exec[apt_update] via packages_base]" in proc.stdout
    h = [json.loads(l) for l in (lab.root / "metrics" / "events.jsonl").read_text().splitlines()][-1]["data"]
    assert h["run2_expected"] == {"hits": 1, "own": [], "inherited": {"packages_base": ["Exec[apt_update]"]}}


# --- run-2 REPORT stage (batch 3, nginx_frontend_domain): a change logged below notice has no console line
REPORT_CALL = r"puppet/bin/ruby - /opt/puppetlabs/puppet/cache/state/last_run_report.yaml"
DEBUG_NOTIFY = ("Notify[Generated Upstream members for p8test.example.com are: {127.0.0.1:8080 in p8test.example.com"
                " => {server => 127.0.0.1, port => 8080}}]")


def report(lab, stdout, rc=0):
    lab.world["ssh"].insert(0, {"match": REPORT_CALL, "stdout": stdout, "rc": rc})


def test_silent_report_change_without_expectation_is_red(lab):
    agent_runs(lab, {"rc": 2, "stdout": APPLIED}, {"rc": 2, "stdout": APPLIED})
    report(lab, "Notify[debug note]\n")
    proc = harness(lab)
    assert proc.returncode == 1 and "not idempotent" in proc.stderr
    assert "Run-2 report, changed with no console event (log level below notice): Notify[debug note]" in proc.stderr


def test_unreadable_run2_report_fails_closed(lab):
    agent_runs(lab, {"rc": 2, "stdout": APPLIED}, {"rc": 2, "stdout": APPLIED})
    report(lab, "", rc=255)
    proc = harness(lab)
    assert proc.returncode == 1 and "report could not be read" in proc.stderr and "GREEN" not in proc.stdout


def test_expected_silent_event_with_a_glob_title_is_green(lab):
    params = lab.root / "home" / ".config" / "infra_populi" / "params"
    params.mkdir(parents=True)
    (params / "puppet_infrastructure::nginx_frontend_domain.json").write_text('{"domain": "p8test.example.com"}')
    agent_runs(lab, {"rc": 2, "stdout": APPLIED}, {"rc": 2, "stdout": APPLIED})
    report(lab, DEBUG_NOTIFY + "\n")
    lab.world["ssh"].insert(0, {"match": r"python3 - puppet_infrastructure::nginx_frontend_domain$", "stdout":
                                "COVERAGE puppet_infrastructure::nginx_frontend_domain: 9 concrete resources (+3 defined-type instances)\n"})
    proc = lab.run([SCRIPT, "puppet_infrastructure::nginx_frontend_domain"], env={"HOME": str(lab.root / "home")})
    assert proc.returncode == 0, proc.stderr
    assert "RUN2_EXPECTED_EVENTS: 1 from Notify[Generated Upstream members for *]" in proc.stdout
    assert "GREEN: run 2 events limited to the plan's expected_run2_events" in proc.stdout
    import json
    h = [json.loads(l) for l in (lab.root / "metrics" / "events.jsonl").read_text().splitlines()
         if json.loads(l)["kind"] == "harness"][-1]["data"]
    assert h["run2_expected"]["own"] == ["Notify[Generated Upstream members for *]"]  # a ref with spaces, whole


def test_an_event_on_console_and_in_the_report_counts_once(lab):
    agent_runs(lab, {"rc": 2, "stdout": APPLIED}, {"rc": 2, "stdout": APT_EVENT + APPLIED})
    report(lab, "Exec[apt_update]\n")
    lab.world["ssh"].insert(0, PKG_COVERAGE)
    proc = lab.run([SCRIPT, "puppet_infrastructure::packages_base"])
    assert proc.returncode == 0, proc.stderr
    assert "RUN2_EXPECTED_EVENTS: 1 from Exec[apt_update]" in proc.stdout
