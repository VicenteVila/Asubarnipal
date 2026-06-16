"""Dependency verification script for TurboQuant Phase 2."""

import importlib
import sys
from typing import Dict, Tuple


DEPS = {
    "torch": ("torch", "2.0"),
    "transformers": ("transformers", "4.35"),
    "accelerate": ("accelerate", "0.24"),
}

OPTIONAL_DEPS = {
    "bitsandbytes": ("bitsandbytes", "0.41", "CUDA quantization library (GPU required)"),
}


def check_deps() -> Dict[str, Tuple[bool, str]]:
    results = {}
    for name, (pkg, min_ver) in DEPS.items():
        try:
            mod = importlib.import_module(pkg)
            ver = getattr(mod, "__version__", "unknown")
            results[name] = (True, ver)
        except ImportError:
            results[name] = (False, f"NOT INSTALLED (required >= {min_ver})")

    for name, (pkg, min_ver, desc) in OPTIONAL_DEPS.items():
        try:
            mod = importlib.import_module(pkg)
            ver = getattr(mod, "__version__", "unknown")
            results[name] = (True, f"{ver} (CUDA)")
        except ImportError:
            results[name] = (False, f"NOT INSTALLED - {desc}")

    return results


def print_status():
    results = check_deps()
    all_ok = True
    print("=" * 50)
    print("TurboQuant Dependency Check")
    print("=" * 50)
    for name, (ok, detail) in results.items():
        if ok:
            marker = "✅"
        else:
            marker = "❌"
            all_ok = False
        print(f"  {marker} {name}: {detail}")

    print("=" * 50)
    if all_ok:
        print("All required dependencies installed.")
    else:
        print("Some dependencies missing. Install with:")
        print("  pip install torch transformers accelerate")
        print("  # For GPU support: pip install bitsandbytes")
        print("=" * 50)
    return all_ok


if __name__ == "__main__":
    sys.exit(0 if print_status() else 1)
