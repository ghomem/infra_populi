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


def test_pki_v2_names_the_harness_fixture_domain_and_replaces_v1():
    """HQ 2026-11-10: the fixture certificate carries the fixture domain (p8test.example.com) so TLS names verify."""
    pki = remotes()[2]
    san = next(l for l in pki.splitlines() if "subjectAltName=" in l)
    assert "DNS:p8test.example.com" in san and "DNS:*.p8test.example.com" in san
    assert "DNS:p8test.invalid" in san and "DNS:star.example.com" in san  # earlier names kept
    assert 'marker="$1/.p8test_pki_v2"' in pki  # a v1 layout is not OK any more: it is regenerated
    assert pki.index('rm -f "$dir/.p8test_pki_v1"') > pki.index('>"$marker"')  # v1 marker dropped only after v2 exists


def test_every_remote_script_parses():
    """shellcheck never sees the REMOTE heredocs; a syntax error there surfaces only on the master (pki v2, 2026-11-10:
    a stray quote on the last line made a successful run exit 2)."""
    import subprocess
    for body in remotes():
        proc = subprocess.run(["bash", "-n"], input=body, capture_output=True, text=True)
        assert proc.returncode == 0, proc.stderr
