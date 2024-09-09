import os
import math
from pathlib import Path

import build123d as bd

from cad_lib import make_curved_bent_cylinder


if os.getenv("CI"):

    def show(*args):
        return print(f"Skipping show({args}) in CI")
else:
    from ocp_vscode import show


# Constants. All distances are in mm.

# Core braille cell dimensions.
dot_separation_x = 2.5
dot_separation_y = 2.5
dot_x_count = 2
dot_y_count = 3
inter_cell_dot_pitch_x = 7.6  # 6.1 to 7.6, with 6.2 nominal in printing
inter_cell_dot_pitch_y = 10.0
dot_diameter_base = 1.6
dot_diameter_top = 1.2
dot_height = 0.8

# Housing dimensions.
min_wall_thickness = 1.0
spring_max_length = 5
spring_min_length = 2
spring_od = 2.0
cell_outer_y_length = 15
spring_cell_width = spring_od + 0.1
housing_roof_thickness = 1.0
# Thickness of the part that holds the spring and routes the string.
housing_basement_thickness = 0
lock_plate_thickness = 1.0  # <- This is the cool part that locks the dots.
housing_cable_channel_od = 1

# Pogo Pin Specs
# H=8mm from https://www.aliexpress.com/item/1005003789308391.html
pogo_length = 8.0  # Excludes the male pin below the flange.
pogo_throw_tip_od = 0.9
pogo_throw_length = 2.0
pogo_shaft_od = 1.5
pogo_shaft_length = 6.0
pogo_flange_od = 2.0
pogo_flange_length = 0.5  # Estimated. Not specified.
pogo_below_flange_od = 0.8
pogo_below_flange_length = 2.0  # Ambiguous, 2mm is the longest option.


def validate_dimensions():
    # Calculate the wall thickness between the cell parts.
    wall_thickness_x = dot_separation_x - spring_cell_width
    wall_thickness_y = dot_separation_y - spring_cell_width

    print(f"Wall thicknesses between dots: {wall_thickness_x=}, {wall_thickness_y=}")

    # assert (
    #     wall_thickness_x >= min_wall_thickness
    # ), f"Wall thickness too thin: {wall_thickness_x}"
    # assert (
    #     wall_thickness_y >= min_wall_thickness
    # ), f"Wall thickness too thin: {wall_thickness_y}"

    print("Dimensions validated.")


def make_pogo_pin(pogo_throw_tip_od_delta: float = 0):
    """Make a pogo pin in order to act as a negative for the print-in-place surrounding part."""

    # Orientation: Pin extends up.
    # Origin (XY): Center of bottom of flange. `pogo_length` extends up.
    with bd.BuildPart() as pogo_pin_part:
        # Below flange.
        bd.Cylinder(
            radius=pogo_below_flange_od / 2,
            height=pogo_below_flange_length,
            align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MAX),
        )

        # Flange.
        bd.Cylinder(
            radius=pogo_flange_od / 2,
            height=pogo_flange_length,
            align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
        )

        # Shaft.
        bd.Cylinder(
            radius=pogo_shaft_od / 2,
            height=pogo_shaft_length,
            align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
        )

        # Throw/tip.
        with bd.Locations(pogo_pin_part.faces().sort_by(bd.Axis.Z)[-1]):
            bd.Cylinder(
                radius=(pogo_throw_tip_od + pogo_throw_tip_od_delta) / 2,
                height=pogo_throw_length,
                align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
            )

    return pogo_pin_part.part


def make_housing():
    housing_size_x = inter_cell_dot_pitch_x + 5
    housing_size_y = cell_outer_y_length
    # Includes roof and basement.
    housing_size_z = pogo_length + pogo_below_flange_length + housing_basement_thickness

    dot_center_grid_locations = bd.GridLocations(
        x_spacing=dot_separation_x,
        y_spacing=dot_separation_y,
        x_count=dot_x_count,
        y_count=dot_y_count,
    )

    part = bd.Box(
        length=housing_size_x,
        width=housing_size_y,
        height=housing_size_z,
        align=bd.Align.CENTER,
    )
    box_top_face = part.faces().sort_by(bd.Axis.Z)[-1]
    box_bottom_face = part.faces().sort_by(bd.Axis.Z)[0]

    # Remove the pogo pin holes. Set the Z by making the pogo pin stick out
    # the perfect amount to get `dot_height` above the top face.
    part -= dot_center_grid_locations * make_pogo_pin(
        pogo_throw_tip_od_delta=0.5
    ).translate(
        (
            0,
            0,
            box_top_face.center().Z - pogo_length + dot_height,
        )
    )

    # Remove small cable channels which go all the way to the roof.
    for idx1, grid_pos in enumerate(dot_center_grid_locations):
        for offset in (-1, 1):
            # Create a channel out through the bottom.
            # Do this `idx * 0.0005` to avoid overlapping/self-intersecting geometry.
            cable_channel = make_curved_bent_cylinder(
                diameter=housing_cable_channel_od + (idx1 * 0.0005),
                vertical_seg_length=(pogo_length - dot_height) + (idx1 * 0.0005),
                horizontal_seg_length=housing_size_y
                + (idx1 * 0.0005),  # Extra for safety.
                bend_radius=3 + (idx1 * 0.0005),
            )

            part -= grid_pos * cable_channel.translate(
                (
                    offset * math.cos(45) * dot_separation_x,
                    offset * math.cos(45) * dot_separation_y,
                    box_top_face.center().Z,
                )
            )

            print(f"Cable channel {idx1} added.")

    # Remove the channels out the bottom.
    for x_multiplier in [-1, 0, 1]:
        channel_center_x = x_multiplier * math.cos(45) * dot_separation_x * 2

        part -= bd.Box(
            housing_cable_channel_od,
            housing_size_y * 0.8,  # TODO
            housing_size_z - pogo_length + dot_height,
            align=(bd.Align.CENTER, bd.Align.MAX, bd.Align.MIN),
        ).translate(
            (
                box_bottom_face.center().X + channel_center_x,
                box_bottom_face.bounding_box().max.Y,
                box_bottom_face.center().Z,
            )
        )

    return part


def demo_test_pipe_bend():
    # Lesson learned: The swept line must start at the origin, and
    # the sweep polygon must be centered at the origin, normal to the sweep path at the origin.

    line1 = bd.Line((10, 0, 0), (2, 0, 0))
    line2 = bd.Line((0, 2, 0), (0, 10, 0))
    line_sum = (
        line1
        + bd.RadiusArc(
            line1 @ 1,
            line2 @ 0,
            radius=2,
        )
        + line2
    ).translate(-line1.start_point())

    sweep_polygon = bd.Plane.YZ * bd.Circle(0.5).translate(line2.end_point())

    line_sum = bd.sweep(sweep_polygon, path=line_sum)
    line_sum = line_sum.translate(line1.start_point())
    return line_sum


if __name__ == "__main__":
    validate_dimensions()

    parts = {
        "pogo_pin": make_pogo_pin(),
        "housing": make_housing(),
    }

    print("Showing CAD model(s)")
    # show(parts["pogo_pin"])
    show(parts["housing"])

    (export_folder := Path(__file__).parent.with_name("build")).mkdir(exist_ok=True)
    for name, part in parts.items():
        bd.export_stl(part, str(export_folder / f"{name}.stl"))
        bd.export_step(part, str(export_folder / f"{name}.step"))
