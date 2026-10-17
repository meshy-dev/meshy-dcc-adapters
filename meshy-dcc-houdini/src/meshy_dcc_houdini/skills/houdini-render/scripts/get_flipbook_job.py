"""Read a chunked viewport flipbook job."""

from __future__ import annotations

from flipbook import get_flipbook_job
from meshy_dcc_core.skill import skill_entry


@skill_entry
def main(**kwargs) -> dict:
    return get_flipbook_job(**kwargs)
