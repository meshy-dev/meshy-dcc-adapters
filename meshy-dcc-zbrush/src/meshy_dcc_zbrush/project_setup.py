"""Set up a project folder so ``meshy-dcc start-instance`` can launch ZBrush.

ZBrush has no project directory of its own; the project is the folder that
holds the work (models to import, saved ``.zpr`` and ``.ztl`` files). Setup
writes one file, ``<project>/.meshy-dcc/launch-plan.json``: start ZBrush with
``-script`` pointing at the bridge inside this package. Nothing is written into
the ZBrush installation or the user's ZBrush settings, so a ZBrush the user
opens by hand does not load the bridge.

``meshy-dcc install --dcc-type zbrush --project <folder>`` runs
``meshy-dcc-zbrush setup-project <folder> --dcc-path <ZBrush> --json`` from the
package with the package's own Python.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Optional

from meshy_dcc_zbrush.__version__ import __version__

LAUNCH_PLAN_RELATIVE = Path(".meshy-dcc") / "launch-plan.json"
EXECUTABLE_ENV = "MESHY_DCC_ZBRUSH_EXECUTABLE"


def bridge_script() -> Path:
    """The bridge ZBrush runs with ``-script`` (packaged inside the wheel)."""
    return Path(__file__).resolve().parent / "plugin" / "mcp_socket_bridge.py"


def _atomic_write(path: Path, text: str) -> None:
    staging = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    staging.write_text(text, encoding="utf-8")
    os.replace(staging, path)


def setup_project(project: Path, dcc_path: Path) -> dict[str, Any]:
    """Validate ZBrush and write the project's launch plan; return the report."""
    from meshy_dcc_zbrush.install_lifecycle import _probe_zbrush_host  # noqa: PLC0415

    if not project.is_absolute() or not project.is_dir():
        raise ValueError(f"project must be an absolute path to an existing folder: {project}")
    bridge = bridge_script()
    if not bridge.is_file():
        raise ValueError(f"the ZBrush bridge is missing from this package: {bridge}")
    host = _probe_zbrush_host(dcc_path)
    state = project / LAUNCH_PLAN_RELATIVE.parent
    state.mkdir(exist_ok=True)
    ignore = state / ".gitignore"
    if not ignore.exists():
        # The plan holds machine-local paths.
        ignore.write_text("*\n", encoding="utf-8")
    plan = {
        "schema_version": 1,
        "dcc_type": "zbrush",
        "executable": host["dcc_path"],
        "argv": ["{executable}", "-script", str(bridge)],
        "version": host["zbrush_version"],
    }
    _atomic_write(project / LAUNCH_PLAN_RELATIVE, json.dumps(plan, indent=2) + "\n")
    return {
        "status": "installed",
        "adapter_version": __version__,
        "project": str(project),
        "launch_plan": str(project / LAUNCH_PLAN_RELATIVE),
        "executable": host["dcc_path"],
        "zbrush_version": host["zbrush_version"],
        "bridge": str(bridge),
    }


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="meshy-dcc-zbrush setup-project", description=__doc__.splitlines()[0])
    parser.add_argument("project", type=Path, help="Folder that holds the ZBrush work")
    parser.add_argument(
        "--dcc-path",
        type=Path,
        default=os.environ.get(EXECUTABLE_ENV) or None,
        help=f"ZBrush.app or ZBrush.exe (or set {EXECUTABLE_ENV})",
    )
    parser.add_argument("--json", action="store_true", dest="json_output")
    args = parser.parse_args(argv)
    try:
        if args.dcc_path is None:
            raise ValueError(f"pass --dcc-path or set {EXECUTABLE_ENV}")
        report = setup_project(args.project, Path(args.dcc_path))
        code = 0
    except Exception as exc:  # noqa: BLE001 - one JSON failure report for the installer
        report = {"status": "failed", "reason": str(getattr(exc, "reason", exc)), "project": str(args.project)}
        code = 10
    if args.json_output:
        print(json.dumps(report, sort_keys=True))
    else:
        print(f"{report['status']}: {report.get('launch_plan') or report.get('reason')}", file=sys.stdout)
    return code
