import os
import sys
from pathlib import Path

import pytest

SUITE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SUITE_ROOT / "src"))

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture
def tuner_root(tmp_path, monkeypatch):
    """Isolate every test's suite directory layout under a tmp_path."""
    monkeypatch.setenv("TUNERPRO_TOOLS_ROOT", str(tmp_path))
    import tunerpro_tools.config as config

    config._CONFIG = None
    cfg = config.get_config()
    yield cfg
    config._CONFIG = None
