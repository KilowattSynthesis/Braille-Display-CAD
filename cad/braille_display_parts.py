"""Create CAD models for the braille display parts."""

import json
import math
import os
from pathlib import Path

import build123d as bd
import build123d_ease as bde
from bd_warehouse.gear import SpurGear
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
dot_height = 0.8  # Amount to stick out above the housing.

# Housing dimensions.
min_wall_thickness = 1.0
housing_roof_thickness = 1.0
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
spool_pulley_od = 7
spool_pulley_width = 5  # Width of the tape part.

# Bearing (603zz = 3mm ID, 9mm OD, 5mm thickness)
# spool_bearing_od = 9
# spool_bearing_thickness = 5

# Bearing (MR63 ZZ 3x6x2.5mm)
spool_bearing_od = 6
spool_bearing_thickness = 2.5

# Other bearing options:
# 681 1mm * 3mm * 1mm L-415ZZ 681X -> https://www.aliexpress.com/item/4000449063951.html
# Full list -> https://www.aliexpress.com/item/1005006599062930.html

# Gear specs.
gear_module = 0.2
spool_gear_tooth_count = 64
spool_gear_thickness = 1.1
spool_flange_thickness = 0.5
spool_flange_od = 8
spool_bolt_d = 3.2
spool_bearing_border_thickness = 0.1  # Border around the bearing on non-gear side.

# Assembly planning.
spool_mounting_angle = 45  # 0 means motor_shaft_z==spool_shaft_z. >0 moves it up.
# end region

# Motor Model Specs.
motor_pin_sep_x = 3
motor_pin_sep_y = 3
motor_pin_diameter = 0.5
motor_pin_length = 1
motor_body_width_x = 7.4  # Axial.
motor_body_width_y = 6  # Radial.
motor_body_height_z = 5.9
motor_shaft_diameter = 0.8
motor_shaft_length = 1.5  # Including gear.
motor_shaft_z = 3.0
motor_gear_tooth_count = 8
motor_gear_length = 0.85

# region Horizontal Bar Holder
bar_holder_peg_d = 1.9
bar_holder_peg_len = 1.6

bar_holder_anchor_bolt_d = 1.85  # 1.85mm for thread-forming M2.
bar_holder_anchor_bolt_sep_x = 5
bar_holder_anchor_bolt_sep_y = 8

bar_holder_horizontal_bolt_d = 3.2

bar_holder_box_width_x = 10 - 0.8
bar_holder_box_length_y = 13 - 0.8
bar_holder_box_height_z = 12
# end region

##############################
##### CALCULATED VALUES ######
##############################

# Calculated housing dimensions.
housing_size_x = inter_cell_dot_pitch_x
housing_size_y = inter_cell_dot_pitch_y + 3.3
# Includes roof and basement.
housing_size_z = pogo_length - dot_height

# Separation for 0.2 module; 52 teeth + 8 teeth = 6mm = 0.2 * (52+8)/2
spool_to_motor_shaft_separation = (
    gear_module * (motor_gear_tooth_count + spool_gear_tooth_count) / 2
)

spool_vs_motor_delta_y = (
    math.cos(math.radians(spool_mounting_angle)) * spool_to_motor_shaft_separation
)
spool_vs_motor_delta_z = (
    math.sin(math.radians(spool_mounting_angle)) * spool_to_motor_shaft_separation
)

bar_holder_horizontal_bolt_center_z = motor_shaft_z + spool_vs_motor_delta_z


def validate_dimensions_and_info() -> None:
    """Validate that the dimensions are within the expected range.

    Also, print out sizing info for PCB design.
    """
    logger.info("Validating dimensions.")

    assert spool_pulley_od > spool_bearing_od
    assert spool_flange_od > spool_bearing_od

    # Print mounting screw hole info.
    pcb_design_info = {
        "mounting_screw_hole": {
            "diameter": housing_mounting_screw_od,
            "separation_x": dot_separation_x,
            "separation_y": housing_mounting_screw_sep_y,
        },
        "gears": {
            "spool_to_motor_shaft_separation": spool_to_motor_shaft_separation,
        },
        "spool_assembly": {
            "shift_motor_assembly_x": (
                motor_shaft_length + motor_body_width_x / 2 - motor_pin_sep_x / 2
            ),
            "y_dist_motor_shaft_to_spool_shaft": spool_vs_motor_delta_y,
            "z_dist_motor_shaft_to_spool_shaft": spool_vs_motor_delta_z,
            "bar_holder_horizontal_bolt_center_z": bar_holder_horizontal_bolt_center_z,
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
    part += bd.Sphere(radius=0.25) & bd.Box(
        10,
        10,
        10,
        align=bde.align.ANCHOR_BOTTOM,
    )

    motor_body_center_x = -motor_shaft_length - motor_body_width_x / 2

    # Add the motor body (box part, esp at bottom).
    part += bd.Box(
        motor_body_width_x - 2,
        motor_pin_sep_y * 1.2,
        1,
        align=(bd.Align.MAX, bd.Align.CENTER, bd.Align.MIN),
    ).translate((-motor_shaft_length - 1, 0, 0))

    # Add the motor body (round part, esp at top).
    part += bd.Cylinder(
        radius=motor_body_width_y / 2,
        height=motor_body_width_x,
        align=bde.align.ANCHOR_BOTTOM,  # Align pre-rotation.
        rotation=bde.rotation.NEG_X,
    ).translate(
        (
            -motor_shaft_length,
            0,
            motor_body_width_y / 2,
        ),
    )

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
            align=bde.align.ANCHOR_BOTTOM,
        )
        .rotate(angle=-90, axis=bd.Axis.Y)
        .translate((0, 0, motor_shaft_z))
    )

    logger.info(f"Motor model bounding box: {part.bounding_box()}")

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
            align=bde.align.ANCHOR_BOTTOM,
        )

        # Shaft.
        bd.Cylinder(
            radius=pogo_shaft_od / 2,
            height=pogo_shaft_length,
            align=bde.align.ANCHOR_BOTTOM,
        )

        # Throw/tip.
        with bd.Locations(pogo_pin_part.faces().sort_by(bd.Axis.Z)[-1]):
            bd.Cylinder(
                radius=(pogo_throw_tip_od + pogo_throw_tip_od_delta) / 2,
                height=pogo_throw_length,
                align=bde.align.ANCHOR_BOTTOM,
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
        align=bde.align.ANCHOR_BOTTOM,
    )
    box_top_face = part.faces().sort_by(bd.Axis.Z)[-1]

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

    # Remove the tape.
    part -= bd.Box(
        4,  # Width of the tape.
        100,
        0.5,  # Thickness of tape passage.
        align=bde.align.ANCHOR_CENTER,
    ).translate((0, 0, box_top_face.center().Z - 1))

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
    part = bd.Part()

    part += bd.Box(
        bar_holder_box_width_x,
        bar_holder_box_length_y,
        bar_holder_box_height_z,
        align=bde.align.ANCHOR_BOTTOM,
    )

    # Remove horizontal bolt in middle
    part -= bd.Cylinder(
        radius=bar_holder_horizontal_bolt_d / 2,
        height=bar_holder_box_width_x,
        rotation=(0, 90, 0),
    ).translate((0, 0, bar_holder_horizontal_bolt_center_z))

    # Remove anchor bolts
    for x_sign, y_sign in [(1, 1), (-1, -1)]:
        part -= bd.Cylinder(
            radius=bar_holder_anchor_bolt_d / 2,
            height=bar_holder_box_height_z,
            align=bde.align.ANCHOR_BOTTOM,
        ).translate(
            (
                x_sign * bar_holder_anchor_bolt_sep_x / 2,
                y_sign * bar_holder_anchor_bolt_sep_y / 2,
                0,
            ),
        )

    # Add the anchor peg additions
    for x_sign, y_sign in [(1, -1), (-1, 1)]:
        peg_cyl = bd.Part() + bd.Cylinder(
            radius=bar_holder_peg_d / 2,
            height=bar_holder_peg_len,
            align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MAX),
        ).translate(
            (
                x_sign * bar_holder_anchor_bolt_sep_x / 2,
                y_sign * bar_holder_anchor_bolt_sep_y / 2,
                0,
            ),
        )

        part += peg_cyl.fillet(
            radius=bar_holder_peg_d * 0.4,
            edge_list=list(peg_cyl.faces().sort_by(bd.Axis.Z)[0].edges()),
        )

    return part


def make_gear_spool() -> bd.Part:
    """Make spool with gear."""
    spool_total_width = (
        spool_gear_thickness + spool_flange_thickness + spool_pulley_width
    )

    part = bd.Part()

    # Spool pulley (in x axis).
    part += bd.Cylinder(
        radius=spool_pulley_od / 2,
        height=spool_pulley_width,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.CENTER),
        rotation=(0, 90, 0),
    )

    # Add gear (on POS_X side).
    part += SpurGear(
        module=gear_module,
        tooth_count=spool_gear_tooth_count,
        thickness=spool_gear_thickness,
        # TODO: Pressure angle might not be right. Was sorta random.  # noqa: FIX002
        pressure_angle=14.5,  # Controls tooth length.
        root_fillet=0.001,  # Rounding at base of each tooth.
        rotation=bde.rotation.POS_X,
        align=bde.align.ANCHOR_BOTTOM,  # Normal mode.
    ).translate((part.bounding_box().max.X, 0, 0))

    # Add flange (on NEG_X side).
    part += bd.Cylinder(
        radius=spool_flange_od / 2,
        height=spool_flange_thickness,
        rotation=bde.rotation.NEG_X,
        align=bde.align.ANCHOR_BOTTOM,  # Normal mode.
    ).translate((part.bounding_box().min.X, 0, 0))

    # Remove bearing (gear side, POS_X).
    part -= bd.Cylinder(
        radius=spool_bearing_od / 2,
        height=spool_bearing_thickness,
        rotation=bde.rotation.NEG_X,
        align=bde.align.ANCHOR_BOTTOM,
    ).translate((part.bounding_box().max.X, 0, 0))

    # Remove bearing (non-gear side, NEG_X).
    part -= bd.Cylinder(
        radius=spool_bearing_od / 2,
        height=spool_bearing_thickness,
        rotation=bde.rotation.POS_X,
        align=bde.align.ANCHOR_BOTTOM,
    ).translate((part.bounding_box().min.X, 0, 0))

    # Remove center bolt hole.
    part -= bd.Cylinder(
        radius=spool_bolt_d / 2,
        height=100,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.CENTER),
        rotation=(0, 90, 0),
    )

    # Log the envelope.
    logger.info(f"Spool envelope: {part.bounding_box()}")
    min_supported_pitch_x = spool_total_width  # Way simpler now.
    logger.info(f"Min supported pitch (X, inter-cell): {min_supported_pitch_x:.3f}")

    return part


def make_spool_motor_assembly() -> bd.Part:
    """Create a spool+motor assembly."""
    p = bd.Part()

    p += make_motor_model()

    spool = make_gear_spool()
    spool = spool.translate(
        (
            -spool.faces().sort_by(bd.Axis.X)[-1].center().X,
            spool_vs_motor_delta_y,
            motor_shaft_z + spool_vs_motor_delta_z,
        ),
    )
    p += spool

    if spool.bounding_box().min.Z < 0:
        logger.warning(
            f"Bounding box min Z is below 0: {spool.bounding_box().min.Z:,.3f}. "
            "Gear is probably dipping into the PCB. "
            "Adjust `spool_mounting_angle`, probably.",
        )

    return p


if __name__ == "__main__":
    validate_dimensions_and_info()

    parts = {
        "spool_motor_assembly": (make_spool_motor_assembly()),
        "pogo_pin": (make_pogo_pin()),
        "housing": (make_housing()),
        "housing_chain_3x": make_housing_chain(3),
        "housing_chain_10x": make_housing_chain(10),
        "horizontal_bar_holder": (make_horizontal_bar_holder()),
        "spool": show(make_gear_spool()),
        "motor_model": (make_motor_model()),
    }

    logger.info("Saving CAD model(s)")

    (export_folder := Path(__file__).parent.parent / "build/pogo_spools").mkdir(
        exist_ok=True,
        parents=True,
    )
    for name, part in parts.items():
        assert isinstance(part, bd.Part), f"{name} is not a Part"
        # assert part.is_manifold is True, f"{name} is not manifold"

        bd.export_stl(part, str(export_folder / f"{name}.stl"))
        bd.export_step(part, str(export_folder / f"{name}.step"))

    logger.info("Done")
