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
    DROOPY = 1
    FROWN = 2
    CHEERFUL = 3
    SQUINT = 4
    CLOSED = 5
    # TODO: Add special FX-based shapes for anime chibi style:
    # HEART = 6  # Heart eyes for love/affection (😘, ❤️, 🥰, 🤗)
    # STAR = 7   # Star eyes for excited/happy (👍, 👌, 🤩, 🥳, 🌹, ✌️)


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
    # TODO: Add special FX-based animations for anime chibi style:
    # bounce = 9   # Cheerful bounce (👍, ❤️, 🤩, 🥰)
    # sway = 10      # Affectionate sway (😘, ❤️, 🤗)
    # sparkle = 11 # Star twinkle (👌, 🥳, 🌹)
    # wave = 12     # Greeting wave (👋)
    # peace = 13    # Victory peace sign (✌️)
    # glow = 14     # Angelic halo ring (🌹)
    # tears = 15     # Tear drops (😭)
    # dizzy = 16     # Poop confused spin (💩)
    # TODO: Add temporary color override for animations (temp_color in RoboEyes)
    # Implement set_temp_color(color) and clear_temp_color() methods
    # Modify renderer to check for temp_color before drawing
    # Update anim_* methods to set/clear temp color as needed


SHAPE_MAP: dict[str, Shape] = {
    "default": Shape.DEFAULT,
    "tired": Shape.DROOPY,
    "frown": Shape.FROWN,
    "cheerful": Shape.CHEERFUL,
    "squint": Shape.SQUINT,
    "closed": Shape.CLOSED,
}
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
