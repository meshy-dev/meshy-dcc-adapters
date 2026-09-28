"""Submit a bounded multiview render in an isolated Blender worker."""

from meshy_dcc_core.skill import skill_entry

from meshy_dcc_blender._multiview_ops import start_multiview_render_job


@skill_entry
def main(**kwargs):
    return start_multiview_render_job(**kwargs)
