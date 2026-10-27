"""The Codex wrapper carries an outer timeout and closes stdin (steps 1.1, 2026-10-01 rule)."""

from conftest import TOOLS

WRAPPER = str(TOOLS / "codex_migrate_class")


def stub_codex(lab, body):
    path = lab.bin / "codex"
    path.write_text("#!/usr/bin/env bash\n" + body + "\n")
    path.chmod(0o755)


def test_hung_codex_is_killed(lab):
    stub_codex(lab, "exec python3 -c 'import time; time.sleep(30)'")
    proc = lab.run([WRAPPER, "puppet_infrastructure::dns_client"], env={"CODEX_TIMEOUT_SECONDS": "1"})
    assert proc.returncode == 124
    assert "CODEX_TIMEOUT: codex exec killed after 1s" in proc.stderr


def test_codex_exit_code_is_propagated_and_stdin_closed(lab):
    stub_codex(lab, '[[ "$(cat)" == "" ]] || exit 9; exit 3')
    proc = lab.run([WRAPPER, "puppet_infrastructure::dns_client"])
    assert proc.returncode == 3


def test_prompt_names_the_pinned_baseline(lab):
    out = lab.root / "prompt.txt"
    stub_codex(lab, f'printf "%s" "${{@: -1}}" > {out}')
    assert lab.run([WRAPPER, "puppet_infrastructure::dns_client"]).returncode == 0
    prompt = out.read_text()
    assert "release-0.9.10 (cf477c6)" in prompt and "release-0.9.8" not in prompt


def test_wrapper_reverts_before_codex(lab):
    marker = lab.root / "codex_ran"
    stub_codex(lab, f"touch {marker}")
    proc = lab.run([WRAPPER, "puppet_infrastructure::dns_client"])
    assert proc.returncode == 0, proc.stderr
    assert ["VBoxManage", "snapshot", "ubuntu24-puppet8-Node", "restore", "P8NODE_BASELINE_GREEN_v2"] in lab.calls()
    assert marker.exists()


def test_wrapper_does_not_start_codex_when_revert_fails(lab):
    marker = lab.root / "codex_ran"
    stub_codex(lab, f"touch {marker}")
    lab.world["vms"]["ubuntu24-puppet8-Node"]["state"] = "restoring"
    proc = lab.run([WRAPPER, "puppet_infrastructure::dns_client"])
    assert proc.returncode == 3 and "REVERT_FAILED" in proc.stderr
    assert not marker.exists()


def test_prompt_carries_the_orientation_packet_and_the_record_recipe(lab):
    out = lab.root / "prompt.txt"
    stub_codex(lab, f'printf "%s" "${{@: -1}}" > {out}')
    assert lab.run([WRAPPER, "puppet_infrastructure::sysmon_fs_health"]).returncode == 0
    prompt = out.read_text()
    assert "ORIENTATION PACKET puppet_infrastructure::sysmon_fs_health" in prompt
    assert "plan: resource_type=define title=sysmon_fs_health" in prompt
    assert "record_green.sh puppet_infrastructure::sysmon_fs_health" in prompt
    assert "supersedes runbook section 2 steps 5-7" in prompt
