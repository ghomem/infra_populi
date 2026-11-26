"""The engine's switch sample (HQ review of design note F, ruling 7): verdicts compared per check, and coverage."""
import json
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))
import behaviour_sample as bs  # noqa: E402

ENGINE = {"outcome": "ALL_PASS", "apply": {"green": True},
          "clean": [{"id": "a", "ok": True}],
          "applied": [{"id": "a", "passed": True, "mismatch": {"passed": False}},
                      {"id": "m", "passed": True, "action": {"rc": 0}}],
          "variants": {"rhel": {"outcome": "ALL_PASS", "apply": {"green": True}, "clean": [], "applied": [
              {"id": "r", "passed": True}]}}}


def records(tmp_path, monkeypatch, public):
    monkeypatch.setattr(bs, "OLD", tmp_path / "old")
    monkeypatch.setattr(bs, "NEW", tmp_path / "new")
    (tmp_path / "old" / "x").mkdir(parents=True)
    (tmp_path / "new" / "x").mkdir(parents=True)
    (tmp_path / "old" / "x" / "20261125T000000Z-reviewer.json").write_text(json.dumps(ENGINE))
    (tmp_path / "new" / "x" / "20261126T000000Z.json").write_text(json.dumps(public))


def test_the_same_verdicts_compare_equal(tmp_path, monkeypatch):
    records(tmp_path, monkeypatch, ENGINE)
    assert bs.compare("x") == []


def test_a_mismatch_control_that_passes_only_in_the_public_run_is_a_difference(tmp_path, monkeypatch):
    public = json.loads(json.dumps(ENGINE))
    public["applied"][0]["mismatch"]["passed"] = True
    records(tmp_path, monkeypatch, public)
    assert bs.compare("x") == ["x base mismatch a: engine False, public True"]


def test_a_variant_check_is_compared_too(tmp_path, monkeypatch):
    public = json.loads(json.dumps(ENGINE))
    public["variants"]["rhel"]["applied"][0]["passed"] = False
    records(tmp_path, monkeypatch, public)
    assert bs.compare("x") == ["x variant rhel applied r: engine True, public False"]


def test_the_helpers_are_read_from_the_suite():
    assert "p8_count" in bs.HELPERS and "p8_hold" in bs.HELPERS
