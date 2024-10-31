"""Create CAD models for the braille display parts.

BOM:
- M1.6 Nuts
- M1.6 x 6mm grub screws

Future options:
- Try M1.4 x 6mm grub screws and nuts for a little better fit.
- Try creating the nut holder so it's a smooth surface on the top.

"""

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import build123d as bd
import build123d_ease as bde
from loguru import logger

if os.getenv("CI"):

    def show(*args: object) -> bd.Part:
        """Do nothing (dummy function) to skip showing the CAD model in CI."""
        logger.info(f"Skipping show({args}) in CI")
        return args[0]
else:
    import ocp_vscode

    def show(*args: object) -> bd.Part:
        """Show the CAD model in the CAD viewer."""
        ocp_vscode.show(*args)
        return args[0]


# Constants. All distances are in mm.

# Core braille cell dimensions.
inter_cell_dot_pitch_x = 6.2  # 6.1 to 7.6, with 6.2 nominal in printing
inter_cell_dot_pitch_y = 10.0
dot_diameter_base = 1.6
dot_diameter_top = 1.2
dot_height = 0.8

# Housing dimensions.
min_wall_thickness = 1.0
housing_roof_thickness = 1.0
# Thickness of the part that holds the spring and routes the string.
housing_basement_thickness = 0
lock_plate_thickness = 1.0  # <- This is the cool part that locks the dots.
housing_cable_channel_od = 1
housing_mounting_screw_od = 2.2
housing_mounting_screw_sep_y = 10.1


@dataclass
class Nut:
    """Dimensions for any nut."""

    width: float
    thickness: float
    m_diameter: float


m2p5_nut = Nut(width=4.9, thickness=1.8, m_diameter=2.5)
m1p6_nut = Nut(width=3.1, thickness=1.2, m_diameter=1.6)


@dataclass
class NutHolder:
    """Dimensions and generator for the nut holder."""

    nut: Nut

    # Whether the bottom-most nut should be placed with its opening facing the top or
    # bottom. For all nuts on the same side, the opening should face "top".
    nut_from_top_or_bottom: Literal["top", "bottom"] = "top"

    # Separation between nuts in the Z direction.
    # Set to 0 if `nut_from_top_or_bottom == "top"`.
    separation_between_nuts_z: float = 0

    # Set to 0 if `nut_from_top_or_bottom == "bottom"`.
    bottom_thickness: float = 1
    top_thickness_above_nut: float = 0

    border_thickness_xy: float = 10

    dot_separation_x = 2.5
    dot_separation_y = 2.5
    dot_x_count: int = 2
    dot_y_count: int = 3

    cell_count_x: int = 8
    cell_count_y: int = 2

    nut_rotate_z: float = 15  # 0-30 is the range. Half that fits magically.

    screw_extra_diameter: float = 0.2

    # mount_screw_d: float = 3.2
    # mount_screw_standoff_d: float = 6

    @property
    def min_max_x_dot_center(self) -> tuple[float, float]:
        """Get the min and max x values for the dot centers."""
        return (
            min(x[0] for x in self.dot_centers),
            max(x[0] for x in self.dot_centers),
        )

    @property
    def min_max_y_dot_center(self) -> tuple[float, float]:
        """Get the min and max y values for the dot centers."""
        return (
            min(x[1] for x in self.dot_centers),
            max(x[1] for x in self.dot_centers),
        )

    @property
    def total_width(self) -> float:
        """Total width of the nut holder."""
        return self.border_thickness_xy * 2 + (
            self.min_max_x_dot_center[1] - self.min_max_x_dot_center[0]
        )

    @property
    def total_height(self) -> float:
        """Total height of the nut holder."""
        return self.border_thickness_xy * 2 + (
            self.min_max_y_dot_center[1] - self.min_max_y_dot_center[0]
        )

    @property
    def total_thickness(self) -> float:
        """Total thickness of the nut holder."""
        return (
            self.bottom_thickness
            + self.top_thickness_above_nut
            + self.separation_between_nuts_z
            + 2 * self.nut.thickness
        )

    @property
    def cell_centers(self) -> list[tuple[float, float]]:
        """Get the centers of the cells."""
        return [
            (
                inter_cell_dot_pitch_x * (x_num - (self.cell_count_x - 1) / 2),
                inter_cell_dot_pitch_y * (y_num - (self.cell_count_y - 1) / 2),
            )
            for y_num in range(self.cell_count_y)
            for x_num in range(self.cell_count_x)
        ]

    @property
    def dot_centers(self) -> list[tuple[float, float, int]]:
        """Get the centers of the dots.

        Returns a list of (x, y, dot_num) tuples.
        """
        dot_nums = [
            (-0.5, -1, 1),
            (-0.5, 0, 2),
            (-0.5, 1, 3),
            (0.5, -1, 4),
            (0.5, 0, 5),
            (0.5, 1, 6),
        ]
        return [
            (
                self.dot_separation_x * x + cell_coord[0],
                self.dot_separation_y * y + cell_coord[1],
                dot_num,
            )
            for x, y, dot_num in dot_nums
            for cell_coord in self.cell_centers
        ]

    def validate(self) -> None:
        """Validate the dimensions."""
        assert self.min_max_x_dot_center[1] == -self.min_max_x_dot_center[0]
        assert self.min_max_y_dot_center[1] == -self.min_max_y_dot_center[0]

        assert self.total_width > 0
        assert self.total_height > 0
        assert self.total_thickness > 0

        data = {
            "total_width": self.total_width,
            "total_height": self.total_height,
            "total_thickness": self.total_thickness,
            # "cell_centers": self.cell_centers,
            # "dot_centers": self.dot_centers,
        }

        logger.success(f"Dimensions validated: {json.dumps(data, indent=4)}")

    def make_part(self) -> bd.Part:
        """Make the nut holder part."""
        self.validate()

        p = bd.Part()

        # Make the body.
        p += bd.Box(
            self.total_width,
            self.total_height,
            self.total_thickness,
        )

        box_bottom_z = bde.bottom_face_of(p).center().Z

        # Make the nuts.
        for x, y, dot_num in self.dot_centers:
            nut_center_z = (
                box_bottom_z + self.bottom_thickness + (self.nut.thickness / 2)
            )
            rotate_nut_direction = 0

            if dot_num % 2 == 0:
                nut_center_z += self.nut.thickness + self.separation_between_nuts_z
            elif self.nut_from_top_or_bottom == "bottom":
                rotate_nut_direction = 180

            # Remove the nut.
            p -= (
                bd.extrude(
                    bd.RegularPolygon(
                        radius=self.nut.width / 2,
                        side_count=6,
                        major_radius=False,
                    ),
                    amount=self.total_thickness * 2,  # Extrude it through the brick.
                )
                .translate((0, 0, -self.nut.thickness / 2))  # Center the nut.
                .rotate(axis=bd.Axis.Z, angle=self.nut_rotate_z)
                .rotate(axis=bd.Axis.X, angle=rotate_nut_direction)
                .translate((x, y, nut_center_z))
            )

            # Remove the screw hole.
            p -= (
                bd.Cylinder(
                    radius=(self.nut.m_diameter + self.screw_extra_diameter) / 2,
                    height=self.total_thickness * 2.5,  # Extrude it through the brick.
                )
                .rotate(axis=bd.Axis.X, angle=rotate_nut_direction)
                .translate((x, y, nut_center_z))
            )

        return p


##############################
##### CALCULATED VALUES ######
##############################


if __name__ == "__main__":
    parts = {
        "nut_holder_M1p6_From_Top": (
            NutHolder(
                nut=m1p6_nut,
            ).make_part()
        ),
        "nut_holder_M1p6_From_Bottom": show(
            NutHolder(
                nut=m1p6_nut,
                nut_from_top_or_bottom="bottom",
                separation_between_nuts_z=1,
                bottom_thickness=0,
            ).make_part()
        ),
    }

    logger.info("Showing CAD model(s)")

    (export_folder := Path(__file__).parent.with_name("build")).mkdir(exist_ok=True)
    for name, part in parts.items():
        assert isinstance(part, bd.Part), f"{name} is not a Part"
        # assert part.is_manifold is True, f"{name} is not manifold"

        bd.export_stl(part, str(export_folder / f"{name}.stl"))
        bd.export_step(part, str(export_folder / f"{name}.step"))
