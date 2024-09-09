import os
from pathlib import Path  # noqa: F401

import build123d as bd

from cad_lib import make_curved_bent_cylinder, make_angled_cylinders


if os.getenv("CI"):

    def show(*args):
        return print(f"Skipping show({args}) in CI")
else:
    from ocp_vscode import show


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
    parts = {
        "demo_test_pipe_bend": demo_test_pipe_bend(),
        "demo_test_make_curved_bent_cylinder": demo_test_make_curved_bent_cylinder(),
        "demo_test_make_angled_cylinders": demo_test_make_angled_cylinders(),
    }

    print("Made CAD model(s)")

    print("Showing CAD model(s)")
    for part in parts.values():
        show(part)

    # (export_folder := Path(__file__).parent.with_name("build")).mkdir(exist_ok=True)
    # for name, part in parts.items():
    #     bd.export_stl(part, str(export_folder / f"{name}.stl"))
    #     bd.export_step(part, str(export_folder / f"{name}.step"))
