"""Create CAD models for the braille display parts."""

import json
import math
import os
from pathlib import Path

import build123d as bd
from bd_warehouse.gear import SpurGear
from cad_lib import make_curved_bent_cylinder
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
dot_separation_x = 2.5
dot_separation_y = 2.5
dot_x_count = 2
dot_y_count = 3
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

# region Spool Specs
# Note: Known issue - The pulley and gear is too wide to fit the pitch. See log.
spool_pulley_od = 6
spool_pulley_width = 4
# Bearing (603zz = 3mm ID, 9mm OD, 5mm thickness)
spool_bearing_od = 9
spool_bearing_recess = 1
spool_bearing_thickness = 5
# Gear specs.
gear_module = 0.2
spool_gear_teeth = 52
spool_gear_thickness = 1.5
# Separation for 0.2 module; 52 teeth + 8 teeth = 6mm = 0.2 * (52+8)/2
spool_bolt_d = 3.2
# end region

# Motor Model Specs.
motor_pin_sep_x = 6  # TODO: Check this.
motor_pin_sep_y = 6
motor_pin_diameter = 1
motor_pin_length = 2
motor_body_width_x = 8
motor_body_width_y = 8
motor_body_height_z = 6.8
motor_shaft_diameter = 0.8
motor_shaft_length = 4  # Including gear.
motor_shaft_z = 6
motor_gear_tooth_count = 8
motor_gear_module = 0.2
motor_gear_length = 2


##############################
##### CALCULATED VALUES ######
##############################

# Calculated housing dimensions.
housing_size_x = inter_cell_dot_pitch_x
housing_size_y = inter_cell_dot_pitch_y + 3.3
# Includes roof and basement.
housing_size_z = pogo_length + pogo_below_flange_length + housing_basement_thickness


def validate_dimensions_and_info() -> None:
    """Validate that the dimensions are within the expected range.

    Also, print out sizing info for PCB design.
    """
    logger.info("Validating dimensions.")

    # Print mounting screw hole info.
    pcb_design_info = {
        "mounting_screw_hole": {
            "diameter": housing_mounting_screw_od,
            "separation_x": dot_separation_x,
            "separation_y": housing_mounting_screw_sep_y,
        },
    }

    logger.success(f"PCB Design Info: {json.dumps(pcb_design_info, indent=4)}")

    logger.info("Dimensions validated.")


def make_motor_model() -> bd.Part:
    """Make a motor model for rendering, mostly.

    Origin plane is at PCB.
    Origin (XY): Tip of the motor shaft/gear.
    """
    part = bd.Part()

    # Add tiny ball at origin for tracking.
    part += bd.Sphere(radius=0.5) & bd.Box(
        10,
        10,
        10,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )

    motor_body_center_x = -motor_shaft_length - motor_body_width_x / 2

    # Add the motor body.
    part += bd.Box(
        motor_body_width_x,
        motor_body_width_y,
        motor_body_height_z,
        align=(bd.Align.MAX, bd.Align.CENTER, bd.Align.MIN),
    ).translate((-motor_shaft_length, 0, 0))

    # Add the motor PCB pins.
    for x_sign, y_sign in [(1, 1), (-1, 1), (1, -1), (-1, -1)]:
        part += bd.Cylinder(
            radius=motor_pin_diameter / 2,
            height=motor_pin_length,
            align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MAX),
        ).translate(
            (
                motor_body_center_x + (x_sign * motor_pin_sep_x / 2),
                y_sign * motor_pin_sep_y / 2,
                0,
            ),
        )

    # Add the motor shaft.
    part += (
        bd.Cylinder(
            radius=motor_shaft_diameter / 2,
            height=motor_shaft_length,
            align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MAX),
        )
        .rotate(bd.Axis.Y, angle=90)
        .translate((0, 0, motor_shaft_z))
    )

    # Add the gear.
    part += (
        SpurGear(
            module=gear_module,
            tooth_count=motor_gear_tooth_count,
            thickness=motor_gear_length,
            pressure_angle=14.5,  # Controls tooth length.
            root_fillet=0.001,  # Rounding at base of each tooth.
            align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
        )
        .rotate(angle=-90, axis=bd.Axis.Y)
        .translate((0, 0, motor_shaft_z))
    )

    return part


def make_pogo_pin(pogo_throw_tip_od_delta: float = 0) -> bd.Part:
    """Make a pogo pin to act as a negative for the print-in-place surrounding part.

    * Orientation: Pin extends up.
    * Origin (XY): Center of bottom of flange. `pogo_length` extends up.
    """
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


def make_housing() -> bd.Part:
    """Make a housing for a single braille cell."""
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
        pogo_throw_tip_od_delta=0.5,
    ).translate(
        (
            0,
            0,
            box_top_face.center().Z - pogo_length + dot_height,
        ),
    )

    # Remove small cable channels which go all the way to the roof.
    for idx1, grid_pos in enumerate(dot_center_grid_locations):
        for offset in (-1, 1):
            # Create a channel out through the bottom.
            # Do this `idx * 0.0001` to avoid overlapping/self-intersecting geometry.
            cable_channel = make_curved_bent_cylinder(
                diameter=housing_cable_channel_od + (idx1 * 0.0001),
                vertical_seg_length=(pogo_length - dot_height) + (idx1 * 0.0001),
                horizontal_seg_length=housing_size_y,
                bend_radius=3 + (idx1 * 0.0001),
            )

            part -= grid_pos * cable_channel.translate(
                (
                    offset * math.cos(45) * dot_separation_x,
                    offset * math.cos(45) * dot_separation_y,
                    box_top_face.center().Z,
                ),
            )

            logger.info(f"Cable channel {idx1} added.")

    # Remove the channels out the bottom.
    for x_multiplier in [-1, 0, 1]:
        channel_center_x = x_multiplier * math.cos(45) * dot_separation_x * 2

        part -= bd.Box(
            housing_cable_channel_od + 0.01,
            (
                housing_size_y / 2  # Get to middle of housing
                + (
                    # Get to the center of the dot
                    dot_separation_y if x_multiplier != 1 else 0
                )
                + (
                    # Get to the center of the channel
                    math.cos(45) * dot_separation_y
                )
            ),
            housing_size_z - pogo_length + dot_height + housing_cable_channel_od * 0.4,
            align=(bd.Align.CENTER, bd.Align.MAX, bd.Align.MIN),
        ).translate(
            (
                box_bottom_face.center().X + channel_center_x,
                box_bottom_face.bounding_box().max.Y,
                box_bottom_face.center().Z,
            ),
        )

    # Add mounting screw holes.
    for offset in (-1, 1):
        part -= bd.Cylinder(
            radius=housing_mounting_screw_od / 2,
            height=housing_size_z,
            align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
        ).translate(
            (
                offset * (dot_separation_x / 2),  # Align to avoid cable channels.
                offset * housing_mounting_screw_sep_y / 2,
                box_bottom_face.center().Z,
            ),
        )

    assert isinstance(part, bd.Part), "Part is not a Part"

    return part


def make_housing_chain(cell_count: int) -> bd.Part:
    """Make a chain of `cell_count` braille cells.

    Generates the chain in the X direction.
    """
    logger.info(f"Making a chain of {cell_count} braille cells.")
    housing = make_housing()
    assert isinstance(housing, bd.Part), "Housing is not a Part"
    logger.info(f"Single cell housing volume: {housing.volume:.3f}")

    # Make a chain of cells.
    part = bd.Part()
    for cell_num in range(cell_count):
        part += housing.translate(
            (
                cell_num * inter_cell_dot_pitch_x,
                0,
                0,
            ),
        )

    # Add on edge plates.
    chain_min_x = part.faces().sort_by(bd.Axis.X)[0].center().X
    chain_max_x = part.faces().sort_by(bd.Axis.X)[-1].center().X

    for x, mount_align in ((chain_min_x, bd.Align.MAX), (chain_max_x, bd.Align.MIN)):
        part += bd.Box(
            length=1,
            width=housing_size_y,
            height=housing_size_z,
            align=(mount_align, bd.Align.CENTER, bd.Align.CENTER),
        ).translate((x, 0, 0))

    return part


def make_horizontal_bar_holder() -> bd.Part:
    """Make horizontal bar holder for holding the screws."""
    peg_d = 1.9
    peg_len = 1.6

    anchor_bolt_d = 1.85  # 1.85mm for thread-forming M2.
    anchor_bolt_sep_x = 5
    anchor_bolt_sep_y = 8

    horizontal_bolt_d = 3.2
    horizontal_bolt_center_z = 8

    box_width_x = 10 - 0.8
    box_length_y = 13 - 0.8
    box_height_z = 12

    part = bd.Part()

    part += bd.Box(
        box_width_x,
        box_length_y,
        box_height_z,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )

    # Remove horizontal bolt in middle
    part -= bd.Cylinder(
        radius=horizontal_bolt_d / 2,
        height=box_width_x,
        rotation=(0, 90, 0),
    ).translate((0, 0, horizontal_bolt_center_z))

    # Remove anchor bolts
    for x_sign, y_sign in [(1, 1), (-1, -1)]:
        part -= bd.Cylinder(
            radius=anchor_bolt_d / 2,
            height=box_height_z,
            align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
        ).translate(
            (
                x_sign * anchor_bolt_sep_x / 2,
                y_sign * anchor_bolt_sep_y / 2,
                0,
            ),
        )

    # Add the anchor peg additions
    for x_sign, y_sign in [(1, -1), (-1, 1)]:
        peg_cyl = bd.Part() + bd.Cylinder(
            radius=peg_d / 2,
            height=peg_len,
            align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MAX),
        ).translate(
            (
                x_sign * anchor_bolt_sep_x / 2,
                y_sign * anchor_bolt_sep_y / 2,
                0,
            ),
        )

        part += peg_cyl.fillet(
            radius=peg_d * 0.4,
            edge_list=list(peg_cyl.faces().sort_by(bd.Axis.Z)[0].edges()),
        )

    return part


def make_gear_spool() -> bd.Part:
    """Make spool with gear."""
    spool_total_width = 2 * spool_gear_thickness + spool_pulley_width

    part = bd.Part()

    # Spool pulley (in x axis).
    part += bd.Cylinder(
        radius=spool_pulley_od / 2,
        height=spool_pulley_width,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.CENTER),
        rotation=(0, 90, 0),
    )

    # Add gears.
    for rot in [0, 180]:
        gear = (
            SpurGear(
                module=gear_module,
                tooth_count=spool_gear_teeth,
                thickness=spool_gear_thickness,
                pressure_angle=14.5,  # Controls tooth length.
                root_fillet=0.001,  # Rounding at base of each tooth.
                rotation=(0, 90, 0),
                align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
            )
            .translate((spool_pulley_width / 2, 0, 0))
            .rotate(angle=rot, axis=bd.Axis.Y)
        )

        part += gear

        # Remove bearing.
        part -= (
            bd.Cylinder(
                radius=spool_bearing_od / 2,
                height=spool_bearing_recess,
                rotation=(0, -90, 0),
                align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
            )
            .translate((spool_total_width / 2, 0, 0))
            .rotate(angle=rot, axis=bd.Axis.Y)
        )

    # Remove center bolt hole.
    part -= bd.Cylinder(
        radius=spool_bolt_d / 2,
        height=100,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.CENTER),
        rotation=(0, 90, 0),
    )

    # Log the envelope.
    logger.info(f"Spool envelope: {part.bounding_box()}")
    min_supported_pitch_x = (
        spool_total_width - (spool_bearing_recess * 2) + (2 * spool_bearing_thickness)
    )
    logger.info(f"Min supported pitch (X, inter-cell): {min_supported_pitch_x:.3f}")

    return part


if __name__ == "__main__":
    validate_dimensions_and_info()

    parts = {
        "horizontal_bar_holder": (make_horizontal_bar_holder()),
        "spool": (make_gear_spool()),
        "motor_model": show(make_motor_model()),
        "pogo_pin": make_pogo_pin(),
        "housing": (make_housing()),
        "housing_chain_3x": make_housing_chain(3),
        "housing_chain_10x": make_housing_chain(10),
    }

    logger.info("Showing CAD model(s)")
    # show(parts["pogo_pin"])
    # show(parts["housing"])

    (export_folder := Path(__file__).parent.with_name("build")).mkdir(exist_ok=True)
    for name, part in parts.items():
        assert isinstance(part, bd.Part), f"{name} is not a Part"
        # assert part.is_manifold is True, f"{name} is not manifold"

        bd.export_stl(part, str(export_folder / f"{name}.stl"))
        bd.export_step(part, str(export_folder / f"{name}.step"))

    logger.info("Done")
