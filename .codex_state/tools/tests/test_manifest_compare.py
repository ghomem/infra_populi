"""manifest_compare: the harness's managed block and the public manifest compared as Puppet code."""
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))
sys.path.insert(1, str(TOOLS.parent))
import manifest_compare as mc  # noqa: E402

HARNESS_OUT = """==> Lab node: ubuntu
# BEGIN CODEX MANAGED (do not edit by hand)
# MOCK-APPLY node fixture: x
# history of the fixture
file { '/x': ensure => file }
include puppet_infrastructure::a
# END CODEX MANAGED
include outside
"""


def test_only_the_managed_block_code_counts():
    assert mc.code(HARNESS_OUT) == ["file { '/x': ensure => file }", "include puppet_infrastructure::a"]


def test_the_public_manifest_compares_without_its_comments():
    public = "# Node fixture x: ...\nfile { '/x': ensure => file }\n\ninclude puppet_infrastructure::a\n"
    assert mc.public_code(public) == mc.code(HARNESS_OUT)
