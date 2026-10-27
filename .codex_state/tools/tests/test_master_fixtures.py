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


def remotes():
    text = (TOOLS / "master_fixtures.sh").read_text()
    return [part.split("REMOTE\n", 1)[0] for part in text.split("<<'REMOTE'")[1:]]


def test_all_runs_every_section_in_order(lab):
    for name in ("hiera", "pki", "extra_files", "lint"):
        lab.world["ssh"].insert(0, {"match": rf"OK {name}\b|{name}", "stdout": f"OK {name}: stub\n"})
    proc = lab.run([SCRIPT, "all"])
    assert proc.returncode == 0, proc.stderr
    assert len(lab.calls("ssh")) == 4
    assert lab.calls("VBoxManage") == []  # never acts on the master VM


def test_every_section_has_an_ok_branch_and_changed_report():
    for name, body in zip(("lint", "extra_files", "pki", "hiera"), remotes()):
        assert f"OK {name}" in body and f"CHANGED {name}" in body, name


def test_fixture_values_are_obviously_fake():
    hiera = remotes()[3]
    values = [l.split(": ", 1)[1] for l in hiera.split("<<'YAML'", 1)[1].split("YAML\n", 1)[0].splitlines()
              if "::" in l and not l.startswith("#")]
    assert len(values) == 6
    assert all("p8test" in v or "lookup(" in v or v.strip().strip("'").isdigit() for v in values), values
    pki = remotes()[2]
    assert "THROWAWAY" in pki and "CN=p8test throwaway CA" in pki and "CN=p8test.invalid" in pki
    assert "ca.key" not in pki.split("put()")[1]  # the CA key is never installed
    assert "-days 3650" in pki


def test_hiera_level_goes_after_common_and_never_overrides():
    hiera = remotes()[3]
    assert 'h["hierarchy"] <<' in hiera  # appended: lowest priority
    assert "unshift" not in hiera and "insert(0" not in hiera


def test_mount_with_another_path_is_left_alone():
    body = remotes()[1]
    assert "has an [extra_files] mount with another path; not touching it" in body
