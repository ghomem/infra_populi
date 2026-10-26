import importlib.util
import sys
from pathlib import Path

import pytest

sys.dont_write_bytecode = True
GEN = Path(__file__).resolve().parents[2] / "gen_migration_order.py"


@pytest.fixture
def gen():
    spec = importlib.util.spec_from_file_location("gen_migration_order", GEN)
    module = importlib.util.module_from_spec(spec)
    sys.modules["gen_migration_order"] = module
    spec.loader.exec_module(module)
    return module


def test_baseline_name_comes_from_env_file(gen, tmp_path):
    env = tmp_path / "baseline.env"
    env.write_text("# c\nBASELINE_NAME=release-9.9.9\nBASELINE_COMMIT=x\n")
    gen.BASELINE_ENV = env
    assert gen.baseline_name() == "release-9.9.9"


def test_baseline_name_missing_fails(gen, tmp_path):
    env = tmp_path / "baseline.env"
    env.write_text("BASELINE_COMMIT=x\n")
    gen.BASELINE_ENV = env
    with pytest.raises(SystemExit):
        gen.baseline_name()


def test_repo_baseline_is_0_9_10(gen):
    assert gen.baseline_name() == "release-0.9.10"
