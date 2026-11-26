"""The fixtures the public suite carries are the engine's, provably (HQ review of design note F, rulings 2 and 6)."""
import json
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))
sys.path.insert(1, str(TOOLS.parent))
import fixtures_move as fm  # noqa: E402

SETS = fm.sets()


def local(tmp_path, monkeypatch, name, data):
    monkeypatch.setattr(fm, "LOCAL", tmp_path)
    (tmp_path / name).write_text(json.dumps(data))
    return Path(name)


def test_lab_values_become_role_placeholders_that_render_back(tmp_path, monkeypatch):
    rel = local(tmp_path, monkeypatch, "puppet_infrastructure::backup.json",
                {"dir": "/opt/puppet-infrastructure/x", "from": ["192.168.56.1"]})
    template, why = fm.judge(rel, SETS)
    assert template == {"dir": "{{LOCALDIR}}/x", "from": ["{{CONTROLLER_ADDR}}"]}, why


def test_a_value_that_may_be_real_stays_local(tmp_path, monkeypatch):
    rel = local(tmp_path, monkeypatch, "puppet_infrastructure::backup.json", {"dns": ["8.8.8.8"]})
    template, why = fm.judge(rel, SETS)
    assert template is None and "public address" in why


def test_the_short_name_drops_the_module_prefix():
    assert fm.short(Path("for/puppet_infrastructure::a/puppet_infrastructure::b.json")) == Path("for/a/b.json")


def test_a_node_fixture_names_the_peer_by_role_and_keeps_its_code():
    text, why = fm.judge_node("p8test_domain_dns", SETS)
    assert "nameserver {{PEER_ADDR}}" in text, why
    original = fm.code((fm.NODE_IN / "p8test_domain_dns.pp").read_text())
    assert len(fm.code(text)) == len(original)


def test_every_moved_fixture_is_still_neutral():
    assert fm.main(["verify"]) == 0
