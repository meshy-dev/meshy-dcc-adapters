#!/usr/bin/env python
"""Show Python and dependency versions for meshy-dcc-blender."""

import sys
from importlib.metadata import PackageNotFoundError, version

print("📦 Environment Information:")
print(f"Python version: {sys.version.split()[0]}")
print("")

print("Key Packages:")
packages = ["meshy-dcc-blender", "meshy-dcc-core", "pytest", "ruff"]
for pkg in packages:
    try:
        print(f"  {pkg}: {version(pkg)}")
    except PackageNotFoundError:
        if pkg == "meshy-dcc-blender":
            print(f"  {pkg}: not installed (run: pip install -e .)")
        else:
            print(f"  {pkg}: not installed")
