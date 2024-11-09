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

    ball_points_per_turn: int = 5

    demo_ball_count_per_turn: int = 0

    gripper_length: float = 2.3
    gripper_od: float = 2.2

    # TODO(KilowattSynthesis): Consider making these cones instead of cylinders.
    gripper_groove_length = 1
    gripper_groove_depth = 0.5

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


def radius_function(
    z: float, *, pitch: float, start_radius: float, max_radius: float
) -> float:
    """Calculate the radius of a helix with a periodically varying radius.

    Starts at `r(z=0) = start_radius`.
    """
    # TODO(KilowattSynthesis): Consider adding an argument to support various functions,
    # like sine instead of linear.

    radius_diff = max_radius - start_radius

    # Calculate position within a single pitch period
    z_normalized = z % pitch
    # `z_normalized` is now between 0 and pitch/2
    sin_part = math.sin(math.pi * (z_normalized / pitch))
    assert 0 <= sin_part <= 1
    radius = start_radius + (sin_part * radius_diff)
    assert start_radius <= radius <= max_radius

    return radius


def insane_helix_points(
    *,
    start_radius: float,
    max_radius: float,
    pitch: float,
    height: float,
    points_per_turn: int,
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

    helix_points = insane_helix_points(
        start_radius=_min_radius,
        max_radius=_max_radius,
        pitch=spec.screw_pitch,
        # On height, subtract ball_od to prevent jamming/wedging.
        height=spec.screw_length - spec.ball_od,
        points_per_turn=spec.ball_points_per_turn,
    )

    # # Debugging: Helpful demo view.
    show(bd.Polyline(*helix_points))

    helix_path_chunks: list[bd.LineType] = [
        bd.ThreePointArc(point_0, point_1, point_2)
        for point_0, point_1, point_2 in zip(
            helix_points[:-2],
            helix_points[1:-1],
            helix_points[2:],
            strict=True,
        )
    ]

    helix_part = bd.Part()
    for helix_path_chunk in helix_path_chunks:
        helix_part += bd.sweep(
            path=helix_path_chunk,
            sections=(helix_path_chunk ^ 0)
            * bd.Circle(radius=1),  # FIXME: Should be spec.ball_od / 2, too small.
        )
    p -= helix_part
    # for helix_point in helix_points[1:-1]:
    #     # Remove the little "orange slices" that show up.
    #     p -= bd.Sphere(radius=spec.ball_od / 2).translate(helix_point)

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

    # Add on gripper bearing spots.
    screw_top_z = bde.top_face_of(p).center().Z
    screw_bottom_z = bde.bottom_face_of(p).center().Z
    p += bd.Cylinder(
        radius=spec.gripper_od / 2,
        height=spec.gripper_length,
        align=bde.align.BOTTOM,
    ).translate((0, 0, screw_top_z))
    p += bd.Cylinder(
        radius=spec.gripper_od / 2,
        height=spec.gripper_length,
        align=bde.align.BOTTOM,
        rotation=bde.rotation.NEG_Z,
    ).translate((0, 0, screw_bottom_z))

    # Remove the gripper bearing parts.
    gripper_groove = (
        bd.Part()
        + bd.Cylinder(radius=spec.gripper_od / 2, height=spec.gripper_groove_length)
        - bd.Cylinder(
            radius=(spec.gripper_od - 2 * spec.gripper_groove_depth) / 2,
            height=spec.gripper_groove_length,
        )
    )
    p -= gripper_groove.translate((0, 0, screw_bottom_z - spec.gripper_length / 2))
    p -= gripper_groove.translate((0, 0, screw_top_z + spec.gripper_length / 2))

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
