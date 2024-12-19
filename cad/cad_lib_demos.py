"""Demonstrates the CAD library functions."""

from pathlib import Path

import build123d as bd
from build123d_ease import show
from cad_lib import make_angled_cylinders, make_curved_bent_cylinder
from loguru import logger


def demo_test_pipe_bend() -> bd.Part:
    """Make a pipe bend, by creating a swept line and a sweep polygon."""
    # Lesson learned: The swept line must start at the origin, and
    # the sweep polygon must be centered at the origin, normal to the sweep path at the
    # origin.

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
    assert isinstance(sweep_polygon, bd.SweepType)  # Type checking.
    line_sum = bd.sweep(sweep_polygon, path=line_sum)

    line_sum = line_sum.translate(line1.start_point())
    assert isinstance(line_sum, bd.Part)  # Type checking.
    return line_sum


def demo_test_make_curved_bent_cylinder() -> bd.Part:
    """Make a curved bent cylinder using the applicable function."""
    return make_curved_bent_cylinder(
        diameter=0.5,
        vertical_seg_length=4,
        horizontal_seg_length=5,
        bend_radius=1,
    )


def demo_test_make_angled_cylinders() -> bd.Part:
    """Make angled cylinders using the applicable function."""
    return make_angled_cylinders(
        diameter=0.5,
        vertical_seg_length=4,
        horizontal_seg_length=5,
        horizontal_angle=-30,
    )


if __name__ == "__main__":
    parts = {
        "demo_test_pipe_bend": show(demo_test_pipe_bend()),
        "demo_test_make_curved_bent_cylinder": demo_test_make_curved_bent_cylinder(),
        "demo_test_make_angled_cylinders": demo_test_make_angled_cylinders(),
    }

    logger.info("Saving CAD model(s)...")

    (
        export_folder := Path(__file__).parent.parent / "build" / Path(__file__).stem
    ).mkdir(exist_ok=True, parents=True)
    for name, part in parts.items():
        bd.export_stl(part, str(export_folder / f"{name}.stl"))
        bd.export_step(part, str(export_folder / f"{name}.step"))
