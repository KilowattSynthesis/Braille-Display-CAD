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


# Base Plate Specs
motor_base_plate_thickness = 3
motor_od = 4.0
motor_length = 8.0
motor_count = dot_x_count * dot_y_count
motor_raise_from_bottom_of_base = 1
motor_hold_material_on_top_thickness_z = 1
motor_space_between_motors = 0.7
motor_holder_thickness = 2

##############################
##### CALCULATED VALUES ######
##############################

# Calculated housing dimensions.
housing_size_x = inter_cell_dot_pitch_x
housing_size_y = inter_cell_dot_pitch_y + 3.3
# Includes roof and basement.
housing_size_z = pogo_length + pogo_below_flange_length + housing_basement_thickness


# Calculated motor base plate dimensions.
motor_base_plate_y_size = (
    housing_size_y + (motor_count * (motor_od + motor_space_between_motors)) + 3
)


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
        "motor_base_plate": {
            "thickness": motor_base_plate_thickness,
            "motor_count": motor_count,
            "motor_od": motor_od,
            "motor_length": motor_length,
            "motor_space_between_motors": motor_space_between_motors,
            "total_y_size": housing_size_y
            + (motor_count * (motor_od + motor_space_between_motors)),
        },
    }

    logger.success(f"PCB Design Info: {json.dumps(pcb_design_info, indent=4)}")

    logger.info("Dimensions validated.")


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


def make_motor_base(cell_count: int) -> bd.Part:
    """Make a chain of braille cells with a motor base out the end."""
    logger.info(f"Making a chain of {cell_count} braille cells with a motor base.")

    # Make the base.
    part = bd.Box(
        cell_count * inter_cell_dot_pitch_x + 10,
        motor_base_plate_y_size,
        motor_base_plate_thickness,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MAX),
    )

    base_bottom_face = part.faces().sort_by(bd.Axis.Z)[0]
    base_back_face = part.faces().sort_by(bd.Axis.Y)[-1]
    base_front_face = part.faces().sort_by(bd.Axis.Y)[0]

    # Add mounting holes for the cells.
    cell_num_offset = -((cell_count / 2) - 0.5)
    for cell_num in range(cell_count):
        center_of_cell_x = (
            # Get to the center of the box
            base_bottom_face.center().X
            # Then move to the center of the cell
            + (cell_num_offset + cell_num) * inter_cell_dot_pitch_x
        )

        for offset in (-1, 1):
            part -= (
                bd.Cylinder(
                    radius=housing_mounting_screw_od / 2,
                    height=housing_size_z,
                    align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
                )
                .translate(
                    (
                        offset * (dot_separation_x / 2),
                        offset * housing_mounting_screw_sep_y / 2,
                        base_bottom_face.center().Z,
                    ),
                )
                .translate(
                    (
                        (center_of_cell_x),
                        (
                            # Get to the back of the box
                            base_back_face.center().Y
                            # Then move forward to the center of the cell
                            - (housing_size_y / 2)
                        ),
                        0,
                    ),
                )
            )

        logger.debug(f"Mounting holes added for cell {cell_num}.")

        # Add motor gripper.
        part += bd.Box(
            inter_cell_dot_pitch_x - 1,
            (motor_count * (motor_od + motor_space_between_motors)),
            (
                motor_od
                + motor_hold_material_on_top_thickness_z  # Amount on top
                + motor_raise_from_bottom_of_base  # Amount on bottom
            ),
            align=(bd.Align.CENTER, bd.Align.MIN, bd.Align.MIN),
        ).translate(
            (
                center_of_cell_x,
                base_front_face.center().Y,
                base_bottom_face.center().Z + motor_raise_from_bottom_of_base,
            ),
        )

        # Add motor mount locations, for each cell.
        for motor_num in range(motor_count):
            part -= bd.Cylinder(
                radius=motor_od / 2,
                height=motor_length + 15,
                rotation=(0, 90, 0),
                align=(bd.Align.MAX, bd.Align.CENTER, bd.Align.CENTER),
            ).translate(
                (
                    center_of_cell_x,
                    (
                        # Get to the front of the box.
                        base_front_face.center().Y
                        # Then move backwards by the motor count.
                        + ((motor_num + 0.5) * (motor_od + motor_space_between_motors))
                    ),
                    (
                        base_bottom_face.center().Z
                        + motor_raise_from_bottom_of_base
                        + (0.0001 * motor_num)  # Avoid overlapping geometry.
                    ),
                ),
            )

        logger.debug(f"Motor mounts added for cell {cell_num}.")

    assert isinstance(part, bd.Part), "Part is not a Part"

    logger.info(f"Motor base volume: {part.volume:.2f} mm^3 for {cell_count} cells.")

    return part


def make_horizontal_bar_holder() -> bd.Part:
    """Make horizontal bar holder for holding the screws."""
    peg_d = 1.9
    peg_len = 1.6

    anchor_bolt_d = 1.85  # 1.85mm for thread-forming M2.
    anchor_bolt_sep_x = 5
    anchor_bolt_sep_y = 8

    horiz_bolt_d = 3.2
    horiz_bolt_center_z = 8

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

    # Remove horiz bolt in middle
    part -= bd.Cylinder(
        radius=horiz_bolt_d / 2,
        height=box_width_x,
        rotation=(0, 90, 0),
    ).translate((0, 0, horiz_bolt_center_z))

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
    # Note: Known issue - The pulley and gear is too wide to fit the pitch. See log.
    spool_pulley_od = 6
    spool_pulley_width = 4

    # Bearing (603zz = 3mm ID, 9mm OD, 5mm thickness)
    spool_bearing_od = 9
    spool_bearing_recess = 1
    spool_bearing_thickness = 5

    # Gear specs.
    gear_module = 0.2
    gear_teeth = 52
    gear_thickness = 1.5
    # Separation for 0.2 module; 52 teeth + 8 teeth = 6mm = 0.2 * (52+8)/2

    bolt_d = 3.2

    spool_total_width = 2 * gear_thickness + spool_pulley_width

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
                tooth_count=gear_teeth,
                thickness=gear_thickness,
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
        radius=bolt_d / 2,
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
        "horizontal_bar_holder": show(make_horizontal_bar_holder()),
        "spool": show(make_gear_spool()),
        "pogo_pin": make_pogo_pin(),
        "housing": (make_housing()),
        "motor_base_3x": (make_motor_base(3)),
        "motor_base_1x": (make_motor_base(1)),
        "housing_chain_3x": make_housing_chain(3),
        "housing_chain_10x": make_housing_chain(10),
    }

    logger.info("Showing CAD model(s)")
    # show(parts["pogo_pin"])
    # show(parts["housing"])
    # show(parts["motor_base_3x"])

    (export_folder := Path(__file__).parent.with_name("build")).mkdir(exist_ok=True)
    for name, part in parts.items():
        assert isinstance(part, bd.Part), f"{name} is not a Part"
        # assert part.is_manifold is True, f"{name} is not manifold"

        bd.export_stl(part, str(export_folder / f"{name}.stl"))
        bd.export_step(part, str(export_folder / f"{name}.step"))
