"""test_class.sh takes its node from the lab inventory (HQ 2026-11-16 item 2): alias, master node file, certname,
facts variant and per-node params follow the selected node."""

import pytest
import yaml

from conftest import PLANNED_KIND, TOOLS, planned_inventory

pytestmark = pytest.mark.slow

SCRIPT = str(TOOLS / "test_class.sh")


@pytest.fixture
def rhel(tmp_path, lab):
    data = yaml.safe_load((TOOLS.parent / "lab" / "nodes.yml").read_text())
    data["nodes"]["rhel9"].update(status="active", baseline_snapshot="P8LAB_RHEL9_BASELINE_v1")
    path = tmp_path / "nodes.yml"
    path.write_text(yaml.safe_dump(data))
    return {"P8_NODES": str(path)}


def ssh_lines(lab):
    return [" ".join(c[1:]) for c in lab.calls("ssh")]


def test_compile_only_on_a_redhat_node_uses_its_alias_node_file_and_native_facts(lab, rhel):
    proc = lab.run([SCRIPT, "--node", "rhel9", "--compile-only", "puppet_infrastructure::dns_client"], env=rhel)
    out = proc.stdout + proc.stderr
    assert "==> Lab node: rhel9 (p8lab-rhel9, certname p8lab-rhel9, RedHat)" in out
    assert "facts: native" in out
    lines = ssh_lines(lab)
    assert any("p8lab-rhel9 sudo -n /opt/puppetlabs/bin/puppet facts show" in l for l in lines)
    assert any("manifests/nodes/p8lab-rhel9.pp" in l for l in lines)  # the CODEX block goes into the node's own file
    assert not any("nodes/puppet8node.pp" in l for l in lines)
    assert not any("puppet8node" in c for c in lab.calls("ssh"))  # no call targets the Ubuntu node


def test_debian_facts_cannot_be_forced_onto_a_redhat_node(lab, rhel):
    proc = lab.run([SCRIPT, "--node", "rhel9", "--compile-only", "--facts", "debian", "puppet_infrastructure::dns_client"],
                   env=rhel)
    assert proc.returncode == 1 and "cannot rewrite a RedHat node's facts" in proc.stderr


def test_the_default_node_is_unchanged(lab):
    proc = lab.run([SCRIPT, "--compile-only", "puppet_infrastructure::dns_client"])
    assert "==> Lab node: ubuntu (puppet8node, certname puppet8node, Debian)" in proc.stdout
    assert "facts: debian" in proc.stdout


def test_a_planned_node_is_refused_before_anything_runs(lab, tmp_path):
    proc = lab.run([SCRIPT, "--node", PLANNED_KIND, "--revert-first", "puppet_infrastructure::dns_client"],
                   env={"P8_NODES": planned_inventory(tmp_path)})
    assert proc.returncode == 1 and f"No usable lab node '{PLANNED_KIND}'" in proc.stderr
    assert lab.calls("VBoxManage") == [] and lab.calls("rsync") == []


def test_a_node_kind_params_file_wins_over_the_shared_one(lab, rhel, tmp_path):
    home = tmp_path / "home"
    shared = home / ".config" / "infra_populi" / "params"
    (shared / "rhel9").mkdir(parents=True)
    cls = "puppet_infrastructure::backup_rsnapshot"
    (shared / f"{cls}.json").write_text('{"basedir": "/etc", "prefix": "shared", "backdir": "/b", "ndays": 1}\n')
    (shared / "rhel9" / f"{cls}.json").write_text('{"basedir": "/etc", "prefix": "rhelonly", "backdir": "/b", "ndays": 1}\n')
    base = {"HOME": str(home), **rhel}
    out = lab.run([SCRIPT, "--node", "rhel9", "--render-only", cls], env=base).stdout
    assert "rhelonly" in out and "shared" not in out
    out = lab.run([SCRIPT, "--render-only", cls], env={"HOME": str(home)}).stdout
    assert "shared" in out and "rhelonly" not in out



def test_a_per_target_fixture_configures_a_base_class_only_for_that_target(lab, tmp_path):
    # nginx_frontend_mail (2026-11-17): production enables nginx's mail module through nginx_base's my_configs on mail
    # frontends; params/for/<target>/<base>.json applies that only when the base is applied for that target
    home = tmp_path / "home"
    shared = home / ".config" / "infra_populi" / "params"
    target, base = "puppet_infrastructure::user_desktop", "puppet_infrastructure::filesystem_base"
    (shared / "for" / target).mkdir(parents=True)
    (shared / f"{target}.json").write_text('{"myname": "P8 Test User"}\n')
    (shared / "for" / target / f"{base}.json").write_text('{"p8test_marker": "for-target"}\n')
    for given in (target, target.removeprefix("puppet_infrastructure::")):  # full or short name on the command line
        out = lab.run([SCRIPT, "--render-only", given], env={"HOME": str(home)}).stdout
        assert "for-target" in out and base in out, given
    out = lab.run([SCRIPT, "--render-only", base], env={"HOME": str(home)}).stdout
    assert "for-target" not in out  # the base applied on its own keeps its shared (here: no) fixture


# 2026-11-18, the rhel9 pass: nginx_base's required_external `apt` (for its Ubuntu-only Exec['apt_update']) failed
# every RedHat compile ("This module only works on Debian"); a Debian-only external is not declared on RedHat.
def test_a_debian_only_external_is_not_declared_on_a_redhat_target(lab, rhel):
    proc = lab.run([SCRIPT, "--node", "rhel9", "--render-only", "puppet_infrastructure::nginx_base"], env=rhel)
    out = proc.stdout + proc.stderr
    assert "required_external apt not declared: Debian-only, the target is RedHat" in out
    assert "include apt" not in proc.stdout and "class { 'apt'" not in proc.stdout


def test_a_debian_only_external_is_still_declared_on_ubuntu(lab):
    proc = lab.run([SCRIPT, "--render-only", "puppet_infrastructure::nginx_base"])
    assert "not declared: Debian-only" not in proc.stdout + proc.stderr
    assert "apt" in proc.stdout


# HQ 2026-11-18 ruling A2: a required_base entry qualified [Debian] is applied on Ubuntu only.
def test_a_debian_qualified_base_is_not_applied_on_a_redhat_target(lab, rhel):
    proc = lab.run([SCRIPT, "--node", "rhel9", "--render-only", "puppet_infrastructure::sysmon_base"], env=rhel)
    assert proc.returncode == 0, proc.stderr
    assert "puppet_infrastructure::packages_base" in proc.stdout
    assert "puppet_infrastructure::filesystem_lib64" not in proc.stdout


def test_a_debian_qualified_base_is_applied_on_ubuntu(lab):
    proc = lab.run([SCRIPT, "--render-only", "puppet_infrastructure::sysmon_base"])
    assert proc.returncode == 0, proc.stderr
    assert "puppet_infrastructure::filesystem_lib64" in proc.stdout


def test_a_phase3_params_variant_wins_and_a_missing_one_stops_the_harness(lab, tmp_path):
    """HQ 2026-11-23 ruling 1a: a Phase 3 variant run's own params fixture (P8_PARAMS_VARIANT), never a silent default."""
    home = tmp_path / "home"
    shared = home / ".config" / "infra_populi" / "params"
    (shared / "variants" / "strict").mkdir(parents=True)
    cls = "puppet_infrastructure::backup_rsnapshot"
    (shared / f"{cls}.json").write_text('{"basedir": "/etc", "prefix": "shared", "backdir": "/b", "ndays": 1}\n')
    (shared / "variants" / "strict" / f"{cls}.json").write_text(
        '{"basedir": "/etc", "prefix": "variantonly", "backdir": "/b", "ndays": 1}\n')
    out = lab.run([SCRIPT, "--render-only", cls], env={"HOME": str(home), "P8_PARAMS_VARIANT": "strict"}).stdout
    assert "variantonly" in out and "shared" not in out
    proc = lab.run([SCRIPT, "--render-only", cls], env={"HOME": str(home), "P8_PARAMS_VARIANT": "absent"})
    assert proc.returncode != 0 and "params variant absent" in proc.stderr
