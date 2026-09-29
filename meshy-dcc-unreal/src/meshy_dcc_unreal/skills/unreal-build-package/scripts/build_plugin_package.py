"""Build an installable Meshy DCC Unreal plugin archive."""

from __future__ import annotations

from _build_package import build_plugin_package_impl
from meshy_dcc_core.skill import skill_entry


@skill_entry
def build_plugin_package(
    repository_root: str,
    ue_root: str,
    mode: str = "native",
    python_executable: str = "",
    core_wheel: str = "",
    core_spec: str = "meshy-dcc-core>=0.2.0,<0.3.0",
    vctoolchain_version: str = "",
    **kwargs,
) -> dict:
    return build_plugin_package_impl(
        repository_root=repository_root,
        ue_root=ue_root,
        mode=mode,
        python_executable=python_executable,
        core_wheel=core_wheel,
        core_spec=core_spec,
        vctoolchain_version=vctoolchain_version,
    )
