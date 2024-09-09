import build123d as bd


def float_range(start: float, stop: float, step: float):
    while start < stop:
        # Round to avoid floating-point precision issues
        yield round(start, 10)
        start += step


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
