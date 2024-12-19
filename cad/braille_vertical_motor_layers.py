"""Using a layer of screws (like the `cnc_plotter` branch), make motor holder.

Intended as a proof of concept to see how the motors can fit.

Conclusion: At 2.5mm pitch, Motor OD=4mm, H=8mm motors can't really fit.

Conclusion: At 3mm pitch though, Motor OD=4mm, H=8mm motors can totally fit! Just need
to bend their shafts a bit to make them mate with the screws!
"""

import copy
import random
from dataclasses import dataclass
from datetime import datetime, timezone
from itertools import product
from pathlib import Path

import build123d as bd
import build123d_ease as bde
from build123d_ease import show
from loguru import logger


def evenly_space_with_center(
    center: float = 0, *, count: int, spacing: float
) -> list[float]:
    """Evenly space `count` items around `center` with `spacing`."""
    half_spacing = (count - 1) * spacing / 2
    return [center - half_spacing + i * spacing for i in range(count)]


@dataclass(kw_only=True)
class HousingSpec:
    """Specification for braille cell in general."""

    dot_pitch_x: float = 3
    dot_pitch_y: float = 3
    inter_cell_pitch_x: float = 6
    inter_cell_pitch_y: float = 10

    motor_body_od: float = 4.0
    motor_body_length: float = 8.0

    cell_count_x: int = 3
    cell_count_y: int = 2

    # TODO(KilowattSynthesis): Set these as properties
    total_x: float = 50
    total_y: float = 20
    total_z: float = 20

    def __post_init__(self) -> None:
        """Post initialization checks."""
        hypot_len = (self.dot_pitch_x**2 + self.dot_pitch_y**2) ** 0.5
        logger.info(f"Hypotenuse length: {hypot_len:.2f} mm")

    def deep_copy(self) -> "HousingSpec":
        """Copy the current spec."""
        return copy.deepcopy(self)


def make_motor_placement_demo(spec: HousingSpec) -> bd.Part:
    """Make demo of motor placement."""
    p = bd.Part(None)

    # Create the main outer shell.
    # p += bd.Box(
    #     spec.total_x,
    #     spec.total_y,
    #     spec.total_z,
    #     align=bde.align.ANCHOR_BOTTOM,
    # )

    # Create the motor holes.
    for dot_num, (cell_x, cell_y, dot_offset_x, dot_offset_y) in enumerate(
        product(
            evenly_space_with_center(
                count=spec.cell_count_x, spacing=spec.inter_cell_pitch_x
            ),
            evenly_space_with_center(
                count=spec.cell_count_y, spacing=spec.inter_cell_pitch_y
            ),
            evenly_space_with_center(count=2, spacing=spec.dot_pitch_x),
            evenly_space_with_center(count=3, spacing=spec.dot_pitch_y),
        )
    ):
        dot_x = cell_x + dot_offset_x
        dot_y = cell_y + dot_offset_y

        # Create the motor hole.
        p += bd.Cylinder(
            spec.motor_body_od / 2,
            # Add a tiny random amount so you can see the edges clearer.
            spec.motor_body_length + random.random() * 0.2,
            align=bde.align.ANCHOR_BOTTOM,
        ).translate(
            (
                dot_x,
                dot_y,
                (spec.motor_body_length + 1) * (dot_num % 2),
            )
        )

        # Create the motor shaft hole.
        p += bd.Cylinder(
            radius=0.25,
            height=spec.motor_body_length * 2.5,
            align=bde.align.ANCHOR_BOTTOM,
        ).translate(
            (
                dot_x,
                dot_y,
                (spec.motor_body_length + 1) * (dot_num % 2),
            )
        )

    return p


if __name__ == "__main__":
    start_time = datetime.now(timezone.utc)
    py_file_name = Path(__file__).name
    logger.info(f"Running {py_file_name}")

    parts = {
        "motor_placement_demo": show(make_motor_placement_demo(HousingSpec())),
    }

    logger.info("Showing CAD model(s)")

    (
        export_folder := Path(__file__).parent.parent / "build" / Path(__file__).stem
    ).mkdir(exist_ok=True, parents=True)
    for name, part in parts.items():
        # assert isinstance(part, bd.Part), f"{name} is not a Part"
        # assert part.is_manifold is True, f"{name} is not manifold"

        bd.export_stl(part, str(export_folder / f"{name}.stl"))
        bd.export_step(part, str(export_folder / f"{name}.step"))

    logger.info(
        f"Done running {py_file_name} in {datetime.now(timezone.utc) - start_time}"
    )
