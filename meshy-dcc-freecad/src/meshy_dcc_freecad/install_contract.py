"""Thin compatibility facade for the shared Install SOP v1 contract."""

from __future__ import annotations

import meshy_dcc_core as _core

# Value of the report document's own `schema_version` field. Kept in sync with
# `load_install_sop_schema()["properties"]["schema_version"]["const"]` by
# tests/test_doctor.py, which fails when the resolved core drifts.
#
# This is deliberately NOT the revision of the published schema artifact
# (`INSTALL_SOP_SCHEMA_REVISION`), which only ever adds optional members and
# moves independently of what a document means.
SCHEMA_VERSION = 1

EXIT_OK = _core.INSTALL_EXIT_OK
EXIT_PREFLIGHT = _core.INSTALL_EXIT_PREFLIGHT
EXIT_VERIFY = _core.INSTALL_EXIT_VERIFY


def runtime_core_version() -> str:
    return str(getattr(_core, "__version__", "unavailable"))
