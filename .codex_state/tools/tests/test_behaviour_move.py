"""The move of the check sets into spec/behaviour (HQ review of design note F, ruling 6): provably neutral."""
import sys
from pathlib import Path

import pytest
import yaml

TOOLS = Path(__file__).resolve().parents[1]
REPO = TOOLS.parents[1]
sys.path.insert(0, str(TOOLS))
sys.path.insert(1, str(TOOLS.parent))
sys.path.insert(2, str(REPO / "spec" / "behaviour" / "lib"))
import behaviour_move as bm  # noqa: E402

BASE = {**bm.LAB, "NODE_NAME": "puppet8node", "NODE_ADDR": "192.168.56.20", "PEER_NAME": "p8lab-ubuntu2",
        "PEER_ADDR": "192.168.56.24", "NODE:rhel9": "p8lab-rhel9", "NODE:ubuntu": "puppet8node",
        **{f"SITE:{slug}": lit for lit, slug in bm.SITE.items()}}
RHEL = {**BASE, "NODE_NAME": "p8lab-rhel9", "NODE_ADDR": "192.168.56.21"}
OLD = {
    "class": "p8x", "purpose": "x" * 40,
    "outcomes": [{"outcome": "the thing happens on the node", "from": "manifests/p8x.pp:1",
                  "uncovered": {"why": "y" * 20, "lifted_by": "capability: z" * 2,
                                "evidence": "diagnosis/fleet_variant_usage.md: measured on puppet8node"}}],
    "variants": [{"name": "rhel", "why": "w" * 20, "node": "rhel9"}],
    "checks": [
        {"id": "a", "host": "peer", "probe": "nc -z 192.168.56.20 22; ls /opt/puppet-infrastructure/bin",
         "expect": {"stdout": "\\Apuppet8master\\.example\\.com\\n"}},
        {"id": "b", "probe": 'echo "$P8_PEER_ADDR x" >> /etc/hosts; w=${P8_PEER_ADDR%.*}', "mutates": "pins x to $P8_PEER_ADDR",
         "effect": "hostname", "expect": {"stdout": "^puppet8node$"}},
        {"id": "c", "variant": "rhel", "probe": "hostname", "expect": {"stdout": "^p8lab-rhel9$"}},
    ],
}
CTXS = {"base": BASE, "rhel": RHEL}


def test_lab_values_become_placeholders_by_role_in_executed_strings_and_by_kind_in_prose():
    new = bm.to_template(OLD, CTXS)
    a, b, c = new["checks"]
    assert a["probe"] == "nc -z {{NODE_ADDR}} 22; ls {{LOCALDIR}}/bin"
    assert a["expect"]["stdout"] == "\\A{{SERVER_NAME|re}}\\n"
    assert b["probe"] == 'echo "$PEER_ADDR x" >> /etc/hosts; w=${PEER_ADDR%.*}'
    assert b["mutates"] == "pins x to $PEER_ADDR"
    assert b["expect"]["stdout"] == "^{{NODE_NAME}}$"
    assert c["expect"]["stdout"] == "^{{NODE_NAME}}$"  # the variant's own node
    assert new["outcomes"][0]["uncovered"]["evidence"] == "{{SITE:fleet-usage}}: measured on {{NODE:ubuntu}}"


def test_the_template_rendered_with_the_lab_values_is_the_old_set_byte_for_byte():
    assert bm.first_difference(OLD, bm.to_lab(bm.to_template(OLD, CTXS), CTXS)) is None


def test_a_changed_probe_is_not_neutral():
    new = bm.to_template(OLD, CTXS)
    new["checks"][0]["probe"] += " "
    assert "checks[0].probe" in bm.first_difference(OLD, bm.to_lab(new, CTXS))


def test_an_address_beside_the_peer_is_an_offset_of_the_peer():
    assert bm.templatise('["192.168.56.1", "192.168.56.124"]', BASE, "acl") == \
        '["{{CONTROLLER_ADDR}}", "{{PEER_ADDR+100}}"]'


def test_a_name_inside_a_longer_name_is_left_alone():
    assert bm.templatise("puppet8node2 xpuppet8node", BASE, "probe") == "puppet8node2 xpuppet8node"


def test_the_dumped_yaml_reads_back_as_the_set():
    new = bm.to_template(OLD, CTXS)
    assert yaml.safe_load(bm.dump(new)) == new


class Row:
    def __init__(self, **kw):
        self.__dict__.update(kw)


def test_the_catalog_follows_the_harness_bases_first_then_externals_and_apt_only_on_debian():
    rows = {"x": Row(required_base=["b", "[RedHat]r", "[Debian]d"], required_external=["apt", "firewall"]),
            "b": Row(required_base=[], required_external=["stdlib"]), "r": Row(required_base=[]),
            "d": Row(required_base=[])}
    assert bm.expand("x", rows, "Debian") == [{"external": "stdlib"}, {"class": "b"}, {"class": "d"},
                                               {"external": "apt"}, {"external": "firewall"}, {"class": "x"}]
    assert bm.expand("x", rows, "RedHat") == [{"external": "stdlib"}, {"class": "b"}, {"class": "r"},
                                               {"external": "firewall"}, {"class": "x"}]


def test_an_escaped_address_in_a_probe_becomes_a_placeholder_too():
    probe = "grep -c 'unknown\\[192\\.168\\.56\\.20\\]' x"
    assert bm.templatise(probe, BASE, "probe") == "grep -c 'unknown\\[{{NODE_ADDR|re}}\\]' x"
    assert bm.lab_left({"probe": probe}, CTXS) == {"192.168.56.20"}


def test_lab_view_leaves_a_set_without_placeholders_as_it_is():
    plain = {"class": "p8x", "checks": [{"id": "a", "probe": "true"}]}
    assert bm.lab_view("p8x", plain) is plain


def test_every_moved_set_is_still_the_neutral_move_of_its_old_file():
    moved = __import__("json").loads(bm.MOVED.read_text())
    bad = {cls: diff for cls in moved if (diff := bm.verify(cls, moved))
           and diff != "the set changed after the move (its reviews judge it as any changed set)"}
    assert not bad, dict(list(bad.items())[:3])
