"""Cancel an owned Blender render job."""

from meshy_dcc_core.skill import skill_entry

from meshy_dcc_blender._render_job_ops import cancel_render_job


@skill_entry
def main(**kwargs) -> dict:
    return cancel_render_job(**kwargs)
