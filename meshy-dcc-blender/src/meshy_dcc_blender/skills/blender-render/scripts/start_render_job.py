"""Submit an isolated Blender animation render."""

from meshy_dcc_core.skill import skill_entry

from meshy_dcc_blender._render_job_ops import start_render_job


@skill_entry
def main(**kwargs) -> dict:
    return start_render_job(**kwargs)
