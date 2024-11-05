"""Ball screw design with variable diameter for a Braille display."""

import copy
import json
import math
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import build123d as bd
import build123d_ease as bde
from build123d_ease import show
from loguru import logger


@dataclass
class ScrewSpec:
    """Specification for wavy ball screw."""

    ball_od: float = 1.588 + 0.1

    screw_pitch: float = 2.5
    screw_od: float = 2.4  # Just under 2.5mm
    screw_length: float = 2.5 * 4

    ball_points_per_turn: int = 32

    demo_ball_count_per_turn: int = 0

    gripper_length: float = 6
    gripper_od: float = 2.2

    def __post_init__(self) -> None:
        """Post initialization checks."""

    def deep_copy(self) -> "ScrewSpec":
        """Copy the current spec."""
        return copy.deepcopy(self)


def make_basic_ball_screw(spec: ScrewSpec) -> bd.Part:
    """Create a CAD model of the screw."""
    p = bd.Part()

    # Create main screw shaft.
    p += bd.Cylinder(
        radius=spec.screw_od / 2,
        height=spec.screw_length,
        align=bde.align.BOTTOM,
    )

    helix = bd.Helix(
        radius=spec.screw_od / 2,
        pitch=spec.screw_pitch,
        height=spec.screw_length,
        # cone_angle=spec.cone_angle_deg,
        # cone_angle=5,
    )

    p -= bd.sweep(
        path=helix,
        sections=(helix ^ 0) * bd.Circle(radius=spec.ball_od / 2),
    )

    return p


# Define the varying radius function
def radius_function(
    z: float, *, pitch: float, start_radius: float, max_radius: float
) -> float:
    """Calculate the radius of a helix with a periodically varying radius."""
    # TODO(KilowattSynthesis): Consider adding an argument to support various functions,
    # like sine instead of linear.

    # Calculate position within a single pitch period
    z_normalized = z % pitch
    if z_normalized <= pitch / 2:
        return start_radius + (max_radius - start_radius) * (2 * z_normalized / pitch)

    # else:
    return max_radius - (max_radius - start_radius) * (
        2 * (z_normalized - pitch / 2) / pitch
    )


def insane_helix_points(
    *,
    start_radius: float,
    max_radius: float,
    pitch: float,
    height: float,
    points_per_turn: int = 100,
) -> list[tuple[float, float, float]]:
    """Generate points along a helix with a periodically varying radius."""
    # Number of turns
    num_turns = height / pitch

    # Generate points along the helix with varying radius
    points = []
    for i in range(int(num_turns * points_per_turn) + 1):
        z = i * pitch / points_per_turn
        theta = 2 * math.pi * z / pitch
        r = radius_function(
            z=z,
            pitch=pitch,
            start_radius=start_radius,
            max_radius=max_radius,
        )
        x = r * math.cos(theta)
        y = r * math.sin(theta)
        points.append((x, y, z))
    return points


def make_wavy_screw(spec: ScrewSpec) -> bd.Part:
    """Make the wavy screw that can raise and lower the balls.

    Lowest point will be where the center of the ball is at the
    radius of the screw. The circumference of the ball is at the
    radius of the screw, minus 0.1.

    Relevant learning docs: https://build123d.readthedocs.io/en/latest/examples_1.html#handle
    """
    p = bd.Part()

    _min_radius = spec.ball_od / 2 + 0.1  # - 0.5
    _max_radius = spec.screw_od / 2 + spec.ball_od / 2 - 0.2
    # _max_radius = _min_radius + 0.1
    assert _min_radius < _max_radius
    assert _min_radius > 0
    assert _max_radius > 0
    # This angle used to be important, but now it's mostly just for info.
    cone_angle_deg = math.degrees(
        math.atan2(
            # Rise (in X/Y): Between the ball's center at its lowest and highest.
            _max_radius - _min_radius,
            # Run (in Z): 0.5 pitches (must go up and down every 1 pitch).
            (spec.screw_pitch / 2),
        )
    )
    info = {
        "min_radius": _min_radius,
        "max_radius": _max_radius,
        "xy_radius_diff": _max_radius - _min_radius,
        "pin_move_up_amount": _max_radius - _min_radius,
        "pitch": spec.screw_pitch,
        "pitch/2": spec.screw_pitch / 2,
        "cone_angle_deg": cone_angle_deg,
    }
    logger.success(f"Crazy helix sizing: {json.dumps(info, indent=2)}")

    # Create main screw shaft.
    p += bd.Cylinder(
        radius=spec.screw_od / 2,
        height=spec.screw_length,
        align=bde.align.BOTTOM,
    ).translate((0, 0, -spec.ball_od / 2))  # Move down by jamming prevention amount.

    # sections = [
    #     (helix_part ^ 1000) * bd.Circle(radius=spec.ball_od / 2)
    #     for helix_part in helix.wires()
    # ]
    # p += bd.sweep(
    #     path=helix,
    #     sections=sections,
    #     multisection=True,
    # )

    # p += bd.sweep(
    #     path=helix,
    #     sections=(helix ^ 0) * bd.Circle(radius=spec.ball_od / 2),
    #     multisection=True,
    # )

    helix_points = insane_helix_points(
        start_radius=_min_radius,
        max_radius=_max_radius,
        pitch=spec.screw_pitch,
        # On height, subtract ball_od to prevent jamming/wedging.
        height=spec.screw_length - spec.ball_od,
        points_per_turn=spec.ball_points_per_turn,
    )

    # # Debugging: Helpful demo view.
    # show(bd.Polyline(*helix_points))

    for point in helix_points:
        # Must remove outward-pointing cylinder if _min_radius < ball_od/2.
        # Must go in a separate loop as the spheres, or it fails.
        p -= (
            bd.Part()
            + bd.Sphere(radius=spec.ball_od / 2).translate(point)
            + (
                bd.Cylinder(
                    radius=spec.ball_od / 2 - 0.1,
                    height=spec.screw_od,
                    align=bde.align.BOTTOM,
                    rotation=bde.rotation.POS_X,
                )
                # Rotate to point outwards (based on angle from Z-axis to `point`).
                .rotate(
                    axis=bd.Axis.Z, angle=math.degrees(math.atan2(point[1], point[0]))
                )
                .translate(point)
            )
        )

    if spec.demo_ball_count_per_turn:
        helix_demo_points = insane_helix_points(
            start_radius=_min_radius,
            max_radius=_max_radius,
            pitch=spec.screw_pitch,
            height=spec.screw_pitch * 2,
            points_per_turn=spec.demo_ball_count_per_turn,
        )
        for point in helix_demo_points:
            p += bd.Sphere(radius=(spec.ball_od - 0.1) / 2).translate(point)

    # Check cross-sectional area. Doesn't work.
    # cross_areas: list[float] = []
    # z = bde.bottom_face_of(p).center().Z + 0.1
    # while z < bde.top_face_of(p).center().Z:
    #     cross_section = p.cut(bd.Plane.XY.offset(z))
    #     cross_areas.append(cross_section.area)
    #     z += 0.1
    # logger.info(
    #     f"Cross-sectional areas: min={min(cross_areas)} mm^2, "
    #     f"max={max(cross_areas)} mm^2, "
    #     f"mean={sum(cross_areas) / len(cross_areas)} mm^2"
    # )

    # Add on gripper bearing spots.
    p += bd.Cylinder(
        radius=spec.gripper_od / 2,
        height=spec.gripper_length,
        align=bde.align.BOTTOM,
    ).translate((0, 0, bde.top_face_of(p).center().Z))
    p += bd.Cylinder(
        radius=spec.gripper_od / 2,
        height=spec.gripper_length,
        align=bde.align.BOTTOM,
        rotation=bde.rotation.NEG_Z,
    ).translate((0, 0, bde.bottom_face_of(p).center().Z))

    logger.success(f"Final bounding box: {p.bounding_box()}")

    return p


def make_2x_wavy_screw(spec: ScrewSpec) -> bd.Part:
    """Make 2x wavy screws side-by-side for imaging."""
    p = bd.Part()

    spec_with_demo_balls = spec.deep_copy()
    spec_with_demo_balls.demo_ball_count_per_turn = 4

    p += make_wavy_screw(spec).translate((-spec.screw_od, 0, 0))
    p += (
        make_wavy_screw(spec_with_demo_balls)
        # .rotate(axis=bd.Axis.Z, angle=180)
        .translate((spec.screw_od, 0, 0))
    )

    return p


if __name__ == "__main__":
    start_time = datetime.now(UTC)
    py_file_name = Path(__file__).name
    logger.info(f"Running {py_file_name}")

    parts = {
        "basic_ball_screw": (make_basic_ball_screw(ScrewSpec())),
        "wavy_screw": show(make_wavy_screw(ScrewSpec())),
        # "demo_2x_wavy_screw": show(make_2x_wavy_screw(ScrewSpec())),
    }

    logger.info("Showing CAD model(s)")

    (export_folder := Path(__file__).parent.with_name("build")).mkdir(exist_ok=True)
    for name, part in parts.items():
        assert isinstance(part, bd.Part), f"{name} is not a Part"
        # assert part.is_manifold is True, f"{name} is not manifold"

        bd.export_stl(part, str(export_folder / f"{name}.stl"))
        bd.export_step(part, str(export_folder / f"{name}.step"))

    logger.info(f"Done running {py_file_name} in {datetime.now(UTC) - start_time}")
