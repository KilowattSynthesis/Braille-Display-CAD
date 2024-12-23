"""Using a layer of screws (like the `cnc_plotter` branch), make motor holder.

Intended as a proof of concept to see how the motors can fit.

Conclusion: At 2.5mm pitch, Motor OD=4mm, H=8mm motors can't really fit.

Conclusion: At 3mm pitch though, Motor OD=4mm, H=8mm motors can totally fit! Just need
to bend their shafts a bit to make them mate with the screws!
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
    cell_pitch_x: float = 6
    cell_pitch_y: float = 10

    motor_body_od: float = 4.0
    motor_body_length: float = 8.0

    # The distance above the top of the motor to not allow the bending `turner_tube`.
    # Best to keep slightly greater than `gap_between_motor_layers`.
    motor_rigid_shaft_len: float = 3

    gap_between_motor_layers: float = 2
    gap_above_top_motor: float = 5

    cell_count_x: int = 4
    cell_count_y: int = 1

    wire_channel_slot_width: float = 1.5

    # `turner_tube` goes to the surface and connects motor to the dot bolt.
    turner_tube_od: float = 1.4

    total_y: float = 15

    # Distance from outer dots to mounting holes. PCB property.
    x_dist_dots_to_mounting_holes: float = 5.0

    mounting_hole_spacing_y: float = 3
    mounting_hole_diameter: float = 2  # Thread-forming screws from bottom.

    border_x: float = 5

    @property
    def dist_between_motor_walls(self) -> float:
        """Distance between motor walls in a layer."""
        return self.motor_pitch_x * 2 - self.motor_body_od

    @property
    def mounting_hole_spacing_x(self) -> float:
        """Spacing between the mounting holes, in X axis."""
        return (
            self.x_dist_dots_to_mounting_holes * 2
            + self.cell_pitch_x * (self.cell_count_x - 1)
            + self.dot_pitch_x
        )

    @property
    def total_x(self) -> float:
        """Total width of the braille housing."""
        return (
            self.mounting_hole_spacing_x
            + self.mounting_hole_diameter
            + self.border_x * 2
        )

    @property
    def total_z(self) -> float:
        """Total thickness of the housing."""
        return (
            self.motor_body_length * 2
            + self.gap_between_motor_layers
            + self.gap_above_top_motor
        )

    def __post_init__(self) -> None:
        """Post initialization checks."""
        hypot_len = (self.motor_pitch_x**2 + self.motor_pitch_y**2) ** 0.5

        data = {
            "hypot_len": hypot_len,
            "total_x": self.total_x,
            "total_y": self.total_y,
            "total_z": self.total_z,
            "dist_between_motor_walls": self.dist_between_motor_walls,
        }

        logger.info(json.dumps(data, indent=2))

    def deep_copy(self) -> "HousingSpec":
        """Copy the current spec."""
        return copy.deepcopy(self)


def make_motor_placement_demo(spec: HousingSpec) -> bd.Part:
    """Make demo of motor placement."""
    p = bd.Part(None)

    # Create the motor holes.
    for dot_num, (cell_x, cell_y, offset_x, offset_y) in enumerate(
        product(
            evenly_space_with_center(
                count=spec.cell_count_x,
                spacing=spec.cell_pitch_x,
            ),
            evenly_space_with_center(
                count=spec.cell_count_y,
                spacing=spec.cell_pitch_y,
            ),
            evenly_space_with_center(count=2, spacing=1),
            evenly_space_with_center(count=3, spacing=1),
        ),
    ):
        motor_x = cell_x + offset_x * spec.motor_pitch_x
        motor_y = cell_y + offset_y * spec.motor_pitch_x

        layer_num = dot_num % 2  # 0 (bottom) or 1 (top)

        # Create the motor hole.
        p += bd.Cylinder(
            spec.motor_body_od / 2,
            # Add a tiny random amount so you can see the edges clearer.
            spec.motor_body_length + random.random() * 0.2,
            align=bde.align.ANCHOR_BOTTOM,
        ).translate(
            (
                motor_x,
                motor_y,
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
                motor_x,
                motor_y,
                (spec.motor_body_length + spec.gap_between_motor_layers) * layer_num,
            ),
        )

    # Show where the braille dots would be.
    for cell_x, cell_y, offset_x, offset_y in product(
        evenly_space_with_center(
            count=spec.cell_count_x,
            spacing=spec.cell_pitch_x,
        ),
        evenly_space_with_center(
            count=spec.cell_count_y,
            spacing=spec.cell_pitch_y,
        ),
        evenly_space_with_center(count=2, spacing=spec.dot_pitch_x),
        evenly_space_with_center(count=3, spacing=spec.dot_pitch_y),
    ):
        motor_x = cell_x + offset_x
        motor_y = cell_y + offset_y

        # Create the braille dot.
        p += bd.Cylinder(
            radius=0.5,
            height=0.5,
            align=bde.align.ANCHOR_BOTTOM,
        ).translate(
            (
                motor_x,
                motor_y,
                (
                    (spec.motor_body_length * 2)
                    + spec.gap_between_motor_layers
                    + spec.gap_above_top_motor
                ),
            )
        )

    return p


def make_motor_housing(spec: HousingSpec) -> bd.Part:
    """Make housing with the placement from the demo."""
    p = bd.Part(None)

    p += bd.Box(
        spec.total_x,
        spec.total_y,
        spec.total_z,
        align=bde.align.ANCHOR_BOTTOM,
    )

    # Create the motor holes.
    for dot_num, (cell_x, cell_y, offset_x, offset_y) in enumerate(
        product(
            evenly_space_with_center(
                count=spec.cell_count_x,
                spacing=spec.cell_pitch_x,
            ),
            evenly_space_with_center(
                count=spec.cell_count_y,
                spacing=spec.cell_pitch_y,
            ),
            evenly_space_with_center(count=2, spacing=1),
            evenly_space_with_center(count=3, spacing=1),
        ),
    ):
        motor_x = cell_x + offset_x * spec.motor_pitch_x
        motor_y = cell_y + offset_y * spec.motor_pitch_y
        dot_x = cell_x + offset_x * spec.dot_pitch_x
        dot_y = cell_y + offset_y * spec.dot_pitch_y

        layer_num = dot_num % 2  # 0 (bottom) or 1 (top)

        # Create the motor hole.
        p -= bd.Cylinder(
            spec.motor_body_od / 2,
            (
                spec.motor_body_length
                if layer_num == 0
                # Make it stick out on the top
                else spec.motor_body_length + spec.gap_above_top_motor + 1
            ),
            align=bde.align.ANCHOR_BOTTOM,
        ).translate(
            (
                motor_x,
                motor_y,
                (spec.motor_body_length + spec.gap_between_motor_layers) * layer_num,
            ),
        )

        # Remove the hole for the wires.
        if layer_num == 1:  # Top only.
            # In gap.
            p -= bd.extrude(
                bd.SlotCenterToCenter(
                    center_separation=spec.motor_body_od - spec.wire_channel_slot_width,
                    height=spec.wire_channel_slot_width,
                ),
                amount=spec.gap_between_motor_layers,
            ).translate(
                (
                    motor_x,
                    motor_y,
                    spec.motor_body_length + spec.gap_between_motor_layers / 2,
                )
            )

            # Through to bottom.
            p -= bd.extrude(
                bd.Circle(
                    radius=spec.wire_channel_slot_width / 2,
                ),
                amount=spec.motor_body_length + spec.gap_between_motor_layers,
            ).translate((motor_x, motor_y, 0))

        # Create the turner_tube hole, with passage right to the dot.
        if layer_num == 0:  # Bottom only.
            p -= bd.extrude(
                bd.make_hull(
                    bd.Circle(
                        radius=spec.turner_tube_od / 2,
                    )
                    .translate((motor_x, motor_y))
                    .edges()
                    # ----
                    + bd.Circle(
                        radius=spec.turner_tube_od / 2,
                    )
                    .translate((dot_x, dot_y))
                    .edges()
                ),
                amount=spec.motor_body_length + spec.gap_between_motor_layers,
            ).translate((0, 0, spec.motor_body_length + spec.motor_rigid_shaft_len))

            # Bottom part is just a cylinder, from top of bottom motor,
            # up `spec.motor_body_length` amount into/past the gap_between_motor_layers.
            p -= bd.extrude(
                bd.Circle(
                    radius=spec.turner_tube_od / 2,
                ),
                amount=spec.motor_rigid_shaft_len + 0.01,
            ).translate((motor_x, motor_y, spec.motor_body_length))

    # Subtract the mounting holes.
    for hole_x, hole_y in product(
        evenly_space_with_center(count=2, spacing=spec.mounting_hole_spacing_x),
        evenly_space_with_center(count=3, spacing=spec.mounting_hole_spacing_y),
    ):
        p -= bd.Cylinder(
            spec.mounting_hole_diameter / 2,
            spec.total_z,
            align=bde.align.ANCHOR_BOTTOM,
        ).translate((hole_x, hole_y, 0))

    # Subtract the gap_above_top_motor.
    p -= bd.Box(
        spec.mounting_hole_spacing_x - spec.mounting_hole_diameter - 3,
        spec.total_y,
        spec.gap_above_top_motor,
        align=bde.align.ANCHOR_BOTTOM,
    ).translate((0, 0, spec.motor_body_length * 2 + spec.gap_between_motor_layers))

    return p


def write_milling_drawing_info(
    spec: HousingSpec, *, include_each_dot: bool = False
) -> str:
    """Write information for how to mill the housing."""
    lines: list[str] = []
    section_break = ["", "=" * 80, ""]

    lines.extend(
        [
            "Braille display milling machine plate dimensions:",
            "",
            "Cut stock to size:",
            f"  Housing total X: {spec.total_x}",
            f"  Housing total Y: {spec.total_y}",
            f"  Housing total Z: {spec.total_z} (not used for milling)",
            "  Stock thickness: 2mm-3mm is probably best.",
            "",
            f"Dot pitch X: {spec.dot_pitch_x}",
            f"Dot pitch Y: {spec.dot_pitch_y}",
            f"Cell pitch X: {spec.cell_pitch_x}",
            f"Cell pitch Y: {spec.cell_pitch_y}",
            f"Cell count X: {spec.cell_count_x}",
            f"Cell count Y: {spec.cell_count_y}",
            f"Total dots: {spec.cell_count_x * spec.cell_count_y * 6}",
            "",
            f"Mounting hole pitch X (2 positions): {spec.mounting_hole_spacing_x}",
            f"Mounting hole pitch Y (3 positions): {spec.mounting_hole_spacing_y}",
            "",
            "Make center of it all be at (0, 0).",
            *section_break,
        ]
    )

    # Mounting hole positions.
    hole_positions = list(
        product(
            evenly_space_with_center(count=2, spacing=spec.mounting_hole_spacing_x),
            evenly_space_with_center(count=3, spacing=spec.mounting_hole_spacing_y),
        )
    )
    lines.extend(
        [
            "Mounting hole positions (X, Y):",
            f"  Diameter: {spec.mounting_hole_diameter}",
            "",
        ]
    )
    for hole_num, (hole_x, hole_y) in enumerate(hole_positions):
        lines.extend(
            [
                f"Mounting hole {hole_num + 1} position:",
                f"  X: {hole_x}",
                f"  Y: {hole_y}",
                "",
            ]
        )

    lines.extend(section_break)

    dot_positions: list[tuple[float, float]] = []
    for cell_x, cell_y, offset_x, offset_y in product(
        evenly_space_with_center(
            count=spec.cell_count_x,
            spacing=spec.cell_pitch_x,
        ),
        evenly_space_with_center(
            count=spec.cell_count_y,
            spacing=spec.cell_pitch_y,
        ),
        evenly_space_with_center(count=2, spacing=1),
        evenly_space_with_center(count=3, spacing=1),
    ):
        dot_x = cell_x + offset_x * spec.dot_pitch_x
        dot_y = cell_y + offset_y * spec.dot_pitch_y
        dot_positions.append((dot_x, dot_y))

    lines.extend(
        [
            "Dot hole positions (X, Y):",
            "  For M1.6 tap, drill 1.25mm hole [do this].",
            "  For M1.4 tap, drill 1.1mm hole.",
            "  For other sizes, see https://fullerfasteners.com/tech/recommended-tapping-drill-size/.",
            "",
        ]
    )

    if include_each_dot:
        for dot_num, (dot_x, dot_y) in enumerate(dot_positions):
            lines.extend(
                [
                    f"Dot {dot_num + 1} position:",
                    f"  X: {dot_x}",
                    f"  Y: {dot_y}",
                    "",
                ]
            )

        lines.extend(section_break)

    # All dot X positions.
    dot_x_positions: list[float] = sorted({dot_x for dot_x, _ in dot_positions})
    dot_y_positions: list[float] = sorted({dot_y for _, dot_y in dot_positions})
    lines.append("Dot X positions:")
    lines.extend(f"  {dot_x}\n" for dot_x in dot_x_positions)
    lines.append("")

    lines.extend(section_break)

    # All dot Y positions.
    lines.append("Dot Y positions:")
    lines.extend(f"  {dot_y}\n" for dot_y in dot_y_positions)
    lines.extend(["", ""])

    return "\n".join(lines)


if __name__ == "__main__":
    start_time = datetime.now(UTC)
    py_file_name = Path(__file__).name
    logger.info(f"Running {py_file_name}")

    parts = {
        "motor_placement_demo": show(make_motor_placement_demo(HousingSpec())),
        "motor_housing": show(make_motor_housing(HousingSpec())),
    }

    logger.info("Showing CAD model(s)")

    (
        export_folder := Path(__file__).parent.parent / "build" / Path(__file__).stem
    ).mkdir(exist_ok=True, parents=True)
    for name, part in parts.items():
        bd.export_stl(part, str(export_folder / f"{name}.stl"))
        bd.export_step(part, str(export_folder / f"{name}.step"))

    (export_folder / "milling_drawing_info.txt").write_text(
        write_milling_drawing_info(HousingSpec())
    )

    logger.info(f"Done running {py_file_name} in {datetime.now(UTC) - start_time}")
