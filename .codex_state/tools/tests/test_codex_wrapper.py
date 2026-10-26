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
