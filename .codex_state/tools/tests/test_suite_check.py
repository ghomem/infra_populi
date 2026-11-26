"""The public suite stays free of the lab and the engine (HQ review of design note F, rulings 2 and 8)."""
import json
import sys
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))
sys.path.insert(1, str(TOOLS.parent))
import suite_check as sc  # noqa: E402

LAB = sc.lab_values()
FILES = sc.engine_files()


@pytest.mark.parametrize("text, problem", [
    ("probe: ping puppet8node", "lab value (puppet8node)"),
    ("expect: \\Apuppet8master\\.example\\.com", "lab value (puppet8master.example.com)"),
    ("route via 192.168.56.77", "lab address (192.168.56.77)"),
    ("route via 10.0.2.15", "lab address (10.0.2.15)"),
    ("see .codex_state/escalations", "engine (.codex_state)"),
    ("written by Codex", "engine (Codex)"),
    ("the advisor decides", "engine (advisor)"),
    ("as phase3.py says", "engine file (phase3.py)"),
])
def test_lab_values_and_engine_references_are_refused(text, problem):
    found = sc.text_problems(text, LAB, FILES)
    assert any(problem in p for p in found), found


@pytest.mark.parametrize("text", [
    "probe: ping {{NODE_ADDR}}; ls {{LOCALDIR}}/bin",
    "evidence: {{SITE:engine-runner}} has no such step",
    "iptables -A INPUT -s 10.255.255.2/32 -j ACCEPT",
    "kinds.yml names ubuntu2",
])
def test_placeholders_and_test_values_pass(text):
    assert sc.text_problems(text, LAB, FILES) == []


@pytest.mark.parametrize("value, problem", [
    ("8.8.8.8", "public address"),
    ("mail.mycompany.com", "domain name"),
    ("ops@corp.org", "e-mail"),
    ("-----BEGIN OPENSSH PRIVATE KEY-----", "private key"),
    ("0123456789abcdef0123456789abcdef", "opaque value"),
])
def test_a_params_value_that_may_be_real_is_refused(value, problem):
    assert any(problem in p for p in sc.fake_problems(value)), sc.fake_problems(value)


@pytest.mark.parametrize("value", [
    "203.0.113.50", "10.253.0.0", "255.255.255.0", "127.0.0.1", "p8test.example.invalid", "relay.example.com",
    "p8test@example.invalid", "/opt/site/bin/check.sh", "{{PEER_ADDR+100}}", "tcp", "P8 Test User",
    "$6$p8testsalt$9xUyvkdoWnCLqAbCdEfGhIjKlMnOpQrStUvWxYz0123456789", "AAAAB3NzaC1yc2EAAAADAQABAAABgQC" + "x" * 40,
])
def test_a_fake_or_generic_params_value_passes(value):
    assert sc.fake_problems(value) == []


def test_a_params_fixture_file_is_checked_value_by_value(tmp_path, monkeypatch):
    params = tmp_path / "spec" / "behaviour" / "fixtures" / "params"
    params.mkdir(parents=True)
    f = params / "p8x.json"
    f.write_text(json.dumps({"servers": ["203.0.113.1", "8.8.4.4"], "name": "p8test"}))
    monkeypatch.setattr(sc, "SUITE", tmp_path / "spec" / "behaviour")
    found = sc.check_file(f, LAB, FILES)
    assert len(found) == 1 and "8.8.4.4" in found[0]


def test_the_suite_as_committed_is_clean():
    assert sc.main([]) == 0
