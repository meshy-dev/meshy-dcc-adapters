"""Import an FBX file into 3ds Max via the dcc-mcp-3dsmax adapter.

Usage (inside 3ds Max MAXScript Listener):

    import dcc_mcp_3dsmax
    dcc_mcp_3dsmax.start_server()

Then from MCP client:

    load_skill("3dsmax-geometry-io")         # enable import/export tools
    3dsmax_geometry_io__import_fbx(file_path="C:/path/to/model.fbx")
"""

import pymxs

rt = pymxs.runtime


def import_fbx(fbx_path: str) -> dict:
    """Import an FBX file into the current 3ds Max scene."""
    if not fbx_path:
        return {"status": "error", "message": "fbx_path is required"}

    if not rt.doesFileExist(fbx_path):
        return {"status": "error", "message": f"File not found: {fbx_path}"}

    try:
        rt.importFile(
            fbx_path,
            rt.Name("noPrompt"),
            using="FBXIMP",
        )
    except RuntimeError as exc:
        return {"status": "error", "message": str(exc)}

    # Count imported objects
    count = len(list(rt.objects))
    return {
        "status": "success",
        "message": f"Imported {count} objects from {fbx_path}",
        "object_count": count,
    }


def main() -> dict:
    return import_fbx("C:/temp/model.fbx")


if __name__ == "__main__":
    result = main()
    for key, value in result.items():
    