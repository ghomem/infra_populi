"""master_fixtures.sh: pinned, idempotent, never acts on the master VM itself."""

from conftest import TOOLS

SCRIPT = str(TOOLS / "master_fixtures.sh")


def test_lint_section_pins_the_version_and_uses_the_agent_gem(lab):
    lab.world["ssh"].insert(0, {"match": r"puppet8master sudo -n bash -s", "stdout": "OK lint: puppet-lint 4.3.0\n"})
    proc = lab.run([SCRIPT, "lint"])
    assert proc.returncode == 0, proc.stderr
    (call,) = lab.calls("ssh")
    assert "/opt/puppetlabs/puppet/bin/gem" in " ".join(call) and "'4.3.0'" in " ".join(call)
    assert lab.calls("VBoxManage") == []


def test_remote_script_is_idempotent_by_construction():
    text = (TOOLS / "master_fixtures.sh").read_text()
    remote = text.split("<<'REMOTE'", 1)[1].split("REMOTE\n", 1)[0]
    assert remote.index("gem\" list --exact puppet-lint") < remote.index("gem\" install puppet-lint")
    assert "--version \"$version\"" in remote and "OK lint" in remote


def test_unknown_section_is_rejected(lab):
    assert lab.run([SCRIPT, "pki-now"]).returncode == 2
