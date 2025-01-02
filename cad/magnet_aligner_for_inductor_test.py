"""Quick jig with a handle to test out inductors to see if they can lift the magnets.

Has a spot for one cylinder to stay in place on one end, and a spot for a braille cell
on the other end.
"""

import copy
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from itertools import product
from pathlib import Path

import build123d as bd
import build123d_ease as bde
import git
from build123d_ease import show
from loguru import logger


@dataclass(kw_only=True)
class MainSpec:
    """Specification for braille cell housing."""

    magnet_od: float
    magnet_height: float = 3

    dot_pitch: float = 2.5

    base_thickness: float = 0.5

    def __post_init__(self) -> None:
        """Post initialization checks."""
        data = {}
        logger.info(json.dumps(data, indent=2))

    def deep_copy(self) -> "MainSpec":
        """Copy the current spec."""
        return copy.deepcopy(self)


def make_magnet_aligner(spec: MainSpec) -> bd.Part:
    """Make a single cam rod, pointing in Z axis."""
    p = bd.Part(None)

    p += bd.Box(
        8,
        20,
        spec.magnet_height + spec.base_thickness,
        align=(bd.Align.CENTER, bd.Align.MIN, bd.Align.MIN),  # Anchor front bottom.
    )

    p += bd.Pos(Y=-1.5) * bd.Cylinder(
        spec.magnet_od / 2 + 2,
        spec.magnet_height + spec.base_thickness,
        align=bde.align.ANCHOR_BOTTOM,
    )

    p -= bd.Pos(Y=-1.5, Z=spec.base_thickness) * bd.Cylinder(
        radius=spec.magnet_od / 2,
        height=spec.magnet_height,
        align=bde.align.ANCHOR_BOTTOM,
    )

    # At the other end, create a braille cell.
    for dot_x, dot_y in product(
        bde.evenly_space_with_center(count=2, spacing=spec.dot_pitch),
        bde.evenly_space_with_center(count=3, spacing=spec.dot_pitch, center=20 - 5),
    ):
        p -= bd.Pos(X=dot_x, Y=dot_y, Z=spec.base_thickness) * bd.Cylinder(
            radius=spec.magnet_od / 2,
            height=spec.magnet_height,
            align=bde.align.ANCHOR_BOTTOM,
        )

    return p


if __name__ == "__main__":
    start_time = datetime.now(UTC)
    py_file_name = Path(__file__).name
    logger.info(f"Running {py_file_name}")

    parts = {
        "magnet_aligner_2mm_od": show(make_magnet_aligner(MainSpec(magnet_od=2.2))),
        "magnet_aligner_1mm_od": show(make_magnet_aligner(MainSpec(magnet_od=1.2))),
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
