"""Create a braille display base plate."""

from dataclasses import dataclass
from pathlib import Path

import build123d as bd
import build123d_ease as bde
from build123d_ease import show
from loguru import logger


@dataclass
class WindingAdapterSpec:
    """Specification for a winding adapter."""

    motor_shaft_length: float = 8
    motor_shaft_diameter: float = 3
    motor_shaft_wall_thickness: float = 5

    motor_gearbox_diameter: float = 16

    interface_length: float = 2

    output_diameter_max: float = 3.9
    output_diameter_min: float = 3.2
    output_length: float = 7

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
    p = bd.Part(None)

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
        "winding_adapter": show(make_winding_adapter(WindingAdapterSpec())),
    }

    logger.info("Showing CAD model(s)")

    (
        export_folder := Path(__file__).parent.parent / "build" / Path(__file__).stem
    ).mkdir(
        exist_ok=True,
        parents=True,
    )
    for name, part in parts.items():
        bd.export_stl(part, str(export_folder / f"{name}.stl"))
        bd.export_step(part, str(export_folder / f"{name}.step"))
