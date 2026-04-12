"""Shared types, enums, constants, and data structures for RoboEyes."""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum

Color = tuple[int, int, int]

DEFAULT_BGCOLOR: Color = (0, 0, 0)
DEFAULT_MAINCOLOR: Color = (0, 255, 255)

MAX_UDP_MESSAGES_PER_FRAME: int = 10


class Shape(IntEnum):
    """Eye shape expressions."""

    DEFAULT = 0
    TIRED = 1
    ANGRY = 2
    SMILE = 3
    SQUINT = 4
    SLEEP = 5


class Position(IntEnum):
    """Eye gaze directions."""

    CENTER = 0
    N = 1
    NE = 2
    E = 3
    SE = 4
    S = 5
    SW = 6
    W = 7
    NW = 8


SHAPE_MAP: dict[str, Shape] = {s.name.lower(): s for s in Shape}
POSITION_MAP: dict[str, Position] = {p.name.lower(): p for p in Position}

POSITION_FACTORS: dict[Position, tuple[float, float]] = {
    Position.CENTER: (0.5, 0.5),
    Position.N:      (0.5, 0.0),
    Position.NE:     (1.0, 0.0),
    Position.E:      (1.0, 0.5),
    Position.SE:     (1.0, 1.0),
    Position.S:      (0.5, 1.0),
    Position.SW:     (0.0, 1.0),
    Position.W:      (0.0, 0.5),
    Position.NW:     (0.0, 0.0),
}


@dataclass
class EyeState:
    """Holds the geometry and animation state for a single eye."""

    width_default: int = 0
    height_default: int = 0
    width_current: int = 0
    height_current: int = 1
    width_next: int = 0
    height_next: int = 0
    height_offset: int = 0
    border_radius_default: int = 0
    border_radius_current: int = 0
    border_radius_next: int = 0
    x: int = 0
    y: int = 0
    x_default: int = 0
    y_default: int = 0
    x_next: int = 0
    y_next: int = 0
    is_open: bool = False
