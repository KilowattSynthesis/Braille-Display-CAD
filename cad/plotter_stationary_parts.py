"""Create CAD models for the plotter's stationary parts.

Stationary parts are mounted to the PCB.


Future options:
- Solder motor directly into the PCB.
"""

import itertools
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import build123d as bd
import build123d_ease as bde
from build123d_ease import show
from loguru import logger

# Constants. All distances are in mm.


@dataclass
class NutSpec:
    """Dimensions for any nut."""

    width: float
    thickness: float
    m_diameter: float


@dataclass
class Spec:
    """Dimensions for any part."""

    # PM15S Stepper Motor
    # https://nmbtc.com/wp-content/uploads/parts/documents/PM15%20data%20sheet.pdf
    motor_mount_hole_spacing = 20
    motor_mount_hole_d: float = 1.8  # Use thread-forming screws.

    motor_main_d = 15
    motor_shaft_clearance_d = 6 + 1


if __name__ == "__main__":
    parts = {
        "nut_holder_M1p6_From_Top": show(
            make_nut_holder(
                NutHolderSpec(
                    nut=m1p6_nut,
                )
            )
        ),
    }

    logger.info("Saving CAD model(s)")

    (export_folder := Path(__file__).parent.with_name("build")).mkdir(exist_ok=True)
    for name, part in parts.items():
        assert isinstance(part, bd.Part), f"{name} is not a Part"
        # assert part.is_manifold is True, f"{name} is not manifold"

        bd.export_stl(part, str(export_folder / f"{name}.stl"))
        bd.export_step(part, str(export_folder / f"{name}.step"))
