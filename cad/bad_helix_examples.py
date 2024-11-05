"""Create CAD models for the braille display parts."""

import os

import build123d as bd
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


def make_helix() -> bd.Helix:
    """Make basic helix."""
    return bd.Helix(
        radius=2,
        pitch=1,
        height=10,
        cone_angle=0,
    )


def make_helix_sweep() -> bd.Part:
    """Make basic helix sweep."""
    p = bd.Part()
    helix = make_helix()
    p += bd.sweep(
        path=helix,
        sections=((helix ^ 0) * bd.Circle(radius=0.3)),
        transition=bd.Transition.ROUND,
    )
    return p


def spring_demo() -> bd.Part:
    """Construct a "spring" using a helix sweep of a circle."""
    p = bd.Part()
    helix = bd.Helix(radius=2, pitch=1, height=10, cone_angle=0)
    p += bd.sweep(
        path=helix,
        sections=((helix ^ 0) * bd.Circle(radius=0.3)),
    )
    return p


def make_helix_extrude_linear_with_rotation() -> bd.Part:
    """Make basic helix extrude linear with rotation."""
    p = bd.Part()

    helix = make_helix()

    p += bd.Solid.extrude_linear_with_rotation(
        center=helix,
        normal=helix,
        section=bd.Circle(radius=1).wire(),
        angle=270,
    )
    return p


if __name__ == "__main__":
    # show(make_helix())
    # show(make_helix_sweep())
    # show(make_helix_extrude_linear_with_rotation())
    show(spring_demo())
