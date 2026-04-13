"""UDP command parsing and dispatch."""

from __future__ import annotations

import argparse
from collections.abc import Callable
from typing import Any

from roboeyes.eyes import RoboEyes
from roboeyes.types import Color, SHAPE_MAP, POSITION_MAP


def parse_color(s: str) -> Color:
    """Parses an ``R,G,B`` string into a color tuple."""
    parts = s.split(",")
    if len(parts) != 3:
        raise argparse.ArgumentTypeError("Color must be R,G,B (e.g. 255,255,255)")
    r, g, b = (int(x) for x in parts)
    return (r, g, b)


def validate_color(value: Any) -> Color | None:
    """Validates a color value from UDP JSON input."""
    if not isinstance(value, list) or len(value) != 3:
        return None
    if not all(isinstance(c, int) and 0 <= c <= 255 for c in value):
        return None
    return (value[0], value[1], value[2])


def handle_command(cmd: Any, robo_eyes: RoboEyes) -> None:
    """Handles a JSON command dict from UDP with input validation.

    Silently ignores malformed or unrecognized fields so that one bad
    field does not prevent the rest of the command from being processed.
    """
    if not isinstance(cmd, dict):
        return

    if "shape" in cmd and isinstance(cmd["shape"], str):
        shape = SHAPE_MAP.get(cmd["shape"].lower())
        if shape is not None:
            robo_eyes.set_shape(shape)

    if "look" in cmd and isinstance(cmd["look"], str):
        pos = POSITION_MAP.get(cmd["look"].lower())
        if pos is not None:
            robo_eyes.set_position(pos)

    if "anim" in cmd and isinstance(cmd["anim"], str):
        anim = cmd["anim"].lower()
        anim_map: dict[str, Callable[[], None]] = {
            "confused": robo_eyes.anim_confused,
            "laugh": robo_eyes.anim_laugh,
            "sleep": robo_eyes.anim_sleep,
            "breathing": robo_eyes.anim_breathing,
            "blink": robo_eyes.blink,
            "wink_left": robo_eyes.wink_left,
            "wink_right": robo_eyes.wink_right,
        }
        fn = anim_map.get(anim)
        if fn:
            fn()

    if "color" in cmd:
        color = validate_color(cmd["color"])
        if color:
            robo_eyes.eye_color = color

    if "temp_color" in cmd:
        if cmd["temp_color"] is None:
            robo_eyes.clear_temp_color()
        else:
            color = validate_color(cmd["temp_color"])
            if color:
                robo_eyes.set_temp_color(color)

    if "bgcolor" in cmd:
        color = validate_color(cmd["bgcolor"])
        if color:
            robo_eyes.bg_color = color

    if "cyclops" in cmd and isinstance(cmd["cyclops"], bool):
        robo_eyes.set_cyclops(cmd["cyclops"])
    if "idle" in cmd and isinstance(cmd["idle"], bool):
        robo_eyes.set_idle_mode(cmd["idle"])
    if "autoblink" in cmd and isinstance(cmd["autoblink"], bool):
        robo_eyes.set_autoblinker(cmd["autoblink"])
