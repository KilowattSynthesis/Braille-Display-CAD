"""Ball screw design with variable diameter for a Braille display."""

import json
import math
from dataclasses import dataclass
from pathlib import Path

import build123d as bd
import build123d_ease as bde
from build123d_ease import show
from loguru import logger


@dataclass
class ScrewSpec:
    """Specification for part1."""

    ball_od: float = 1.588 + 0.1

    screw_pitch: float = 2.5
    screw_od: float = 2.4  # Just under 2.5mm
    screw_length: float = 10

    cone_angle_deg: float = 0  # Default: 0

    def __post_init__(self) -> None:
        """Post initialization checks."""


def make_basic_screw(spec: ScrewSpec) -> bd.Part:
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


def insane_helix(
    *,
    start_radius: float,
    max_radius: float,
    pitch: float,
    height: float,
    points_per_turn: int = 100,
) -> bd.Polyline:
    """Create a helix with a periodically varying radius.

    Varies twice-per-pitch from start_radius to max_radius and back.

    Args:
        start_radius (float): Starting radius of the helix.
        max_radius (float): Maximum radius reached at halfway through the pitch.
        pitch (float): Pitch of the helix (distance between turns).
        height (float): Total height of the helix.
        points_per_turn (int): Number of points per turn for generating the helix path.

    Returns:
        bd.Sweep: A Polyline of the helix with a varying radius.

    """

    # Define the varying radius function
    def radius_function(z: float) -> float:
        # Calculate position within a single pitch period
        z_normalized = z % pitch
        if z_normalized <= pitch / 2:
            return start_radius + (max_radius - start_radius) * (
                2 * z_normalized / pitch
            )

        # else:
        return max_radius - (max_radius - start_radius) * (
            2 * (z_normalized - pitch / 2) / pitch
        )

    # TODO(KilowattSynthesis): Opportunity to create a version of this function
    # that doesn't use `points_per_turn`.

    # Number of turns
    num_turns = height / pitch

    # Generate points along the helix with varying radius
    points = []
    for i in range(int(num_turns * points_per_turn) + 1):
        z = i * pitch / points_per_turn
        theta = 2 * math.pi * z / pitch
        r = radius_function(z)
        x = r * math.cos(theta)
        y = r * math.sin(theta)
        points.append((x, y, z))

    # Create the helix path
    helix_path = bd.Polyline(*points)
    return helix_path


def make_wavy_screw(spec: ScrewSpec) -> bd.Part:
    """Make the wavy screw that can raise and lower the balls.

    Lowest point will be where the center of the ball is at the
    radius of the screw. The circumference of the ball is at the
    radius of the screw, minus 0.1.
    """
    p = bd.Part()

    _min_radius = spec.ball_od / 2 + 0.3
    # _max_radius = spec.screw_od / 2 + spec.ball_od / 2 - 0.5
    _max_radius = _min_radius + 0.1
    assert _min_radius < _max_radius
    assert _min_radius > 0
    assert _max_radius > 0
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
        "pitch": spec.screw_pitch,
        "pitch/2": spec.screw_pitch / 2,
        "cone_angle_deg": cone_angle_deg,
    }
    logger.success(f"Crazy helix sizing: {json.dumps(info, indent=2)}")
    cone_angle_deg = 0

    increasing_helix = bd.Helix(
        # Min radius. Cone expands outward. Put the ball touching the center.
        radius=_min_radius,
        pitch=spec.screw_pitch,
        height=spec.screw_pitch / 2,
        cone_angle=cone_angle_deg,
    )
    decreasing_helix = (
        bd.Helix(
            # Max radius. Cone contracts inward. Put the ball touching the
            # circumference of the screw.
            radius=_max_radius,
            pitch=spec.screw_pitch,
            height=spec.screw_pitch / 2,
            cone_angle=-cone_angle_deg,
        )
        .rotate(angle=180, axis=bd.Axis.Z)
        .translate((0, 0, spec.screw_pitch / 2))
    )

    incr_decr_helix = increasing_helix + decreasing_helix
    show(incr_decr_helix)
    helix = incr_decr_helix
    for i in range(1, 3):
        helix += incr_decr_helix.translate((0, 0, spec.screw_pitch * i))

    show(helix)

    helix = insane_helix(
        start_radius=_min_radius,
        max_radius=_max_radius,
        pitch=spec.screw_pitch,
        height=spec.screw_length,
    )
    show(helix)

    # Create main screw shaft.
    p += bd.Cylinder(
        radius=spec.screw_od / 2,
        height=spec.screw_length,
        align=bde.align.BOTTOM,
    )

    for helix_part in helix.wires():
        p -= bd.sweep(
            path=helix_part,
            sections=(helix_part ^ 0) * bd.Circle(radius=spec.ball_od / 2),
        )

    return p


if __name__ == "__main__":
    parts = {
        "basic_screw": (make_basic_screw(ScrewSpec())),
        "wavy_screw": show(make_wavy_screw(ScrewSpec())),
    }

    logger.info("Showing CAD model(s)")

    (export_folder := Path(__file__).parent.with_name("build")).mkdir(exist_ok=True)
    for name, part in parts.items():
        assert isinstance(part, bd.Part), f"{name} is not a Part"
        # assert part.is_manifold is True, f"{name} is not manifold"

        bd.export_stl(part, str(export_folder / f"{name}.stl"))
        bd.export_step(part, str(export_folder / f"{name}.step"))
