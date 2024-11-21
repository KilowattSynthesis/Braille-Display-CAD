"""Create a braille display base plate."""

from dataclasses import dataclass
from itertools import product
from pathlib import Path

import build123d as bd
import build123d_ease as bde
from build123d_ease import show
from loguru import logger


def evenly_space_with_center(
    center: float = 0,
    *,
    count: int,
    spacing: float,
) -> list[float]:
    """Evenly space `count` items around `center` with `spacing`."""
    half_spacing = (count - 1) * spacing / 2
    return [center - half_spacing + i * spacing for i in range(count)]


@dataclass
class BasePlateSpec:
    """Specification for part1."""

    # Core braille cell dimensions.
    dot_pitch_x = 2.5
    dot_pitch_y = 2.5
    dot_count_x = 2
    dot_count_y = 3
    cell_pitch_x = 6
    cell_pitch_y = 10.0

    cell_count_x = 4
    cell_count_y = 2

    solenoid_core_id = 0.7
    solenoid_core_height = 8  # Height of the coil.
    solenoid_core_wall_thickness = 0.2  # Match to nozzle diameter.

    base_plate_thickness = 2

    border_width = 10

    protection_wall_height = 10
    protection_wall_thickness = 2

    def __post_init__(self) -> None:
        """Post initialization checks."""
        # Amount of wire that can be wrapped around each coil.
        coil_wire_radius = (
            min(self.dot_pitch_x, self.dot_pitch_y)
            - 2 * self.solenoid_core_wall_thickness
        ) / 2

        logger.success(f"Coil wire radius: {coil_wire_radius:.2f} mm")

    @property
    def solenoid_core_od(self) -> float:
        """Outer diameter of the solenoid core."""
        return self.solenoid_core_id + 2 * self.solenoid_core_wall_thickness

    @property
    def total_x(self) -> float:
        """Total width of the base plate."""
        return (
            self.dot_pitch_x * self.dot_count_x
            + self.cell_pitch_x * (self.cell_count_x - 1)
            + self.border_width
        )

    @property
    def total_y(self) -> float:
        """Total height of the base plate."""
        return (
            self.dot_pitch_y * self.dot_count_y
            + self.cell_pitch_y * (self.cell_count_y - 1)
            + self.border_width
        )


def make_base_plate(spec: BasePlateSpec) -> bd.Part:
    """Create a CAD model of part1."""
    p = bd.Part()

    p += bd.Box(
        spec.total_x,
        spec.total_y,
        spec.base_plate_thickness,
        align=bde.align.ANCHOR_BOTTOM,
    )

    for cell_x, cell_y in product(
        evenly_space_with_center(count=spec.cell_count_x, spacing=spec.cell_pitch_x),
        evenly_space_with_center(count=spec.cell_count_y, spacing=spec.cell_pitch_y),
    ):
        for dot_x, dot_y in product(
            evenly_space_with_center(
                center=cell_x,
                count=spec.dot_count_x,
                spacing=spec.dot_pitch_x,
            ),
            evenly_space_with_center(
                center=cell_y,
                count=spec.dot_count_y,
                spacing=spec.dot_pitch_y,
            ),
        ):
            p += bd.Cylinder(
                spec.solenoid_core_od / 2,
                spec.solenoid_core_height,
                align=bde.align.ANCHOR_BOTTOM,
            ).translate((dot_x, dot_y, spec.base_plate_thickness))

            # Remove iron core.
            p -= bd.Cylinder(
                spec.solenoid_core_id / 2,
                spec.solenoid_core_height + spec.base_plate_thickness,
                align=bde.align.ANCHOR_BOTTOM,
            ).translate((dot_x, dot_y, spec.base_plate_thickness))

    # Add protection walls.
    p += bd.Box(
        spec.total_x,
        spec.total_y,
        spec.base_plate_thickness + spec.protection_wall_height,
        align=bde.align.ANCHOR_BOTTOM,
    ) - bd.Box(
        spec.total_x - 2 * spec.protection_wall_thickness,
        spec.total_y - 2 * spec.protection_wall_thickness,
        spec.base_plate_thickness + spec.protection_wall_height,
        align=bde.align.ANCHOR_BOTTOM,
    )

    return p


if __name__ == "__main__":
    parts = {
        "base_plate": show(make_base_plate(BasePlateSpec())),
    }

    logger.info("Showing CAD model(s)")

    (export_folder := Path(__file__).parent.parent / "build/solenoid_base").mkdir(
        exist_ok=True,
        parents=True,
    )
    for name, part in parts.items():
        assert isinstance(part, bd.Part), f"{name} is not a Part"
        # assert part.is_manifold is True, f"{name} is not manifold"

        bd.export_stl(part, str(export_folder / f"{name}.stl"))
        bd.export_step(part, str(export_folder / f"{name}.step"))
