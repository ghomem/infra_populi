"""Generated rules digest (step 3.5): derived from DESIGN_DECISIONS.md, kept current by the pre-commit hook."""

import importlib.util
import subprocess
import sys

from conftest import TOOLS

spec = importlib.util.spec_from_file_location("gen_rules_digest", TOOLS / "gen_rules_digest.py")
digest = importlib.util.module_from_spec(spec)
sys.modules["gen_rules_digest"] = digest
spec.loader.exec_module(digest)

LOG = """# Design Decisions

## 2026-07-01 — Declared upstream baseline: release-0.9.8
Decision: the baseline is release-0.9.8.

## 2026-07-02 — Something else
1. First rule line.
   continuation is not listed
2. Second rule.

## 2026-10-26 — HQ rulings
1. Baseline. SUPERSEDES 2026-07-01 "Declared upstream baseline: release-0.9.8" and more.
2. Also supersedes 2026-01-01 "Nothing by that name".
"""


def test_supersession_marks_the_matching_entry_and_lists_unresolved():
    text = digest.render(LOG)
    assert "## 2026-07-01 — Declared upstream baseline: release-0.9.8 — **SUPERSEDED (whole or part) by** " \
           "2026-10-26 — HQ rulings" in text
    assert "## 2026-07-02 — Something else\n- 1. First rule line.\n- 2. Second rule.\n" in text
    assert "continuation" not in text
    assert 'supersedes 2026-01-01 "Nothing by that name"' in text
    assert text.index("2026-10-26") < text.index("2026-07-02") < text.index("## 2026-07-01")


def test_entry_without_rule_lines_says_so():
    text = digest.render("## 2026-07-03 — Prose only\nJust prose.\n")
    assert "- (no numbered/Rule/Decision lines; read the entry)" in text


def test_repo_digest_is_current():
    proc = subprocess.run([sys.executable, str(TOOLS / "gen_rules_digest.py"), "--check"], capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
