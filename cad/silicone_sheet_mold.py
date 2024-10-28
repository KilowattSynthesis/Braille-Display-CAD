"""Silicone sheet mold CAD model."""

import itertools
import json
import os
from pathlib import Path

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


# region Constants
crazy_scale_factor = 1  # Normally 1x, but 2x is good for FDM testing.
# Core braille cell dimensions.
dot_separation_x = 2.5 * crazy_scale_factor
dot_separation_y = 2.5 * crazy_scale_factor
dot_x_count = 2
dot_y_count = 3
inter_cell_dot_pitch_x = (
    # 6.1 to 7.6, with 6.2 nominal in printing.
    6.4 * crazy_scale_factor
)
inter_cell_dot_pitch_y = 10.0 * crazy_scale_factor
# dot_diameter_base = 1.6
# dot_diameter_top = 1.2
# dot_height = 0.8

cell_count_x = 3
cell_count_y = 1

sheet_border = 10
sheet_thickness = 0.3

dome_od = 1.9 * crazy_scale_factor
dome_thickness = 0.4

mold_plate_t = 5
mold_side_wall_t = 6
mold_screw_d = 3.2
mold_screw_standoff_od = 6
mold_screw_margin = 4
# end region

# region Calculated dimensions
cell_centers: list[tuple[float, float]] = [
    (
        inter_cell_dot_pitch_x * (x_num - (cell_count_x - 1) / 2),
        inter_cell_dot_pitch_y * (y_num - (cell_count_y - 1) / 2),
    )
    for y_num in range(cell_count_y)
    for x_num in range(cell_count_x)
]

dot_centers: list[tuple[float, float]] = [
    (
        dot_separation_x * x + cell_coord[0],
        dot_separation_y * y + cell_coord[1],
    )
    for y in [-1, 0, 1]
    for x in [-0.5, 0.5]
    for cell_coord in cell_centers
]

min_dot_x = min(x for x, _ in dot_centers)
max_dot_x = max(x for x, _ in dot_centers)
min_dot_y = min(y for _, y in dot_centers)
max_dot_y = max(y for _, y in dot_centers)

sheet_width_x = max_dot_x - min_dot_x + 2 * sheet_border
sheet_height_y = max_dot_y - min_dot_y + 2 * sheet_border

mold_width_x = sheet_width_x + 2 * mold_side_wall_t
mold_width_y = sheet_height_y + 2 * mold_side_wall_t
# end region


def validate() -> None:
    """Raise if variables are not valid."""
    assert len(cell_centers) == cell_count_x * cell_count_y
    assert len(dot_centers) == cell_count_x * cell_count_y * dot_x_count * dot_y_count

    # Ensure cells are centered. Makes lots of math easier.
    assert min_dot_x == -max_dot_x
    assert min_dot_y == -max_dot_y

    data = {
        "sheet_width_x": sheet_width_x,
        "sheet_height_y": sheet_height_y,
    }

    logger.success(f"Data: {json.dumps(data, indent=4)}")


def make_silicone_sheet_positive() -> bd.Part:
    """Make the positive silicone sheet."""
    p = bd.Part()

    p += bd.Box(
        sheet_width_x,
        sheet_height_y,
        sheet_thickness,
    ).translate(
        early_translation := (
            (max_dot_x + min_dot_x) / 2,
            (max_dot_y + min_dot_y) / 2,
            0,
        ),
    )

    # Create a generic bump.
    bump = (
        bd.Part()
        + bd.Sphere(dome_od / 2)
        - bd.Sphere(radius=dome_od / 2 - dome_thickness)
        - bd.Box(10, 10, 10, align=bde.align.TOP)
    )

    for dot_x, dot_y in dot_centers:
        # Remove the dot.
        p -= bd.Cylinder(
            radius=dome_od / 2,
            height=sheet_thickness * 10,
        ).translate((dot_x, dot_y, 0))

        # Create a bump there.
        p += bump.translate((dot_x, dot_y, 0))

    p = p.translate((-early_translation[0], -early_translation[1], 0))

    return p


def make_mold_bottom() -> bd.Part:
    """Make the top part of the mold."""
    p = bd.Part()

    p += bd.Box(
        mold_width_x,
        mold_width_y,
        mold_plate_t + sheet_thickness,
        align=bde.align.TOP,
    )

    # Must fully fill the dots.
    for dot_x, dot_y in dot_centers:
        # Note: division-by-3 is a bit of a hack.
        p += bd.Sphere(dome_od / 3).translate((dot_x, dot_y, 0))

    # Remove the silicone sheet.
    sheet = make_silicone_sheet_positive()
    p -= sheet.translate((0, 0, -sheet.bounding_box().min.Z - sheet_thickness))

    # Bolt holes.
    for x, y in itertools.product([1, -1], [1, -1]):
        p -= bd.Cylinder(
            radius=mold_screw_d / 2,
            height=20,
        ).translate(
            (
                x * (mold_width_x / 2 - mold_screw_margin),
                y * (mold_width_y / 2 - mold_screw_margin),
                0,
            ),
        )

    return p


def make_mold_top() -> bd.Part:
    """Make the top part of the mold."""
    p = bd.Part()

    p += bd.Box(
        sheet_width_x + 2 * mold_side_wall_t,
        sheet_height_y + 2 * mold_side_wall_t,
        mold_plate_t + sheet_thickness,
        align=bde.align.BOTTOM,
    )

    p -= make_mold_bottom()

    # Remove the silicone sheet.
    sheet = make_silicone_sheet_positive()
    p -= sheet.translate((0, 0, -sheet.bounding_box().min.Z - sheet_thickness))

    # Bolt holes.
    for x, y in itertools.product([1, -1], [1, -1]):
        p -= bd.Cylinder(
            radius=mold_screw_d / 2,
            height=20,
        ).translate(
            (
                x * (mold_width_x / 2 - mold_screw_margin),
                y * (mold_width_y / 2 - mold_screw_margin),
                0,
            ),
        )

    # Remove pouring/venting holes.
    for y in [1, -1]:
        p -= bd.Cylinder(
            radius=1.5,
            height=20,
        ).translate(
            (
                0,
                y * (sheet_height_y / 2 - 3),
                0,
            ),
        )

    return p


if __name__ == "__main__":
    validate()

    logger.info("Showing CAD model(s)")
    parts = {
        "silicone_sheet_positive": show(make_silicone_sheet_positive()),
        "mold_bottom": show(make_mold_bottom()),
        "mold_top": (make_mold_top()),
    }

    logger.info(f"Done showing {len(parts)} part(s)")

    (export_folder := Path(__file__).parent.parent / "build/silicone_sheet").mkdir(
        exist_ok=True,
        parents=True,
    )
    for name, part in parts.items():
        assert isinstance(part, bd.Part), f"{name} is not a Part"
        # assert part.is_manifold is True, f"{name} is not manifold"

        bd.export_stl(part, str(export_folder / f"{name}.stl"))
        bd.export_step(part, str(export_folder / f"{name}.step"))
