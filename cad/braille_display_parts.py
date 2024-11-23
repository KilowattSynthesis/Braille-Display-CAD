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
    cell_count_y = 1

    solenoid_core_id = 1.2
    solenoid_core_height = 8  # Height of the coil.
    solenoid_core_wall_thickness = 0.26  # Match to nozzle diameter.

    base_plate_thickness = 1

    border_width = 8

    protection_wall_height = 3
    protection_wall_thickness = 1

    def __post_init__(self) -> None:
        """Post initialization checks."""
        # Amount of wire that can be wrapped around each coil.
        coil_wire_radius = (
            min(self.dot_pitch_x, self.dot_pitch_y)
            - 2 * self.solenoid_core_wall_thickness
            - self.solenoid_core_id
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


@dataclass
class SpoolSpec:
    """Specification for a spool."""

    dot_pitch: float = 2.5

    spool_core_id: float = 0.7  # A bit bigger than the 1.0mm magnets.
    spool_core_height: float = 8  # Height of the coil.
    spool_core_wall_thickness: float = 0.26  # Match to nozzle diameter.

    grip_base_diameter = 10
    grip_base_thickness = 5

    flange_diameter = 2.4  # Bit smaller than the pitch.
    flange_thickness = 1

    dist_between_flange_to_base = 2

    def __post__init__(self) -> None:
        """Post initialization checks."""
        # Amount of wire that can be wrapped around each coil.
        coil_wire_radius = (self.dot_pitch - self.spool_core_od) / 2

        logger.success(f"Coil wire radius for SpoolSpec: {coil_wire_radius:.2f} mm")

    @property
    def spool_core_od(self) -> float:
        """Outer diameter of the spool core."""
        return self.spool_core_id + 2 * self.spool_core_wall_thickness

    @property
    def total_length(self) -> float:
        """Total length, including spool, flanges, and grip base."""
        return (
            self.spool_core_height
            + 2 * self.flange_thickness
            + 2 * self.grip_base_thickness
        )


def make_solenoid_spool(spec: SpoolSpec) -> bd.Part:
    """Make a spool for the solenoid."""
    p = bd.Part()

    p += bd.Cylinder(
        spec.spool_core_od / 2,
        spec.total_length,
        align=bde.align.ANCHOR_CENTER,
    )

    for side in [1, -1]:
        # Add the flanges.
        p += bd.Cylinder(
            spec.flange_diameter / 2,
            spec.flange_thickness,
            align=bde.align.ANCHOR_CENTER,
        ).translate(
            (
                0,
                0,
                side * (spec.spool_core_height / 2 + spec.flange_thickness / 2),
            ),
        )

        # Add the grip base.
        if side == -1:
            p += bd.Cylinder(
                spec.grip_base_diameter / 2,
                spec.grip_base_thickness,
                align=bde.align.ANCHOR_CENTER,
            ).translate(
                (
                    0,
                    0,
                    side
                    * (
                        spec.spool_core_height / 2
                        + spec.flange_thickness
                        + spec.dist_between_flange_to_base
                        + spec.grip_base_thickness / 2
                    ),
                ),
            )

    # Remove the core.
    p -= bd.Cylinder(
        spec.spool_core_id / 2,
        spec.spool_core_height + spec.flange_thickness * 2 + 2,
        align=bde.align.ANCHOR_CENTER,
    )

    return p


@dataclass
class WindingAdapterSpec:
    """Specification for a winding adapter."""

    motor_shaft_length: float = 8
    motor_shaft_diameter: float = 3
    motor_shaft_wall_thickness: float = 5

    motor_gearbox_diameter: float = 16

    interface_length: float = 2

    output_diameter_max: float = 3.1
    output_diameter_min: float = 2.9
    output_length: float = 6

    key_screw_diameter: float = 3.2
    key_nut_width: float = 5.5
    key_nut_thickness: float = 2

    def __post_init__(self) -> None:
        """Post initialization checks."""
        assert self.motor_shaft_wall_thickness > 0

        assert (
            self.motor_shaft_diameter / 2 + self.motor_shaft_wall_thickness
            < self.motor_gearbox_diameter / 2
        )


def make_winding_adapter(spec: WindingAdapterSpec) -> bd.Part:
    """Make a winding adapter for straw-style jig."""
    p = bd.Part()

    # Add outside around motor.
    p += bd.Cylinder(
        radius=spec.motor_shaft_diameter / 2 + spec.motor_shaft_wall_thickness,
        height=spec.motor_shaft_length + spec.interface_length,
        align=bde.align.ANCHOR_BOTTOM,
    )

    # Remove the motor.
    p -= bd.Cylinder(
        radius=spec.motor_shaft_diameter / 2,
        height=spec.motor_shaft_length,
        align=bde.align.ANCHOR_BOTTOM,
    )

    # Add a screw key spot.
    p -= (
        bd.Cylinder(
            radius=spec.key_screw_diameter / 2,
            height=12,
            align=bde.align.ANCHOR_BOTTOM,
        )
        .rotate(axis=bd.Axis.X, angle=90)
        .translate((0, 0, spec.motor_shaft_length / 2))
    )

    # Add a nut hole.
    p -= bd.Box(
        spec.key_nut_width,
        spec.key_nut_thickness,
        spec.motor_shaft_length / 2 + 3,
        align=(bd.Align.CENTER, bd.Align.MAX, bd.Align.MIN),
    ).translate((0, -spec.motor_shaft_diameter / 2 - 1, 0))

    # Add the output shaft.
    p += bd.Cone(
        bottom_radius=spec.output_diameter_max / 2,
        top_radius=spec.output_diameter_min / 2,
        height=spec.output_length,
        align=bde.align.ANCHOR_BOTTOM,
    ).translate((0, 0, spec.motor_shaft_length + spec.interface_length))

    return p


if __name__ == "__main__":
    parts = {
        "base_plate": show(make_base_plate(BasePlateSpec())),
        "spool_0p7mm_id": show(make_solenoid_spool(SpoolSpec(spool_core_id=0.7))),
        "spool_1p0mm_id": show(make_solenoid_spool(SpoolSpec(spool_core_id=1.0))),
        "winding_adapter": show(make_winding_adapter(WindingAdapterSpec())),
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
