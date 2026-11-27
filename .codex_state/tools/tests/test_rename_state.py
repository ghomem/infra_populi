"""A behaviour review across the module rename (HQ review of the behaviour suite, ruling 9): the review that held before
(checks/renamed.json) judges the renamed set once the class's rename review passed for exactly that set."""
import hashlib
import json
import os
import subprocess
import sys

from conftest import TOOLS

SET = b"class: x\nchecks: []\n"


def judged(tmp_path, held=None, rename=None, record_at="20261120T000000Z", raw=SET):
    renamed, reviews = tmp_path / "renamed.json", tmp_path / "rename"
    renamed.write_text(json.dumps({"x": held} if held else {}))
    if rename:
        (reviews / "x").mkdir(parents=True)
        (reviews / "x" / "20261128T000000Z.json").write_text(json.dumps(rename))
    code = (f"import sys; sys.path.insert(0, {str(TOOLS)!r}); import phase3; "
            f"print(phase3.reviewed_as_is('x', {{'at': {record_at!r}, 'check_file_sha256': 'old', "
            f"'content_sha256': 'old'}}, {raw!r}))")
    p = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
                       env={**os.environ, "P8_RENAMED": str(renamed), "P8_RENAME_REVIEWS": str(reviews)})
    assert p.returncode == 0, p.stderr
    return p.stdout.strip() == "True"


HELD = {"state": "pass", "review_at": "20261120T000000Z", "set_sha256": "before"}
PASS = {"verdict": "PASS", "set_sha256": hashlib.sha256(SET).hexdigest()}


def test_the_review_that_held_judges_the_renamed_set_after_a_passing_rename_review(tmp_path):
    assert judged(tmp_path, HELD, PASS)


def test_without_a_passing_rename_review_the_renamed_set_is_unreviewed(tmp_path):
    assert not judged(tmp_path, HELD, None)
    (tmp_path / "b").mkdir()
    assert not judged(tmp_path / "b", HELD, {**PASS, "verdict": "FAIL"})


def test_only_the_review_that_held_and_only_the_set_the_rename_review_judged(tmp_path):
    assert not judged(tmp_path, HELD, PASS, record_at="20261121T000000Z")
    (tmp_path / "c").mkdir()
    assert not judged(tmp_path / "c", HELD, PASS, raw=SET + b"# changed after the rename\n")
