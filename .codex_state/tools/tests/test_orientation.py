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
