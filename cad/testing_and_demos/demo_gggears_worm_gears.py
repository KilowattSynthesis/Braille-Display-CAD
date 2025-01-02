"""Test of the worm gears from the gggears library.

https://github.com/GarryBGoode/gggears/issues/1
"""

from datetime import UTC, datetime
from pathlib import Path

import build123d as bd
import git
from build123d_ease import show
from gggears import PI, RIGHT, HelicalGear
from loguru import logger


def make_worm_gear_test_1() -> bd.Part:
    """Test of the worm gears from the gggears library.

    Source: https://github.com/GarryBGoode/gggears/issues/14
    """
    gear0 = HelicalGear(
        number_of_teeth=5, helix_angle=PI / 2 * 0.75, height=5, z_anchor=0.5
    )
    gear1 = HelicalGear(
        number_of_teeth=45, helix_angle=PI / 2 * 0.25, height=5, z_anchor=0.5
    )
    gear0.mesh_to(gear1, target_dir=RIGHT)
    gear_part_0 = gear0.build_part()
    gear_part_1 = gear1.build_part()

    p = bd.Part(None)
    p += gear_part_0
    p += gear_part_1

    return p


def make_worm_gear_test_2() -> bd.Part:
    """Test of the worm gears from the gggears library.

    Source: https://github.com/GarryBGoode/gggears/issues/14
    """
    worm_gear = HelicalGear(
        number_of_teeth=5, helix_angle=PI / 2 * 0.75, height=15, z_anchor=0.5
    )
    normal_gear = HelicalGear(
        number_of_teeth=45, helix_angle=PI / 2 * 0.25, height=5, z_anchor=0.5
    )
    worm_gear.mesh_to(normal_gear, target_dir=RIGHT)

    p = bd.Part(None)
    p += worm_gear.build_part()
    p += normal_gear.build_part()

    return p


if __name__ == "__main__":
    start_time = datetime.now(UTC)
    py_file_name = Path(__file__).name
    logger.info(f"Running {py_file_name}")

    parts = {
        "worm_gear_test_1": show(make_worm_gear_test_1()),
        # Note: Test 2 takes a very long time to run (4 minutes).
        # "worm_gear_test_2": show(make_worm_gear_test_2()),
    }

    logger.info("Saving CAD model(s)...")

    repo_dir = git.Repo(__file__, search_parent_directories=True).working_tree_dir
    assert repo_dir
    (export_folder := Path(repo_dir) / "build" / Path(__file__).stem).mkdir(
        exist_ok=True, parents=True
    )
    for name, part in parts.items():
        bd.export_stl(part, str(export_folder / f"{name}.stl"))
        bd.export_step(part, str(export_folder / f"{name}.step"))

    logger.info(f"Done running {py_file_name} in {datetime.now(UTC) - start_time}")
