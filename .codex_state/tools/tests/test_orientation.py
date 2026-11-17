"""orientation.py: per-class HQ rulings reach the Codex packet as facts (rules/class_rulings.txt)."""

import importlib.util
import sys

from conftest import TOOLS

spec = importlib.util.spec_from_file_location("orientation_rulings", TOOLS / "orientation.py")
orientation = importlib.util.module_from_spec(spec)
sys.modules["orientation_rulings"] = orientation
spec.loader.exec_module(orientation)


def test_ruling_lines_match_the_class_exactly(tmp_path):
    f = tmp_path / "class_rulings.txt"
    f.write_text("# comment nginx_frontend_domain x\nnginx_frontend_domain use Integer() — ref A\n"
                 "nginx_frontend use something else — ref B\nnginx_frontend_domain\n")
    assert orientation.ruling_lines("nginx_frontend_domain", f) == ["use Integer() — ref A"]
    assert orientation.ruling_lines("nginx_frontend", f) == ["use something else — ref B"]
    assert orientation.ruling_lines("backup", f) == []
    assert orientation.ruling_lines("backup", tmp_path / "missing.txt") == []


def test_tracked_rulings_file_names_the_integer_fix():
    (ruling,) = orientation.ruling_lines("nginx_frontend_domain")
    assert "Integer($element_split[1])" in ruling and "DESIGN_DECISIONS" in ruling


# 2026-11-17 (mysql_server): a done class's re-migration reads hazard-8 drift from before its first migrate commit.
def test_first_migrate_commit_is_the_oldest_for_the_exact_class(monkeypatch):
    log = ("a1\tP8: migrate puppet_infrastructure::mysql_server\n"
           "b2\tP8: migrate puppet_infrastructure::mysql_server_extra\n"
           "c3\tP8: migrate puppet_infrastructure::mysql_server\n")
    monkeypatch.setattr(orientation.generator, "run_git", lambda args: log)
    assert orientation.first_migrate_commit("mysql_server") == "a1"
    assert orientation.first_migrate_commit("mysql_db") is None


def test_repo_mysql_server_has_no_drift_before_its_first_migration():
    base = orientation.baseline.for_class("mysql_server")
    first = orientation.first_migrate_commit("mysql_server")
    assert first and orientation.pre_migration_drift("mysql_server", base, first) == []
