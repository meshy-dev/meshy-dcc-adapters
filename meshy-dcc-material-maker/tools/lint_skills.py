from pathlib import Path

from meshy_dcc_core import validate_skill

skills_root = Path(__file__).parents[1] / "src" / "meshy_dcc_material_maker" / "skills"
reports = [
    validate_skill(str(path))
    for path in skills_root.iterdir()
    if path.is_dir() and (path / "SKILL.md").is_file()
]
assert all(report.is_clean for report in reports), [report.issues for report in reports]
print(f"validated {len(reports)} bundled skills")
