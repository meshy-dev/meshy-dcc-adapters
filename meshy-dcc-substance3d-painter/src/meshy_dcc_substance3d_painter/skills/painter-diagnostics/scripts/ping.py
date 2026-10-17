"""Prove that the Painter main-thread bridge is servicing requests."""

from __future__ import annotations

import os
from pathlib import Path

import meshy_dcc_core
from meshy_dcc_core.skill import skill_entry, skill_success

import meshy_dcc_substance3d_painter as adapter
from meshy_dcc_substance3d_painter.server import painter_version


@skill_entry
def main(**_kwargs):
    return skill_success(
        "Substance 3D Painter main-thread dispatch is ready.",
        host_dispatch_ready=True,
        host="substance3d_painter",
        version=painter_version(),
        host_pid=os.getpid(),
        adapter_version=adapter.__version__,
        core_version=meshy_dcc_core.__version__,
        adapter_module_path=str(Path(adapter.__file__).resolve()),
        core_module_path=str(Path(meshy_dcc_core.__file__).resolve()),
    )


if __name__ == "__main__":
    from meshy_dcc_core.skill import run_main

    run_main(main)
