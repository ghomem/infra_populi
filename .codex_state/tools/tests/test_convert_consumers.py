"""Consumer conversion for the module rename, on synthetic fixtures only (HQ rulings on round 9 "E. Phase 2 rename";
HQ review of the behaviour suite, ruling 8): no real consumer repository, Hiera or Hashman data is ever read here."""
import subprocess
import sys

from conftest import TOOLS

TOOL = str(TOOLS / "convert_consumers.py")


def run(*args):
    return subprocess.run([sys.executable, TOOL, *args], capture_output=True, text=True)


def fixtures(root):
    """A synthetic site: node definitions, Hiera with automatic parameter keys and a localdir, a Hashman-generated
    declaration file, an operator params directory named with the module prefix, and a file it must not touch."""
    (root / "nodes").mkdir(parents=True)
    (root / "nodes" / "p8test-web.pp").write_text(
        "node 'p8test-web.example.invalid' {\n  include puppet_infrastructure::node_base\n"
        "  class { 'puppet_infrastructure::nginx_frontend': domain => 'p8test.example.invalid' }\n"
        "  include meaningful_puppet::meaningful_desktop\n"
        "  Class['Puppet_infrastructure::ssl_base'] -> Service['nginx']\n}\n")
    (root / "data").mkdir()
    (root / "data" / "common.yaml").write_text(
        "filesystem::localdir: /opt/puppet-infrastructure\n"
        "puppet_infrastructure::openvpn_server::local: '203.0.113.50'\nclasses:\n  - puppet_infrastructure::sync\n")
    (root / "hashman").mkdir()
    (root / "hashman" / "users.pp").write_text("  puppet_infrastructure::user        { 'p8testuser': uid => 2001 }\n")
    (root / "params" / "for" / "puppet_infrastructure::nginx_frontend").mkdir(parents=True)
    (root / "params" / "puppet_infrastructure::ssh_secure.json").write_text('{"port": 22}\n')
    (root / "params" / "for" / "puppet_infrastructure::nginx_frontend" / "puppet_infrastructure::ssl_base.json") \
        .write_text("{}\n")
    (root / "README").write_text("a site for p8test\n")


def test_check_lists_every_leftover_before_the_conversion(tmp_path):
    fixtures(tmp_path)
    p = run("check", str(tmp_path))
    assert p.returncode == 1 and "CONVERSION CHECK FAIL" in p.stdout
    assert "nodes/p8test-web.pp:2: names the old module" in p.stdout
    assert "params/puppet_infrastructure::ssh_secure.json: named with the old name" in p.stdout


def test_convert_renames_every_form_and_every_name_and_leaves_the_rest(tmp_path):
    fixtures(tmp_path)
    p = run("convert", str(tmp_path), "--to", "infra_populi")
    assert p.returncode == 0, p.stdout + p.stderr
    node = (tmp_path / "nodes" / "p8test-web.pp").read_text()
    assert "include infra_populi::node_base" in node and "class { 'infra_populi::nginx_frontend'" in node
    assert "Class['Infra_populi::ssl_base']" in node and "include meaningful_puppet::meaningful_desktop" in node
    assert (tmp_path / "data" / "common.yaml").read_text() == (
        "filesystem::localdir: /opt/infra-populi\ninfra_populi::openvpn_server::local: '203.0.113.50'\n"
        "classes:\n  - infra_populi::sync\n")
    assert "infra_populi::user        { 'p8testuser'" in (tmp_path / "hashman" / "users.pp").read_text()
    assert (tmp_path / "params" / "infra_populi::ssh_secure.json").read_text() == '{"port": 22}\n'
    assert (tmp_path / "params" / "for" / "infra_populi::nginx_frontend" / "infra_populi::ssl_base.json").is_file()
    assert (tmp_path / "README").read_text() == "a site for p8test\n"
    assert run("check", str(tmp_path)).returncode == 0
    again = run("convert", str(tmp_path), "--to", "infra_populi")  # idempotent
    assert "changed 0 file(s)" in again.stdout


def test_dry_run_changes_nothing(tmp_path):
    fixtures(tmp_path)
    before = sorted(str(p) for p in tmp_path.rglob("*"))
    p = run("convert", str(tmp_path), "--to", "infra_populi", "--dry-run")
    assert "rename params/puppet_infrastructure::ssh_secure.json" in p.stdout and "would change" in p.stdout
    assert sorted(str(p) for p in tmp_path.rglob("*")) == before
    assert run("check", str(tmp_path)).returncode == 1


def test_a_conversion_to_the_old_name_is_refused(tmp_path):
    fixtures(tmp_path)
    p = run("convert", str(tmp_path), "--to", "puppet_infrastructure")
    assert p.returncode == 2 and "REFUSED" in p.stdout


def test_a_target_name_that_exists_is_refused(tmp_path):
    fixtures(tmp_path)
    (tmp_path / "params" / "infra_populi::ssh_secure.json").write_text("{}\n")
    node = (tmp_path / "nodes" / "p8test-web.pp").read_text()
    p = run("convert", str(tmp_path), "--to", "infra_populi")
    assert p.returncode != 0 and "exists; nothing converted" in (p.stdout + p.stderr)
    assert (tmp_path / "nodes" / "p8test-web.pp").read_text() == node  # nothing half-converted
