"""Using a layer of screws (like the `cnc_plotter` branch), make motor holder.

Intended as a proof of concept to see how the motors can fit.

Conclusion: At 2.5mm pitch, Motor OD=4mm, H=8mm motors can't really fit.

Conclusion: At 3mm pitch though, Motor OD=4mm, H=8mm motors can totally fit! Just need
to bend their shafts a bit to make them mate with the screws!
"""

import copy
import random
from dataclasses import dataclass
from datetime import UTC, datetime
from itertools import product
from pathlib import Path

import build123d as bd
import build123d_ease as bde
from build123d_ease import show
from loguru import logger

# TODO(KilowattSynthesis): Place motors offset by 1 in the second line of Braille
# TODO(KilowattSynthesis): Add slanted routing for screwdrivers to reach the dot pitch


def evenly_space_with_center(
    center: float = 0,
    *,
    count: int,
    spacing: float,
) -> list[float]:
    """Evenly space `count` items around `center` with `spacing`."""
    half_spacing = (count - 1) * spacing / 2
    return [center - half_spacing + i * spacing for i in range(count)]


@dataclass(kw_only=True)
class HousingSpec:
    """Specification for braille cell in general."""

    motor_pitch_x: float = 3
    motor_pitch_y: float = 3
    dot_pitch_x: float = 2.5
    dot_pitch_y: float = 2.5
    inter_cell_pitch_x: float = 6
    inter_cell_pitch_y: float = 10

    motor_body_od: float = 4.0
    motor_body_length: float = 8.0

    gap_between_motor_layers: float = 1
    gap_above_top_motor: float = 3

    cell_count_x: int = 3
    cell_count_y: int = 1

    # TODO(KilowattSynthesis): Set these as properties
    total_x: float = 50
    total_y: float = 20
    total_z: float = 20

    def __post_init__(self) -> None:
        """Post initialization checks."""
        hypot_len = (self.motor_pitch_x**2 + self.motor_pitch_y**2) ** 0.5
        logger.info(f"Hypotenuse length: {hypot_len:.2f} mm")

        total_thickness = (
            self.motor_body_length * 2
            + self.gap_between_motor_layers
            + self.gap_above_top_motor
        )
        logger.info(f"Total thickness: {total_thickness:.2f} mm")

    def deep_copy(self) -> "HousingSpec":
        """Copy the current spec."""
        return copy.deepcopy(self)


def make_motor_placement_demo(spec: HousingSpec) -> bd.Part:
    """Make demo of motor placement."""
    p = bd.Part(None)

    # Create the motor holes.
    for dot_num, (cell_x, cell_y, dot_offset_x, dot_offset_y) in enumerate(
        product(
            evenly_space_with_center(
                count=spec.cell_count_x,
                spacing=spec.inter_cell_pitch_x,
            ),
            evenly_space_with_center(
                count=spec.cell_count_y,
                spacing=spec.inter_cell_pitch_y,
            ),
            evenly_space_with_center(count=2, spacing=spec.motor_pitch_x),
            evenly_space_with_center(count=3, spacing=spec.motor_pitch_y),
        ),
    ):
        dot_x = cell_x + dot_offset_x
        dot_y = cell_y + dot_offset_y

        layer_num = dot_num % 2  # 0 (bottom) or 1 (top)

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
                (spec.motor_body_length + spec.gap_between_motor_layers) * layer_num,
            ),
        )

        # Create the motor shaft hole.
        p += bd.Cylinder(
            radius=0.25,
            height=(
                (
                    spec.motor_body_length + spec.gap_between_motor_layers
                    if layer_num == 0
                    else 0
                )
                + (spec.motor_body_length + spec.gap_above_top_motor)
            ),
            align=bde.align.ANCHOR_BOTTOM,
        ).translate(
            (
                dot_x,
                dot_y,
                (spec.motor_body_length + spec.gap_between_motor_layers) * layer_num,
            ),
        )

    # Show where the braille dots would be.
    for cell_x, cell_y, dot_offset_x, dot_offset_y in product(
        evenly_space_with_center(
            count=spec.cell_count_x,
            spacing=spec.inter_cell_pitch_x,
        ),
        evenly_space_with_center(
            count=spec.cell_count_y,
            spacing=spec.inter_cell_pitch_y,
        ),
        evenly_space_with_center(count=2, spacing=spec.dot_pitch_x),
        evenly_space_with_center(count=3, spacing=spec.dot_pitch_y),
    ):
        dot_x = cell_x + dot_offset_x
        dot_y = cell_y + dot_offset_y

        # Create the braille dot.
        p += bd.Cylinder(
            radius=0.5,
            height=0.5,
            align=bde.align.ANCHOR_BOTTOM,
        ).translate(
            (
                dot_x,
                dot_y,
                (
                    (spec.motor_body_length * 2)
                    + spec.gap_between_motor_layers
                    + spec.gap_above_top_motor
                ),
            )
        )

    return p


if __name__ == "__main__":
    start_time = datetime.now(UTC)
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
        bd.export_stl(part, str(export_folder / f"{name}.stl"))
        bd.export_step(part, str(export_folder / f"{name}.step"))

    logger.info(f"Done running {py_file_name} in {datetime.now(UTC) - start_time}")
