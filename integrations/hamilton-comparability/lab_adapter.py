"""Import the existing teaching lab without executing its notebook cells."""

import importlib.util
from pathlib import Path
import sys


def load_lab():
    name = "_parlayapi_comparability_teaching_lab"
    if name not in sys.modules:
        path = Path(__file__).resolve().parents[2] / "labs/odds-comparability/odds_comparability.py"
        spec = importlib.util.spec_from_file_location(name, path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Cannot load teaching lab at {path}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        try:
            spec.loader.exec_module(module)
        except BaseException:
            sys.modules.pop(name, None)
            raise
    return sys.modules[name]
