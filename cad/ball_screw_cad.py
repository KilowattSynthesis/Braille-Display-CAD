"""Ball screw design with variable diameter for a Braille display."""

import copy
import json
import math
from dataclasses import dataclass
from datetime import UTC, datetime
from itertools import product
from pathlib import Path

import build123d as bd
import build123d_ease as bde
from build123d_ease import show
from loguru import logger

# TODO(KilowattSynthesis): I think you need to make the top face >ball_od thick, and
# then have pegs that go down into where the balls are. Then you can have
# the smooth varying radius channel that guides the balls through the
# ball screw.


@dataclass
class ScrewSpec:
    """Specification for wavy ball screw."""

    ball_od: float = 1.588 + 0.1

    screw_pitch: float = 2.5
    screw_od: float = 2.4  # Just under 2.5mm
    screw_length: float = 2.5 * 4

    ball_points_per_turn: int = 32

    demo_ball_count_per_turn: int = 0

    gripper_length: float = 2.3
    gripper_od: float = 2.2

    # TODO(KilowattSynthesis): Consider making these cones instead of cylinders.
    gripper_groove_length = 1
    gripper_groove_depth = 0.5

    @property
    def gripper_groove_shoulder_length(self) -> float:
        """Length of each shoulder on the sides of the groove."""
        return (self.gripper_length - self.gripper_groove_length) / 2

    def __post_init__(self) -> None:
        """Post initialization checks."""

    def deep_copy(self) -> "ScrewSpec":
        """Copy the current spec."""
        return copy.deepcopy(self)


@dataclass(kw_only=True)
class HousingSpec:
    """Specification for braille cell housing."""

    dot_pitch_x: float = 2.5
    dot_pitch_y: float = 2.5
    inter_cell_pitch_x: float = 6
    inter_cell_pitch_y: float = 10

    # Wall thickness>1.2mm, thinnest part≥0.8mm, hole size≥1.5mm.
    top_face_thickness: float = 0.4
    wall_thickness: float = 1.2

    cell_count_x: int = 3

    # Suspend the screw by this much.
    dist_top_of_screw_to_housing_top_face: float = 0.1
    dist_bottom_of_housing_to_bottom_of_screw: float = 1

    gripper_interface_freedom_radius: float = 0.1
    gripper_interface_freedom_length: float = 0.1

    # housing_size_x: float = inter_cell_dot_pitch_x
    # housing_size_y = inter_cell_dot_pitch_y + 3.3

    screw_spec: ScrewSpec

    def __post_init__(self) -> None:
        """Post initialization checks."""

    def deep_copy(self) -> "HousingSpec":
        """Copy the current spec."""
        return copy.deepcopy(self)

    @property
    def body_height_where_screw_goes(self) -> float:
        """Height of the inside of the housing where the screw goes."""
        return (
            self.dist_bottom_of_housing_to_bottom_of_screw
            + self.screw_spec.screw_od * 0.5
        )

    @property
    def total_z(self) -> float:
        """Total Z height of the housing."""
        return (
            self.top_face_thickness
            + self.body_height_where_screw_goes
            + self.screw_spec.screw_od * 0.5
            + self.dist_top_of_screw_to_housing_top_face
        )

    @property
    def total_x(self) -> float:
        """Total X width of the housing."""
        return (self.inter_cell_pitch_x * self.cell_count_x) + (2 * self.wall_thickness)

    @property
    def total_y(self) -> float:
        """Total Y width of the housing."""
        # return self.inter_cell_pitch_y + self.wall_thickness * 2
        return self.screw_spec.screw_length + 2 * self.screw_spec.gripper_length

    def get_x_of_center_of_cells(self) -> list[float]:
        """Get the X coordinate of the center of each cell."""
        return bde.evenly_space_with_center(
            count=self.cell_count_x,
            spacing=self.inter_cell_pitch_x,
        )

    @property
    def sep_between_centers_of_gripper_grooves(self) -> float:
        """Separation between the centers of the gripper grooves."""
        return self.screw_spec.screw_length + self.screw_spec.gripper_length


def radius_function(
    z: float,
    *,
    pitch: float,
    start_radius: float,
    max_radius: float,
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
    p = bd.Part(None)

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
        ),
    )
    info = {
        "min_radius": _min_radius,
        "max_radius": _max_radius,
        "xy_radius_diff": _max_radius - _min_radius,
        "pin_move_up_amount": _max_radius - _min_radius,
        "pitch": spec.screw_pitch,
        "pitch/2": spec.screw_pitch / 2,
        "cone_angle_deg": cone_angle_deg,
        "total_length": spec.screw_length + 2 * spec.gripper_length,
    }
    logger.success(f"Wavy screw specs: {json.dumps(info, indent=2)}")

    # Create main screw shaft.
    p += bd.Cylinder(
        radius=spec.screw_od / 2,
        height=spec.screw_length,
        align=bde.align.ANCHOR_BOTTOM,
    ).translate((0, 0, -spec.ball_od / 2))  # Move down by jamming prevention amount.

    helix_points = insane_helix_points(
        start_radius=_min_radius,
        max_radius=_max_radius,
        pitch=spec.screw_pitch,
        # On height, subtract ball_od to prevent jamming/wedging.
        height=spec.screw_length - spec.ball_od,
        points_per_turn=spec.ball_points_per_turn,
    )

    helix_path = bd.Polyline(*helix_points)

    # Debugging: Helpful demo view.
    # show(helix_path)

    helix_part = bd.Part(None) + bd.sweep(
        path=helix_path,
        sections=(helix_path ^ 0) * bd.Circle(radius=spec.ball_od / 2),
        transition=bd.Transition.RIGHT,  # Use RIGHT because ROUND is not manifold.
    )
    # show(helix_part)
    assert helix_part.is_manifold, "Helix part is not manifold"
    p -= helix_part

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
        align=bde.align.ANCHOR_BOTTOM,
    ).translate((0, 0, screw_top_z))
    p += bd.Cylinder(
        radius=spec.gripper_od / 2,
        height=spec.gripper_length,
        align=bde.align.ANCHOR_BOTTOM,
        rotation=bde.rotation.NEG_Z,
    ).translate((0, 0, screw_bottom_z))

    # Remove the gripper bearing parts.
    gripper_groove = (
        bd.Part(None)
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


def make_housing(
    spec: HousingSpec,
    *,
    preview_screw: bool = False,
    print_in_place_screws: bool = False,
) -> bd.Part:
    """Make the housing that the screw fits into.

    Args:
        spec: The specification for the housing.
        preview_screw: Whether to preview the screw in the housing.
        print_in_place_screws: Whether to print the screws in place.
            Adds the screws, and keeps the screw install holes there.

    """
    p = bd.Part(None)

    # Create the main outer shell.
    p += bd.Box(
        spec.total_x,
        spec.total_y,
        spec.total_z,
        align=bde.align.ANCHOR_BOTTOM,
    )

    # Remove the inside of the housing.
    p -= bd.Box(
        spec.total_x - 2 * spec.wall_thickness,
        # spec.total_y - 2 * spec.wall_thickness,
        spec.screw_spec.screw_length,
        spec.body_height_where_screw_goes,
        align=bde.align.ANCHOR_BOTTOM,
    )

    # Remove the dots.
    for _cell_num, cell_center_x in enumerate(spec.get_x_of_center_of_cells()):
        for dot_x, dot_y in product(
            bde.evenly_space_with_center(count=2, spacing=spec.dot_pitch_x),
            bde.evenly_space_with_center(count=3, spacing=spec.dot_pitch_y),
        ):
            p -= bd.Cylinder(
                radius=spec.screw_spec.ball_od / 2,
                height=10,
                align=bde.align.ANCHOR_BOTTOM,
            ).translate(((cell_center_x + dot_x), dot_y, 0))

    # For each ball screw, remove the gripper holders.
    z_center_of_screw = (
        spec.dist_bottom_of_housing_to_bottom_of_screw + spec.screw_spec.screw_od / 2
    )
    wavy_screw_part = make_wavy_screw(spec.screw_spec).rotate(bd.Axis.X, 90)
    wavy_screw_part.color = bd.Color("red")
    for cell_center_x, dot_x in product(
        spec.get_x_of_center_of_cells(),
        bde.evenly_space_with_center(count=2, spacing=spec.dot_pitch_x),
    ):
        # Small hole through the whole thing.
        p -= (
            bd.Cylinder(
                radius=(
                    spec.screw_spec.gripper_od / 2
                    - spec.screw_spec.gripper_groove_depth
                    + spec.gripper_interface_freedom_radius
                ),
                height=spec.total_y,
                align=bde.align.ANCHOR_CENTER,
            )
            .rotate(axis=bd.Axis.X, angle=90)
            .translate(
                (
                    cell_center_x + dot_x,
                    0,
                    z_center_of_screw,
                ),
            )
        )

        # Screw OD.
        p -= (
            bd.Cylinder(
                radius=(
                    spec.screw_spec.screw_od / 2 + spec.gripper_interface_freedom_radius
                ),
                height=spec.screw_spec.screw_length,
                align=bde.align.ANCHOR_CENTER,
            )
            .rotate(axis=bd.Axis.X, angle=90)
            .translate(
                (
                    cell_center_x + dot_x,
                    0,
                    z_center_of_screw,
                ),
            )
        )

        # Large hole parts for the gripper.
        for y_side, y_offset in product([1, -1], [1, -1]):
            p -= (
                bd.Cylinder(
                    radius=(
                        spec.screw_spec.gripper_od / 2
                        + spec.gripper_interface_freedom_radius
                    ),
                    height=(
                        spec.screw_spec.gripper_groove_shoulder_length
                        + 2 * spec.gripper_interface_freedom_length
                    ),
                )
                .rotate(bd.Axis.X, 90)
                .translate(
                    (
                        cell_center_x + dot_x,
                        (
                            y_side
                            * (
                                spec.total_y / 2
                                - spec.screw_spec.gripper_length / 2
                                + y_offset
                                * (
                                    0.5 * spec.screw_spec.gripper_groove_length
                                    + 0.5
                                    * spec.screw_spec.gripper_groove_shoulder_length
                                )
                            )
                        ),
                        z_center_of_screw,
                    ),
                )
            )

        # Remove the insertion slot from the bottom.
        # One per cell.
        if not print_in_place_screws:
            p -= bd.Box(
                spec.screw_spec.gripper_od + spec.dot_pitch_x,
                spec.total_y,
                z_center_of_screw,
                align=bde.align.ANCHOR_BOTTOM,
            ).translate((cell_center_x, 0, 0))

        # Add a screw if we're doing print-in-place.
        if print_in_place_screws:
            p += wavy_screw_part.translate(
                (
                    cell_center_x + dot_x + 0.01,
                    -wavy_screw_part.bounding_box().center().Y,
                    (
                        spec.dist_bottom_of_housing_to_bottom_of_screw
                        + spec.screw_spec.screw_od / 2
                    ),
                ),
            )

    # Preview: Add the screw to the housing.
    if preview_screw:
        p += wavy_screw_part.translate(
            (
                spec.dot_pitch_x / 2 + 0.01,
                -wavy_screw_part.bounding_box().center().Y,
                (
                    spec.dist_bottom_of_housing_to_bottom_of_screw
                    + spec.screw_spec.screw_od / 2
                ),
            ),
        )

    return p


def make_2x_wavy_screw(spec: ScrewSpec) -> bd.Part:
    """Make 2x wavy screws side-by-side for imaging."""
    p = bd.Part(None)

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
        "wavy_screw": (make_wavy_screw(ScrewSpec())),
        "housing": show(
            make_housing(
                HousingSpec(screw_spec=ScrewSpec()),
            )
        ),
        "housing_and_screws_in_place": show(
            make_housing(
                HousingSpec(screw_spec=ScrewSpec()),
                print_in_place_screws=True,
            )
        ),
        "housing_assembly_with_screw": (
            make_housing(
                HousingSpec(screw_spec=ScrewSpec()),
                preview_screw=True,
            )
        ),
        "demo_2x_wavy_screw": (make_2x_wavy_screw(ScrewSpec())),
    }

    logger.info("Saving CAD model(s)...")

    (
        export_folder := Path(__file__).parent.parent / "build" / Path(__file__).stem
    ).mkdir(
        exist_ok=True,
        parents=True,
    )
    for name, part in parts.items():
        bd.export_stl(part, str(export_folder / f"{name}.stl"))
        bd.export_step(part, str(export_folder / f"{name}.step"))

    logger.info(f"Done running {py_file_name} in {datetime.now(UTC) - start_time}")
