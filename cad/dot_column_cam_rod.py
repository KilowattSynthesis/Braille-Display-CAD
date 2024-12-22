"""Cam rod for each column, rotated to a multiple of 45 degrees (8 positions).

Would require that the bed be lifted.
"""

import copy
import json
import random
from dataclasses import dataclass
from datetime import UTC, datetime
from itertools import product
from pathlib import Path

import build123d as bd
import build123d_ease as bde
from build123d_ease import show
from loguru import logger


@dataclass(kw_only=True)
class MainSpec:
    """Specification for braille cell housing."""

    dot_pitch_x: float = 2.5
    dot_pitch_y: float = 2.5
    inter_cell_pitch_x: float = 6
    inter_cell_pitch_y: float = 10

    cam_pitch_x: float = 2.9

    cell_count_x: int = 3

    dot_travel: float = 1
    dot_diameter_in_rod_inner: float = 0.5
    dot_diameter_in_rod_outer: float = 0.8

    # Like `dot_travel`, but for the not-down dot positions.
    dot_up_divot_depth: float = 0.2

    cam_rod_diameter: float = 2.4  # Must be less than dot_pitch_x.
    cam_rod_length: float = 10

    def __post_init__(self) -> None:
        """Post initialization checks."""
        data = {}
        logger.info(json.dumps(data, indent=2))

    def deep_copy(self) -> "MainSpec":
        """Copy the current spec."""
        return copy.deepcopy(self)


def make_cam_rod(spec: MainSpec) -> bd.Part:
    """Make a single cam rod, pointing in Z axis."""
    p = bd.Part(None)

    p += bd.Cylinder(
        radius=spec.cam_rod_diameter / 2,
        height=spec.cam_rod_length,
    ).rotate(
        # Rotate is a hack so that the cylinder seam doesn't insect the dots.
        # If the seam intersects the dots, sometimes they're not removed right.
        axis=bd.Axis.Z,
        angle=360 / 16,
    )

    # Remove the magnets (one on each side).
    for (rot_idx, rot_val), (z_idx, z_pos) in product(
        enumerate(range(0, 360, 45)),
        enumerate(bde.evenly_space_with_center(count=3, spacing=spec.dot_pitch_y)),
    ):
        # Only dig out not-extended pins.
        assert 0 <= rot_idx < 8  # noqa: PLR2004
        assert 0 <= z_idx < 3  # noqa: PLR2004
        is_pin_extended: bool = (rot_idx & (1 << z_idx)) > 0
        # logger.debug(f"{rot_idx=}, {z_idx=}, {is_pin_extended=}")
        dot_depth = spec.dot_travel if is_pin_extended else spec.dot_up_divot_depth

        p -= (
            (
                bd.Cone(
                    # Bottom is toward the center of the cam rod.
                    bottom_radius=spec.dot_diameter_in_rod_inner / 2,
                    top_radius=spec.dot_diameter_in_rod_outer / 2,
                    height=dot_depth,
                    align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
                )
                # Add on a cylinder that removes the extra bit above the cone.
                # Required because the faces of the cone are flat, but the rod is round.
                + bd.Cylinder(
                    radius=spec.dot_diameter_in_rod_outer / 2,
                    height=5,
                    align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
                ).translate((0, 0, spec.dot_travel - 0.05))
            )
            .rotate(axis=bd.Axis.Y, angle=90)  # Point in Pos X.
            .translate(
                (
                    spec.cam_rod_diameter / 2 - dot_depth,
                    0,
                    z_pos,
                )
            )
            .rotate(axis=bd.Axis.Z, angle=rot_val)
        )

    return p


def make_assembly_cam_rod(spec: MainSpec) -> bd.Part:
    """Make an assembly of cam rod with magnet."""
    p = bd.Part(None)

    for cell_x, dot_offset_x in product(
        bde.evenly_space_with_center(count=3, spacing=spec.inter_cell_pitch_x),
        bde.evenly_space_with_center(count=2, spacing=spec.cam_pitch_x),
    ):
        dot_x = cell_x + dot_offset_x

        random_rot_value = random.randint(0, 359)

        p += (
            make_cam_rod(spec)
            .rotate(axis=bd.Axis.Z, angle=random_rot_value)
            .translate((0, dot_x, 0))
        )

    return p


if __name__ == "__main__":
    start_time = datetime.now(UTC)
    py_file_name = Path(__file__).name
    logger.info(f"Running {py_file_name}")

    parts = {
        "cam_rod": show(make_cam_rod(MainSpec())),
        "assembly_cam_rod_with_box_magnet": (make_assembly_cam_rod(MainSpec())),
    }

    logger.info("Saving CAD model(s)...")

    (
        export_folder := Path(__file__).parent.parent / "build" / Path(__file__).stem
    ).mkdir(
        exist_ok=True,
        parents=True,
    )
    for name, part in parts.items():
        bd.export_stl(part, str(export_folder / f"{name}.stl"))
        bd.export_step(part, str(export_folder / f"{name}.step"))

    logger.info(f"Done running {py_file_name} in {datetime.now(UTC) - start_time}")
