import os
import math
from pathlib import Path

import build123d as bd

# from cad_lib import float_range


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
housing_basement_thickness = 3
lock_plate_thickness = 1.0  # <- This is the cool part that locks the dots.


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


def make_housing_sketches_deprecated():
    housing_width_x = inter_cell_dot_pitch_x * 2
    housing_height_y = cell_outer_y_length

    with bd.BuildPart() as base_body_wall_part:
        with bd.BuildSketch(bd.Plane.XY):
            bd.Rectangle(
                width=housing_width_x,
                height=housing_height_y,
                align=bd.Align.CENTER,
            )

            # Draw a grid of the dot squares.
            dot_centers = bd.GridLocations(
                x_spacing=dot_separation_x,
                y_spacing=dot_separation_y,
                x_count=dot_x_count,
                y_count=dot_y_count,
            )
            with dot_centers:
                bd.Rectangle(
                    width=spring_cell_width,
                    height=spring_cell_width,
                    align=bd.Align.CENTER,
                    mode=bd.Mode.SUBTRACT,
                )
        bd.extrude(amount=spring_max_length + housing_basement_thickness)

        # Add the roof.
        with bd.BuildSketch(
            base_body_wall_part.faces().sort_by(bd.Axis.Z)[-1]
        ) as _roof_sketch:
            bd.Rectangle(
                width=housing_width_x,
                height=housing_height_y,
                align=bd.Align.CENTER,
            )
            with dot_centers:
                bd.Circle(
                    radius=dot_diameter_base / 2,
                    mode=bd.Mode.SUBTRACT,
                )

        bd.extrude(amount=housing_roof_thickness)

    return base_body_wall_part.part


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
    # box_bottom_face = part.faces().sort_by(bd.Axis.Z)[0]

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

    # Remove main cable channel. Bends from bottom of pogo out +Y side.
    for idx1, grid_pos in enumerate(dot_center_grid_locations):
        # Create a channel out through the bottom.
        # Do this `idx * 0.001` to avoid overlapping/self-intersecting geometry.
        cable_channel = make_curved_bent_cylinder(
            diameter=1 + (idx1 * 0.001),
            vertical_seg_length=4 + (idx1 * 0.001),
            horizontal_seg_length=housing_size_y + (idx1 * 0.001),  # Extra for safety.
            bend_radius=3 + (idx1 * 0.001),
        )

        part -= grid_pos * cable_channel.translate(
            # Place top of snorkel at the bottom of the pogo pin's flange.
            # Then, move it down by `z_offset` to make it go through the bottom.
            (
                0,
                0,
                (box_top_face.center().Z - pogo_length + dot_height),
            )
        )
        show(part)
        print(f"Cable channel {idx1} added.")

    # Remove small cable channel which goes all the way to the roof,
    # and into the large cable channels.
    for idx1, grid_pos in enumerate(dot_center_grid_locations):
        for offset in (-1, 1):
            # Note: offset=1 is the downstream (+Y) side.
            z_rot = {1: 35, -1: -35}[offset]
            part -= grid_pos * make_angled_cylinders(
                diameter=0.75,
                vertical_seg_length=pogo_length - dot_height + pogo_below_flange_length,
                horizontal_seg_length={1: 2.7, -1: 2.5}[offset],
                horizontal_angle={1: -60, -1: -30}[offset],
            ).rotate(bd.Axis.Z, z_rot).translate(
                # Place top of snorkel at the bottom of the pogo pin's flange.
                (
                    offset * math.cos(45) * 2,
                    offset * math.cos(45) * 2,
                    box_top_face.center().Z,
                )
            )

        show(part)
        print(f"Tiny channel to surface #{idx1} added.")

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


def make_curved_bent_cylinder(
    *,
    diameter: float,
    vertical_seg_length: float,
    horizontal_seg_length: float,
    bend_radius: float,
    horizontal_angle: float = 0,
):
    """Make a bent cylinder for this project.

    * Top snorkel part starts at the origin, then goes down, then in the +Y direction.
    * Makes a 90-degree bend. All X=0.
    * Changing the bend_radius will not change the placement of the straight segments.

    Args:
        horizontal_angle: Angle in degrees to rotate the horizontal segment.
            0 means flat. Negative angle means point downwards.
    """

    if horizontal_angle != 0:
        raise NotImplementedError("Horizontal angle rotation not implemented.")

    line_vertical = bd.Line((0, 0, 0), (0, 0, -vertical_seg_length + bend_radius))
    line_horizontal = bd.Line(
        (0, bend_radius, -vertical_seg_length),
        (0, horizontal_seg_length, -vertical_seg_length),
    )
    line_sum = line_vertical + (
        # bd.Plane.YZ *
        bd.CenterArc(
            (0, 0, 0),
            radius=bend_radius,
            start_angle=270,
            arc_size=90 - horizontal_angle,
        )
        .rotate(bd.Axis.Y, 90)  # Rotate to be in the YZ plane.
        .translate((0, bend_radius, -vertical_seg_length + bend_radius))
    )
    if horizontal_seg_length > 0:
        line_sum += line_horizontal

    sweep_polygon = bd.Plane.XY * bd.Circle(diameter / 2)
    line_sum = bd.sweep(sweep_polygon, path=line_sum)

    return line_sum


def make_angled_cylinders(
    *,
    diameter: float,
    vertical_seg_length: float,
    horizontal_seg_length: float,
    horizontal_angle: float = 0,
):
    """Make two connected cylinders at an angle.

    * Top snorkel part starts at the origin, then goes down, then in the +Y direction.

    Args:
        horizontal_angle: Angle in degrees to rotate the horizontal segment.
            0 means flat. Negative angle means point downwards.
    """

    part = bd.Cylinder(
        radius=diameter / 2,
        height=vertical_seg_length + diameter / 2,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MAX),
    )

    part += (
        bd.Cylinder(
            radius=diameter / 2,
            height=horizontal_seg_length,  #  + diameter / 2,
            align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
        )
        .rotate(bd.Axis.X, -90 + horizontal_angle)
        .translate((0, 0, -vertical_seg_length))
    )

    return part


def demo_test_make_curved_bent_cylinder():
    return make_curved_bent_cylinder(
        diameter=0.5,
        vertical_seg_length=4,
        horizontal_seg_length=5,
        bend_radius=1,
    )


def demo_test_make_angled_cylinders():
    return make_angled_cylinders(
        diameter=0.5,
        vertical_seg_length=4,
        horizontal_seg_length=5,
        horizontal_angle=-30,
    )


if __name__ == "__main__":
    validate_dimensions()

    # show(demo_test_make_curved_bent_cylinder())
    # show(demo_test_make_angled_cylinders())
    # exit(0)

    parts = {
        "pogo_pin": make_pogo_pin(),
        # "housing_sketches_deprecated": make_housing_sketches_deprecated(),
        "housing": make_housing(),
        # "demo_test_pipe_bend": demo_test_pipe_bend(),
        # "demo_test_make_curved_bent_cylinder": demo_test_make_curved_bent_cylinder(),
    }

    print("Showing CAD model(s)")
    # show(parts["pogo_pin"])
    show(parts["housing"])

    (export_folder := Path(__file__).parent.with_name("build")).mkdir(exist_ok=True)
    for name, part in parts.items():
        bd.export_stl(part, str(export_folder / f"{name}.stl"))
        bd.export_step(part, str(export_folder / f"{name}.step"))
