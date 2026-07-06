"""Make the hook and script modules importable from tests."""
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
for sub in ("hooks", "scripts"):
    p = str(ROOT / sub)
    if p not in sys.path:
        sys.path.insert(0, p)
