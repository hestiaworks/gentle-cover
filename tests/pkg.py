"""Import the integration's modules without running its __init__ (which needs HA)."""

import importlib
import sys
import types
from pathlib import Path

PACKAGE = "gentle_cover_under_test"


def load(name: str):
    if PACKAGE not in sys.modules:
        package = types.ModuleType(PACKAGE)
        # The nearest custom_components/gentle_cover above the tests, so they
        # run from this repository and from a Home Assistant config alike.
        here = Path(__file__).resolve()
        source = next(
            parent / "custom_components" / "gentle_cover"
            for parent in here.parents
            if (parent / "custom_components" / "gentle_cover").is_dir()
        )
        package.__path__ = [str(source)]
        sys.modules[PACKAGE] = package
    return importlib.import_module(f"{PACKAGE}.{name}")
