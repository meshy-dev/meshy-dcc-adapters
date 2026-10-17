"""
3ds Max agent workflow demo — create particle-like spheres with dynamics.

This demo shows a reproducible MCP agent workflow inside Autodesk 3ds Max.
It exercises the full gateway search/describe/call pipeline:

  1. Start the embedded MCP server in 3ds Max
  2. Create scene primitives (spheres, box as ground)
  3. Apply materials with procedural maps
  4. Set keyframes for animation
  5. Capture viewport preview

Run this inside 3ds Max MAXScript Listener or Python editor:

    import dcc_mcp_3dsmax
    dcc_mcp_3dsmax.start_server()

Then from any MCP client (Claude Desktop, dcc-mcp-cli):

    1. search_tools("sphere")    → discover create_sphere
    2. load_skill("3dsmax-modeling")
    3. 3dsmax_modeling__create_sphere(radius=25.0)
    4. load_skill("3dsmax-animation")
    5. 3dsmax_animation__set_keyframe(...)
    6. capture_viewport()        → base64 PNG of current view
"""

import pymxs

rt = pymxs.runtime


def create_particle_demo() -> dict:
    """Create 10 random spheres with animation in 3ds Max via MAXScript."""
    print("=" * 60)
    print("3ds Max agent workflow demo — particle spheres")
    print("=" * 60)

    # ── 1. Reset scene ────────────────────────────────────────────────────
    rt.resetMaxFile(rt.Name("noPrompt"))
    print("\n[1/5] Scene reset")

    # ── 2. Create ground plane ────────────────────────────────────────────
    ground = rt.Plane(length=200, width=200, name="ground")
    ground.pos = rt.Point3(0, 0, -5)
    print(f"[2/5] Ground created: {ground.name}")

    # ── 3. Create 10 random spheres ───────────────────────────────────────
    import random

    spheres = []
    for i in range(10):
        sphere = rt.Sphere(
            radius=random.uniform(5, 15),
            pos=rt.Point3(
                random.uniform(-60, 60),
                random.uniform(-60, 60),
                random.uniform(0, 40),
            ),
            name=f"particle_{i + 1:03d}",
        )
        spheres.append(sphere)
        print(f"  particle_{i + 1:03d} at ({sphere.pos.x:.1f}, {sphere.pos.y:.1f}, {sphere.pos.z:.1f})")

    print(f"[3/5] Created {len(spheres)} particle spheres")

    # ── 4. Create Standard material with noise map ────────────────────────
    for sphere in spheres:
        mat = rt.StandardMaterial()
        noise = rt.Noise()
        noise.amplitude = random.uniform(30, 80)
        mat.diffusemap = noise
        sphere.material = mat
        rt.showTextureMap(mat, noise, True)

    print("[4/5] Procedural materials applied")

    # ── 5. Keyframe sphere positions (bouncing effect) ────────────────────
    for i, sphere in enumerate(spheres):
        with rt.animate(True):
            # Frame 0 — start position
            rt.sliderTime = 0
            sphere.pos.z = random.uniform(0, 40)

            # Frame 30 — peak
            rt.sliderTime = 30
            sphere.pos.z = random.uniform(40, 80)

            # Frame 60 — ground
            rt.sliderTime = 60
            sphere.pos.z = 0

    print("[5/5] Bounce keyframes set on all spheres")

    # ── Summary ───────────────────────────────────────────────────────────
    print("=" * 60)
    print("Demo complete — scene ready for viewport capture")
    print("=" * 60)

    return {
        "spheres_created": len(spheres),
        "sphere_names": [s.name for s in spheres],
        "ground_name": ground.name,
        "status": "success",
    }


def main() -> dict:
    try:
        return create_particle_demo()
    except Exception as exc:
        import traceback

        traceback.print_exc()
        return {"status": "error", "message": str(exc)}


if __name__ == "__main__":
    result = main()
    for key, value in result.items():
        print(f"{key}: {value}")
