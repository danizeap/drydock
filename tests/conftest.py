"""Make the hook and script modules importable from tests, and isolate coord state."""
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
for sub in ("hooks", "scripts"):
    p = str(ROOT / sub)
    if p not in sys.path:
        sys.path.insert(0, p)


@pytest.fixture(autouse=True)
def _isolate_drydock_coord_state(tmp_path, monkeypatch):
    """Never let coord.py write to the real %LOCALAPPDATA%\\Drydock during tests.

    Wiring coord into executors.status() means any test that reads fleet fuel
    would otherwise pollute the machine's real shared cache with test data a real
    session could then read. Every test gets its own throwaway state dir.
    """
    monkeypatch.setenv("DRYDOCK_STATE", str(tmp_path / "drydock-state"))
