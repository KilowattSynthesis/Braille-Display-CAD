"""Cam rod for magnetic braille cell, which uses magnets to actuate the dots.

Coupled with the sliding locking mechanism (using PCB stencils to lock/unlock certain
columns of dots), this mechanism can be used as one half of a mechanical multiplexer.

Known magnet sizes:
    * 6x2x1 Magnet: https://www.aliexpress.com/item/1005004061119495.html
    * 6x2x2, others Magnet: https://www.aliexpress.com/item/1005008214969727.html
    * D=2 x H=1 Magnet - Available.
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
import git
from build123d_ease import show
from loguru import logger


@dataclass(kw_only=True)
class BoxMagnet:
    """Magnet specification."""

    magnet_dimensions: tuple[float, float, float] = (1, 2, 6)


@dataclass(kw_only=True)
class CylinderMagnet:
    """Magnet specification."""

    magnet_diameter: float = 2
    magnet_height: float = 1


@dataclass(kw_only=True)
class MainSpec:
    """Specification for braille cell housing."""

    dot_pitch_x: float = 2.5
    dot_pitch_y: float = 2.5
    inter_cell_pitch_x: float = 6
    inter_cell_pitch_y: float = 10

    cam_pitch_x: float = 2.9

    cell_count_x: int = 3

    magnet: BoxMagnet | CylinderMagnet  # Must select!
    magnet_recess_below_surface: float = 0.1

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
    )

    if isinstance(spec.magnet, BoxMagnet):
        magnet_part = bd.Box(
            spec.cam_rod_diameter,  # Break the magnet out all the way. Extra long!
            spec.magnet.magnet_dimensions[1],
            spec.magnet.magnet_dimensions[2],
            align=(bd.Align.MIN, bd.Align.CENTER, bd.Align.CENTER),
        )
        real_magnet_thickness_x = spec.magnet.magnet_dimensions[0]
        z_count = 1
    elif isinstance(spec.magnet, CylinderMagnet):
        # Magnet points in the positive X.
        magnet_part = bd.Cylinder(
            radius=spec.magnet.magnet_diameter / 2,
            height=spec.cam_rod_diameter,  # Extra long!
            align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
        ).rotate(axis=bd.Axis.Y, angle=90)
        real_magnet_thickness_x = spec.magnet.magnet_height
        z_count = 3

    # Remove the magnets (one on each side).
    for rot, z_pos in product(
        (0, 180),
        bde.evenly_space_with_center(count=z_count, spacing=spec.dot_pitch_y),
    ):
        p -= magnet_part.translate(
            (
                (
                    spec.cam_rod_diameter / 2
                    - real_magnet_thickness_x
                    - spec.magnet_recess_below_surface
                ),
                0,
                z_pos,
            )
        ).rotate(axis=bd.Axis.Z, angle=rot)

    return p


def make_assembly_cam_rod_with_magnet(spec: MainSpec) -> bd.Part:
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

        if isinstance(spec.magnet, BoxMagnet):
            magnet_part = bd.Box(
                spec.magnet.magnet_dimensions[0],
                spec.magnet.magnet_dimensions[1],
                spec.magnet.magnet_dimensions[2],
                align=(bd.Align.MIN, bd.Align.CENTER, bd.Align.CENTER),
            )
            real_magnet_thickness_x = spec.magnet.magnet_dimensions[0]
            z_count = 1
        elif isinstance(spec.magnet, CylinderMagnet):
            # Magnet points in the positive X.
            magnet_part = bd.Cylinder(
                radius=spec.magnet.magnet_diameter / 2,
                height=spec.magnet.magnet_height,
                align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
            ).rotate(axis=bd.Axis.Y, angle=90)
            real_magnet_thickness_x = spec.magnet.magnet_height
            z_count = 3

        # Remove the magnets (one on each side).
        for rot, z_pos in product(
            (0, 180),
            bde.evenly_space_with_center(count=z_count, spacing=spec.dot_pitch_y),
        ):
            p += (
                magnet_part.translate(
                    (
                        (
                            spec.cam_rod_diameter / 2
                            - real_magnet_thickness_x
                            - spec.magnet_recess_below_surface
                        ),
                        0,
                        z_pos,
                    )
                )
                .rotate(axis=bd.Axis.Z, angle=rot)
                .rotate(axis=bd.Axis.Z, angle=random_rot_value)  # Extra step.
                .translate((0, dot_x, 0))  # Extra step.
            )

    return p


if __name__ == "__main__":
    start_time = datetime.now(UTC)
    py_file_name = Path(__file__).name
    logger.info(f"Running {py_file_name}")

    parts = {
        "cam_rod_box_magnets": show(make_cam_rod(MainSpec(magnet=BoxMagnet()))),
        "assembly_cam_rod_with_box_magnet": show(
            make_assembly_cam_rod_with_magnet(MainSpec(magnet=BoxMagnet()))
        ),
        "cam_rod_cyl_magnets": show(make_cam_rod(MainSpec(magnet=CylinderMagnet()))),
        "assembly_cam_rod_with_cyl_magnet": show(
            make_assembly_cam_rod_with_magnet(MainSpec(magnet=CylinderMagnet()))
        ),
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
