"""fleet_variants.py (HQ 2026-11-23 ruling 1c): parameter names and counts from the fleet, never a value."""

import importlib
import sys

import pytest

from conftest import TOOLS

sys.path.insert(0, str(TOOLS))

SECRET = "p8test-value-never-recorded"


@pytest.fixture
def fleet(tmp_path, monkeypatch):
    nodes, company = tmp_path / "nodes", tmp_path / "company"
    for d in ("services", "operations", "desktops", "deleted", "tests", "passwd"):
        (nodes / d).mkdir(parents=True)
    (company / "manifests").mkdir(parents=True)
    (nodes / "common.pp").write_text(f"$x = '{SECRET}'\n")
    (nodes / "services" / "a.pp").write_text(
        "node 'a' {\n"
        "  # class { 'infra_populi::firewall_secure': strict => true }  (a comment)\n"
        f"  class {{ 'infra_populi::firewall_secure': strict => true, extra => {{ k => '{SECRET}' }}, }}\n"
        "  include meaningful_puppet::web\n"
        "}\n")
    (nodes / "operations" / "b.pp").write_text(
        f"node 'b' {{\n  class {{ '::infra_populi::firewall_secure': strict => false, ports => ['{SECRET}'] }}\n}}\n")
    (nodes / "desktops" / "d.pp").write_text("node /^lap/ {\n  include meaningful_puppet::web\n}\n")
    (nodes / "deleted" / "old.pp").write_text("node 'old' { class { 'infra_populi::firewall_secure': strict => true } }\n")
    (nodes / "tests" / "t.pp").write_text("node 't' { class { 'infra_populi::firewall_secure': strict => true } }\n")
    (nodes / "passwd" / "p.pp").write_text(
        "class passwd_x { infra_populi::user_base { 'u': shell => '/bin/zsh' } }\n")
    (company / "manifests" / "web.pp").write_text(
        f"class meaningful_puppet::web {{\n  infra_populi::nginx_frontend {{ 'w': domain => '{SECRET}' }}\n}}\n")
    monkeypatch.setenv("P8_FLEET_DIR", str(nodes))
    monkeypatch.setenv("P8_COMPANY_DIR", str(company))
    import fleet_variants
    return importlib.reload(fleet_variants)


def test_counts_production_statements_directly_and_through_a_company_class(fleet):
    assert fleet.count("firewall_secure", "strict") == "2"  # a and b; deleted/ and tests/ do not count
    assert fleet.count("firewall_secure", "extra") == "1"
    assert fleet.count("firewall_secure", "ignore_patterns") == "0"
    assert fleet.count("nginx_frontend", "domain") == "2"  # a and the desktops statement, through meaningful_puppet::web


def test_nested_hash_keys_are_not_parameters(fleet):
    assert fleet.count("firewall_secure", "k") == "0"


def test_the_passwd_layer_is_never_read_and_its_classes_are_undeterminable(fleet):
    assert fleet.count("user_base", "shell") == "undeterminable"
    assert "user_base" not in fleet.usage()


def test_the_table_records_names_and_counts_never_a_value(fleet):
    text = fleet.render()
    assert "| firewall_secure | strict | 2 |" in text
    assert SECRET not in text and "true" not in text.split("| class |")[1]


def test_a_composite_forwards_the_parameter_to_its_component(fleet, monkeypatch, tmp_path):
    repo = tmp_path / "repo"
    (repo / "manifests").mkdir(parents=True)
    (repo / "manifests" / "node_base.pp").write_text(
        "class infra_populi::node_base ($fw_strict = false) {\n"
        "  class { 'infra_populi::firewall_secure': strict => $fw_strict }\n}\n")
    (fleet.fleet_dir() / "services" / "c.pp").write_text(
        "node 'c' { class { 'infra_populi::node_base': fw_strict => true } }\n")
    monkeypatch.setattr(fleet, "REPO", repo)
    assert fleet.count("firewall_secure", "strict") == "3"
    assert fleet.count("node_base", "fw_strict") == "1"
