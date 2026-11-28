import copy
import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
from behaviour import setfile  # noqa: E402

GOOD = {
    "class": "p8x",
    "fixture": "defaults",
    "purpose": "Keeps the p8x service running and answering on its port, for the tests.",
    "outcomes": [{"outcome": "the service answers on its port", "from": "manifests/p8x.pp:3", "checks": ["answers"]},
                 {"outcome": "the other machine reaches it too", "from": "manifests/p8x.pp:4",
                  "uncovered": {"why": "no second machine in this sketch", "lifted_by": "ubuntu2", "evidence": "x" * 20}}],
    "checks": [{"id": "answers", "what": "it answers", "control": "negative", "probe": "p8_tcp 127.0.0.1 80",
                "expect": {"stdout": "^open$"}, "derived_from": [{"path": "anything", "lines": "999"}]}],
    "apply": {"resource_type": "class", "node": "ubuntu", "catalog": {"Debian": [{"external": "apt"}, {"class": "p8x"}]}},
}


def write(tmp_path, data) -> Path:
    path = tmp_path / f"{data.get('class', 'p8x')}.yml"
    path.write_text(yaml.safe_dump(data, sort_keys=False))
    return path


def test_a_complete_set_is_valid_and_derived_from_is_provenance_only(tmp_path):
    assert setfile.validate(write(tmp_path, GOOD)) == []


def change(**edits):
    data = copy.deepcopy(GOOD)
    for path, value in edits.items():
        target = data
        *keys, last = path.split("__")
        for k in keys:
            target = target[int(k)] if k.isdigit() else target[k]
        if value is None:
            del target[last]
        else:
            target[last] = value
    return data


@pytest.mark.parametrize("edits, problem", [
    ({"purpose": "short"}, "purpose"),
    ({"outcomes": None}, "outcomes"),
    ({"outcomes__0__checks": ["missing"]}, "no check 'missing'"),
    ({"outcomes__1__uncovered": {"why": "x" * 20, "lifted_by": "mars"}}, "lifted_by"),
    ({"checks__0__probe": "ping {{SITE:fleet-usage}}"}, "not a value a run supplies"),
    ({"checks__0__probe": "ping {{NOWHERE}}"}, "unknown"),
    ({"checks__0__probe": "puppet agent -t"}, "runs Puppet"),
    ({"checks__0__control": "invariant"}, "why_invariant"),
    ({"checks__0__probe": "curl -s --resolve a:443:127.0.0.1 https://a/"}, "mismatch` control is mandatory"),
    ({"checks__0__expect": {"stdout": "("}}, "not a regex"),
    ({"apply__catalog": {"Debian": [{"class": "other"}]}}, "ending with the class"),
    ({"apply__node": "mars"}, "not a kind"),
    ({"peer": {"kind": "ubuntu", "why": "x" * 20}}, "second-node"),
    ({"variants": [{"name": "rh", "why": "x" * 20, "node": "rhel9"}]}, "negative control of its own"),
])
def test_each_rule_names_its_problem(tmp_path, edits, problem):
    found = setfile.validate(write(tmp_path, change(**edits)))
    assert any(problem in p for p in found), found


def test_a_placeholder_in_an_expectation_compiles_as_a_regex(tmp_path):
    data = change(checks__0__expect={"stdout": r"^{{NODE_NAME|re}} {{NODE_ADDR|re}}$"})
    assert setfile.validate(write(tmp_path, data)) == []


def test_site_records_may_be_cited_in_prose(tmp_path):
    data = change(**{"outcomes__1__uncovered": {"why": "measured in {{SITE:fleet-usage}} long ago",
                                                "lifted_by": "capability: a registry the lab runs"}})
    assert setfile.validate(write(tmp_path, data)) == []


def test_a_missing_params_fixture_is_reported_when_the_caller_asks(tmp_path):
    data = change(fixture="params")
    assert any("no params fixture" in p for p in setfile.validate(write(tmp_path, data), params_found=lambda v: False))
    assert setfile.validate(write(tmp_path, data)) == []


def test_every_set_of_the_suite_is_valid():
    checks = setfile.SUITE / "checks"
    sets = sorted(checks.glob("*.yml")) if checks.is_dir() else []
    bad = {p.stem: found for p in sets if (found := setfile.validate(p))}
    assert not bad, dict(list(bad.items())[:3])


def test_a_set_that_needs_a_server_says_what_for(tmp_path):
    data = copy.deepcopy(GOOD)
    data["apply"]["requires"] = ["server"]
    assert any("requires_why" in p for p in setfile.validate(write(tmp_path, data)))
    data["apply"]["requires_why"] = "its files come from the server's file mount puppet:///extra_files"
    assert setfile.validate(write(tmp_path, data)) == []


def with_peer_variant(**peer):
    data = copy.deepcopy(GOOD)
    data["variants"] = [{"name": "reg", "params": "reg", "why": "a registry the class logs in to, served by the peer"}]
    data["checks"].append({"id": "from-the-peer", "what": "the peer pulls", "control": "negative", "host": "peer",
                           "variant": "reg", "probe": "true", "expect": {"stdout": "^x$"},
                           "derived_from": [{"path": "anything", "lines": "1"}]})
    data["peer"] = {"kind": "ubuntu2", "why": "a second machine serves what the class uses", **peer}
    return data


def test_a_peer_may_serve_a_variant_and_be_prepared_before_the_clean_phase(tmp_path):
    # HQ 2026-11-27 item 2: peer.runs names the runs that get a fresh peer, peer.setup prepares it
    ok = with_peer_variant(runs=["reg"], setup="systemctl restart docker-registry\n")
    assert setfile.validate(write(tmp_path, ok), params_found=lambda v: True) == []
    assert setfile.peer_runs(ok) == ["reg"] and setfile.peer_runs(GOOD) == []
    assert setfile.peer_runs({**GOOD, "peer": {"kind": "ubuntu2", "why": "x" * 20}}) == ["base"]
    for bad, message in [({"runs": ["nope"]}, "peer.runs lists the runs"), ({"setup": ""}, "peer.setup is a script"),
                         ({}, "variant reg has no peer")]:
        found = setfile.validate(write(tmp_path, with_peer_variant(**bad)), params_found=lambda v: True)
        assert any(message in p for p in found), found


@pytest.mark.parametrize("lifted, refused", [
    ("capability: a second node kind for the RedHat branch", True),
    ("capability: an agent run on the peer after the change", True),
    ("capability: an ecryptfs fixture user with a mounted private directory", False),
])
def test_a_row_naming_a_capability_the_runner_has_is_refused(lifted, refused):
    # HQ 2026-11-27 item 1: such a row is a check to write; the list of capabilities is setfile.RUNNER_CAPABILITIES
    problems = setfile.uncovered_problems({"why": "the fixture cannot show this outcome yet", "lifted_by": lifted},
                                          "o", {})
    assert bool(problems and "the runner has" in problems[0]) is refused, problems


def test_a_variant_names_an_existing_node_fixture(tmp_path):
    data = copy.deepcopy(GOOD)
    data["variants"] = [{"name": "enc", "why": "an encrypted home", "node_fixture": "p8test_no_such_fixture"}]
    problems = setfile.variant_problems(data, data["checks"], setfile.kinds(), None)
    assert any("node_fixture 'p8test_no_such_fixture' is not a file" in p for p in problems), problems
    data["variants"][0]["node_fixture"] = "p8test_ecryptfs_home"
    assert not any("node_fixture" in p for p in setfile.variant_problems(data, data["checks"], setfile.kinds(), None))
