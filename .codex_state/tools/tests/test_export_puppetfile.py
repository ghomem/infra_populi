import importlib.util
import sys
from pathlib import Path

sys.dont_write_bytecode = True
TOOL = Path(__file__).resolve().parents[1] / "export_puppetfile.py"
spec = importlib.util.spec_from_file_location("export_puppetfile", TOOL)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

PINNED = """forge 'https://forge.puppet.com'

mod 'saz-resolv_conf', '8.0.1'
mod "puppet-network", "2.2.1"  # comment allowed
"""


def test_all_pinned_is_clean():
    assert mod.unpinned_lines(PINNED) == []
    assert mod.pinned_modules(PINNED) == {"saz-resolv_conf": "8.0.1", "puppet-network": "2.2.1"}


def test_bare_mod_line_is_reported():
    problems = mod.unpinned_lines(PINNED + "mod 'puppetlabs-stdlib'\n")
    assert len(problems) == 1 and "puppetlabs-stdlib" in problems[0]


def test_range_or_latest_is_not_a_pin():
    for rest in (", '>= 9.0.0'", ", :latest", ", '9.7'"):
        assert mod.unpinned_lines(f"mod 'puppetlabs-stdlib'{rest}\n"), rest


def test_git_source_is_reported():
    text = "mod 'foo',\n  :git => 'https://example.invalid/foo.git'\n"
    assert mod.unpinned_lines(text)


def test_check_mode_exit_codes(tmp_path):
    good = tmp_path / "good"
    good.write_text(PINNED)
    assert mod.main(["--check", str(good)]) == 0
    bad = tmp_path / "bad"
    bad.write_text("mod 'saz-sudo'\n")
    try:
        mod.main(["--check", str(bad)])
    except SystemExit as exc:
        assert "saz-sudo" in str(exc)
    else:
        raise AssertionError("unpinned file passed --check")
