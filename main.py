"""RoboEyes - Animated robot eyes display with remote control support.

Usage:
    uv run main.py [OPTIONS]

Options:
    --rotate {0,90,180,270}   Screen rotation in degrees (default: 0)
    --port PORT               UDP port for remote commands (default: 5005)
    --bind ADDRESS            Bind address for UDP (default: 127.0.0.1)
    --color R,G,B             Eye color (default: 0,255,255)
    --bgcolor R,G,B           Background color (default: 0,0,0)
    --width WIDTH             Canvas width in pixels (default: 640)
    --height HEIGHT           Canvas height in pixels (default: 480)
    --fullscreen              Run in fullscreen mode

Keyboard Controls:
    Esc         Quit
    0/1/2/3/4   Shape: default / tired / angry / smile / squint
    Arrow keys  Look direction (up/down/left/right)
    Space       Reset look to center
    b           Blink
    q           Wink left
    e           Wink right
    c           Confused animation
    l           Laugh animation
    f           Toggle fullscreen
    ?           Toggle key bindings overlay

UDP Remote Commands (JSON):
    Send JSON to the configured UDP port to control the eyes remotely.

    {"shape": "smile"}                   Set shape (default/tired/angry/smile/squint)
    {"look": "e"}                       Look direction (n/ne/e/se/s/sw/w/nw/center)
    {"anim": "laugh"}                   Trigger animation (confused/laugh/blink/wink_left/wink_right)
    {"color": [0, 200, 255]}            Set eye color [R, G, B]
    {"bgcolor": [20, 20, 40]}           Set background color [R, G, B]
    {"cyclops": true}                   Toggle single-eye mode
    {"idle": true}                      Toggle idle random movement
    {"autoblink": true}                 Toggle automatic blinking

    Commands can be combined: {"shape": "angry", "look": "e", "color": [255, 50, 50]}

    Example:
        echo '{"shape":"smile","look":"w"}' | nc -u 127.0.0.1 5005
"""

from __future__ import annotations

import argparse
import json
import math
import random
import socket
from collections.abc import Callable
from dataclasses import dataclass
from enum import IntEnum
from typing import Any

import pygame

Color = tuple[int, int, int]

DEFAULT_BGCOLOR: Color = (0, 0, 0)
DEFAULT_MAINCOLOR: Color = (0, 255, 255)

MAX_UDP_MESSAGES_PER_FRAME: int = 10

KEY_BINDINGS_LINES: list[str] = [
    "Key Bindings",
    "",
    "Esc         Quit",
    "0           Shape: default",
    "1           Shape: tired",
    "2           Shape: angry",
    "3           Shape: smile",
    "4           Shape: squint",
    "Arrows      Look direction",
    "Space       Center look",
    "b           Blink",
    "q           Wink left",
    "e           Wink right",
    "c           Confused",
    "l           Laugh",
    "f           Fullscreen",
    "?           Toggle help",
]


class Shape(IntEnum):
    """Eye shape expressions."""

    DEFAULT = 0
    TIRED = 1
    ANGRY = 2
    SMILE = 3
    SQUINT = 4


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
    """Holds the geometry and animation state for a single eye.

    Attributes:
        width_default: Default eye width in pixels.
        height_default: Default eye height in pixels.
        width_current: Current animated eye width.
        height_current: Current animated eye height.
        width_next: Target eye width for lerp.
        height_next: Target eye height for lerp.
        height_offset: Additional height from curiosity mode.
        border_radius_default: Default corner radius.
        border_radius_current: Current animated corner radius.
        border_radius_next: Target corner radius for lerp.
        x: Current X position on screen.
        y: Current Y position on screen.
        x_default: Default X position.
        y_default: Default Y position.
        x_next: Target X position for lerp.
        y_next: Target Y position for lerp.
        is_open: Whether the eye should re-open after closing.
    """

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


class RoboEyes:
    """Animated robot eyes display with shape, position, and animation support."""

    def __init__(
        self,
        draw_surface: pygame.Surface,
        width: int = 640,
        height: int = 480,
        bg_color: Color = DEFAULT_BGCOLOR,
        eye_color: Color = DEFAULT_MAINCOLOR,
    ) -> None:
        """Initializes the RoboEyes display.

        Args:
            draw_surface: Pygame surface to draw on.
            width: Canvas width in pixels (unrotated).
            height: Canvas height in pixels (unrotated).
            bg_color: Background color as (R, G, B).
            eye_color: Eye color as (R, G, B).
        """
        self.surface: pygame.Surface = draw_surface
        self.screen_width: int = width
        self.screen_height: int = height
        self.bg_color: Color = bg_color
        self.eye_color: Color = eye_color

        # Shape flags
        self.current_shape: Shape = Shape.DEFAULT
        self.tired: bool = False
        self.angry: bool = False
        self.happy: bool = False
        self.curious: bool = False
        self.squint: bool = False
        self.cyclops: bool = False

        # Scale factor relative to reference resolution (320x240)
        # Eye sizes and spacing are defined at 320x240 and scaled up
        self.scale: float = min(width / 320, height / 240)

        # Eye geometry
        self.space_between_default: int = int(10 * self.scale)
        self.space_between_current: int = self.space_between_default
        self.space_between_next: int = self.space_between_default

        eye_w: int = int(100 * self.scale)
        eye_h: int = int(100 * self.scale)
        border_r: int = int(20 * self.scale)

        self.left: EyeState = EyeState(
            width_default=eye_w, height_default=eye_h,
            width_current=eye_w, height_current=1,
            width_next=eye_w, height_next=eye_h,
            border_radius_default=border_r,
            border_radius_current=border_r,
            border_radius_next=border_r,
        )
        self.right: EyeState = EyeState(
            width_default=eye_w, height_default=eye_h,
            width_current=eye_w, height_current=1,
            width_next=eye_w, height_next=eye_h,
            border_radius_default=border_r,
            border_radius_current=border_r,
            border_radius_next=border_r,
        )

        # Default positions
        self.left.x_default = (self.screen_width - (eye_w + self.space_between_default + eye_w)) // 2
        self.left.y_default = (self.screen_height - eye_h) // 2
        self.left.x = self.left.x_default
        self.left.y = self.left.y_default
        self.left.x_next = self.left.x
        self.left.y_next = self.left.y

        self.right.x_default = self.left.x + self.left.width_current + self.space_between_default
        self.right.y_default = self.left.y
        self.right.x = self.right.x_default
        self.right.y = self.right.y_default
        self.right.x_next = self.right.x
        self.right.y_next = self.right.y

        # Eyelid state
        self.eyelids_tired_height: int = 0
        self.eyelids_tired_height_next: int = 0
        self.eyelids_angry_height: int = 0
        self.eyelids_angry_height_next: int = 0
        self.eyelids_happy_bottom_offset: int = 0
        self.eyelids_happy_bottom_offset_next: int = 0

        # Flicker animations
        self.h_flicker: bool = False
        self.h_flicker_alternate: bool = False
        self.h_flicker_amplitude: int = int(4 * self.scale)

        self.v_flicker: bool = False
        self.v_flicker_alternate: bool = False
        self.v_flicker_amplitude: int = int(20 * self.scale)

        # Auto-blinker
        self.autoblinker: bool = False
        self.blink_interval: int = 2000
        self.blink_interval_variation: int = 4000
        self.blink_timer: int = pygame.time.get_ticks()

        # Idle mode
        self.idle: bool = False
        self.idle_interval: int = 5000
        self.idle_interval_variation: int = 5000
        self.idle_animation_timer: int = pygame.time.get_ticks()

        # Wink tracking (distinguishes intentional wink from normal blink)
        self._winking: bool = False

        # Confused animation
        self.confused: bool = False
        self.confused_animation_timer: int = 0
        self.confused_animation_duration: int = 500
        self.confused_toggle: bool = True

        # Laugh animation
        self.laugh: bool = False
        self.laugh_animation_timer: int = 0
        self.laugh_animation_duration: int = 500
        self.laugh_toggle: bool = True

    def begin(self) -> None:
        """Initializes the display and starts with eyes closed."""
        self.clear_display()
        self.left.height_current = 1
        self.right.height_current = 1

    def update(self) -> None:
        """Runs one frame of the eye animation loop."""
        self._draw_eyes()

    def set_width(self, left_eye: int, right_eye: int) -> None:
        """Sets the default and target width for both eyes.

        Args:
            left_eye: Width in pixels for the left eye.
            right_eye: Width in pixels for the right eye.
        """
        self.left.width_next = left_eye
        self.right.width_next = right_eye
        self.left.width_default = left_eye
        self.right.width_default = right_eye

    def set_height(self, left_eye: int, right_eye: int) -> None:
        """Sets the default and target height for both eyes.

        Args:
            left_eye: Height in pixels for the left eye.
            right_eye: Height in pixels for the right eye.
        """
        self.left.height_next = left_eye
        self.right.height_next = right_eye
        self.left.height_default = left_eye
        self.right.height_default = right_eye

    def set_border_radius(self, left_eye: int, right_eye: int) -> None:
        """Sets the default and target border radius for both eyes.

        Args:
            left_eye: Border radius in pixels for the left eye.
            right_eye: Border radius in pixels for the right eye.
        """
        self.left.border_radius_next = left_eye
        self.right.border_radius_next = right_eye
        self.left.border_radius_default = left_eye
        self.right.border_radius_default = right_eye

    def set_space_between(self, space: int) -> None:
        """Sets the default and target spacing between eyes.

        Args:
            space: Space in pixels between left and right eyes.
        """
        self.space_between_next = space
        self.space_between_default = space

    def set_shape(self, shape: Shape) -> None:
        """Sets current shape expression.

        Args:
            shape: The shape to display.
        """
        self.current_shape = shape
        self.tired = shape == Shape.TIRED
        self.angry = shape == Shape.ANGRY
        self.happy = shape == Shape.SMILE
        self.squint = shape == Shape.SQUINT

    def set_position(self, position: Position) -> None:
        """Sets the gaze direction using a compass position.

        Args:
            position: The direction to look toward.
        """
        fx, fy = POSITION_FACTORS[position]
        self.left.x_next = int(self._screen_constraint_x() * fx)
        self.left.y_next = int(self._screen_constraint_y() * fy)

    def set_autoblinker(self, active: bool, interval: int = 2, variation: int = 4) -> None:
        """Configures automated eye blinking.

        Args:
            active: Whether to enable automatic blinking.
            interval: Base interval between blinks in seconds.
            variation: Random variation range in seconds added to interval.
        """
        self.autoblinker = active
        self.blink_interval = interval * 1000
        self.blink_interval_variation = variation * 1000

    def set_idle_mode(self, active: bool, interval: int = 5, variation: int = 5) -> None:
        """Configures idle mode for random eye repositioning.

        Args:
            active: Whether to enable idle movement.
            interval: Base interval between movements in seconds.
            variation: Random variation range in seconds added to interval.
        """
        self.idle = active
        self.idle_interval = interval * 1000
        self.idle_interval_variation = variation * 1000

    def set_curiosity(self, curious_bit: bool) -> None:
        """Enables or disables curiosity mode.

        When enabled, eyes grow taller when looking toward screen edges.

        Args:
            curious_bit: Whether to enable curiosity mode.
        """
        self.curious = curious_bit

    def set_cyclops(self, cyclops_bit: bool) -> None:
        """Enables or disables cyclops (single-eye) mode.

        Args:
            cyclops_bit: Whether to enable cyclops mode.
        """
        self.cyclops = cyclops_bit

    def set_h_flicker(self, flicker_bit: bool, amplitude: int = 4) -> None:
        """Enables or disables horizontal flicker animation.

        Args:
            flicker_bit: Whether to enable horizontal flicker.
            amplitude: Flicker displacement in pixels.
        """
        self.h_flicker = flicker_bit
        self.h_flicker_amplitude = amplitude

    def set_v_flicker(self, flicker_bit: bool, amplitude: int = 20) -> None:
        """Enables or disables vertical flicker animation.

        Args:
            flicker_bit: Whether to enable vertical flicker.
            amplitude: Flicker displacement in pixels.
        """
        self.v_flicker = flicker_bit
        self.v_flicker_amplitude = amplitude

    def close(self, left: bool = True, right: bool = True) -> None:
        """Closes the specified eyes by setting their height target to 1.

        Args:
            left: Whether to close the left eye.
            right: Whether to close the right eye.
        """
        if left:
            self.left.height_next = 1
            self.left.is_open = False
        if right:
            self.right.height_next = 1
            self.right.is_open = False

    def open_eyes(self, left: bool = True, right: bool = True) -> None:
        """Marks the specified eyes to re-open after closing.

        Args:
            left: Whether to re-open the left eye.
            right: Whether to re-open the right eye.
        """
        if left:
            self.left.is_open = True
        if right:
            self.right.is_open = True

    def blink(self, left: bool = True, right: bool = True) -> None:
        """Triggers a blink animation (close then re-open).

        Args:
            left: Whether to blink the left eye.
            right: Whether to blink the right eye.
        """
        self.close(left, right)
        self.open_eyes(left, right)

    def wink_left(self) -> None:
        """Triggers a wink with the left eye only."""
        self._winking = True
        self.blink(left=True, right=False)

    def wink_right(self) -> None:
        """Triggers a wink with the right eye only."""
        self._winking = True
        self.blink(left=False, right=True)

    def anim_confused(self) -> None:
        """Triggers the confused (horizontal shake) animation."""
        self.confused = True

    def anim_laugh(self) -> None:
        """Triggers the laugh (vertical bounce) animation."""
        self.laugh = True

    def clear_display(self) -> None:
        """Fills the draw surface with the background color."""
        self.surface.fill(self.bg_color)

    # -- Private helpers --

    def _lerp(self, current: int, target: int) -> int:
        """Smoothly interpolates an integer value toward a target.

        Uses halving with a nudge to guarantee convergence even when
        integer division would otherwise stall.

        Args:
            current: The current value.
            target: The target value to move toward.

        Returns:
            The next interpolated value.
        """
        if current == target:
            return current
        mid = (current + target) // 2
        if mid == current:
            return target
        return mid

    def _screen_constraint_x(self) -> int:
        """Returns the maximum X offset for the left eye position."""
        return self.screen_width - self.left.width_current - self.space_between_current - self.right.width_current

    def _screen_constraint_y(self) -> int:
        """Returns the maximum Y offset for eye positioning."""
        return self.screen_height - self.left.height_default

    def _update_eye_geometry(self, eye: EyeState) -> None:
        """Advances a single eye's dimensions and position toward their targets.

        Args:
            eye: The eye state to update in place.
        """
        eye.height_current = self._lerp(eye.height_current, eye.height_next + eye.height_offset)
        eye.width_current = self._lerp(eye.width_current, eye.width_next)
        eye.border_radius_current = self._lerp(eye.border_radius_current, eye.border_radius_next)

        # Compute Y target: center-adjust for current height, then offset
        target_y = eye.y_next + (eye.height_default - eye.height_current) // 2
        target_y -= eye.height_offset // 2
        eye.y = self._lerp(eye.y, target_y)

        eye.x = self._lerp(eye.x, eye.x_next)

        # Re-open after close animation completes
        if eye.is_open and eye.height_current <= 1 + eye.height_offset:
            eye.height_next = eye.height_default

    def _compute_curiosity_offsets(self) -> None:
        """Sets height offsets on both eyes based on gaze position.

        Eyes grow taller when looking toward the edges of the screen,
        creating a curious expression.
        """
        threshold: int = int(20 * self.scale)
        offset: int = int(16 * self.scale)

        if self.curious:
            if self.left.x_next <= threshold:
                self.left.height_offset = offset
            elif self.left.x_next >= (self._screen_constraint_x() - threshold) and self.cyclops:
                self.left.height_offset = offset
            else:
                self.left.height_offset = 0

            if self.right.x_next >= self.screen_width - self.right.width_current - threshold:
                self.right.height_offset = offset
            else:
                self.right.height_offset = 0
        else:
            self.left.height_offset = 0
            self.right.height_offset = 0

    def _draw_eyes(self) -> None:
        """Main drawing routine that updates state and renders one frame."""
        current_time: int = pygame.time.get_ticks()

        self._compute_curiosity_offsets()

        # Update geometry for both eyes
        self._update_eye_geometry(self.left)

        # Right eye tracks left eye position
        self.right.x_next = self.left.x_next + self.left.width_current + self.space_between_current
        self.right.y_next = self.left.y_next
        self._update_eye_geometry(self.right)

        # Space between eyes
        self.space_between_current = self._lerp(self.space_between_current, self.space_between_next)

        # Auto-blinker
        if self.autoblinker and current_time >= self.blink_timer:
            self.blink()
            variation = random.randint(0, self.blink_interval_variation)
            self.blink_timer = current_time + self.blink_interval + variation

        # Laugh animation
        if self.laugh:
            if self.laugh_toggle:
                self.set_v_flicker(True, int(10 * self.scale))
                self.laugh_animation_timer = current_time
                self.laugh_toggle = False
            elif current_time >= self.laugh_animation_timer + self.laugh_animation_duration:
                self.set_v_flicker(False, 0)
                self.laugh_toggle = True
                self.laugh = False

        # Confused animation
        if self.confused:
            if self.confused_toggle:
                self.set_h_flicker(True, int(40 * self.scale))
                self.confused_animation_timer = current_time
                self.confused_toggle = False
            elif current_time >= self.confused_animation_timer + self.confused_animation_duration:
                self.set_h_flicker(False, 0)
                self.confused_toggle = True
                self.confused = False

        # Idle animation
        if self.idle and current_time >= self.idle_animation_timer:
            self.left.x_next = random.randint(0, self._screen_constraint_x())
            self.left.y_next = random.randint(0, self._screen_constraint_y())
            variation = random.randint(0, self.idle_interval_variation)
            self.idle_animation_timer = current_time + self.idle_interval + variation

        # Horizontal flicker
        if self.h_flicker:
            amp: int = self.h_flicker_amplitude if self.h_flicker_alternate else -self.h_flicker_amplitude
            self.left.x += amp
            self.right.x += amp
            self.h_flicker_alternate = not self.h_flicker_alternate

        # Vertical flicker
        if self.v_flicker:
            amp = self.v_flicker_amplitude if self.v_flicker_alternate else -self.v_flicker_amplitude
            self.left.y += amp
            self.right.y += amp
            self.v_flicker_alternate = not self.v_flicker_alternate

        # Cyclops mode
        if self.cyclops:
            self.right.width_current = 0
            self.right.height_current = 0
            self.space_between_current = 0

        # Squint: tighter gap
        if self.squint:
            self.space_between_current = min(self.space_between_current, int(8 * self.scale))

        self.clear_display()

        # Determine squint/wink rendering
        left_blinking: bool = self.left.height_current < self.left.height_default - 2
        right_blinking: bool = self.right.height_current < self.right.height_default - 2

        left_use_squint: bool = self.squint and not left_blinking
        right_use_squint: bool = self.squint and not right_blinking

        # During an intentional wink, the open eye shows squint
        if self._winking and left_blinking != right_blinking:
            if not self.squint:
                left_use_squint = not left_blinking
                right_use_squint = not right_blinking

        # Clear wink flag once both eyes are fully open
        if self._winking and not left_blinking and not right_blinking:
            self._winking = False

        # Draw left eye
        if left_use_squint:
            self._draw_x_eye(self.left, "left")
        else:
            self._draw_eye(self.left)

        # Draw right eye
        if not self.cyclops:
            if right_use_squint:
                self._draw_x_eye(self.right, "right")
            else:
                self._draw_eye(self.right)

        # Shape eyelid overlays (skip when squint is active)
        if not left_use_squint and not right_use_squint:
            self._draw_eyelids()

    def _draw_eye(self, eye: EyeState) -> None:
        """Draws a single rounded-rectangle eye.

        Args:
            eye: The eye state containing position and dimensions.
        """
        rect = pygame.Rect(eye.x, eye.y, eye.width_current, eye.height_current)
        pygame.draw.rect(self.surface, self.eye_color, rect,
                         border_radius=max(eye.border_radius_current, 0))

    def _draw_x_eye(self, eye: EyeState, direction: str = "left") -> None:
        """Draws a squint eye as a ``>`` or ``<`` shape using rotated rectangles.

        Args:
            eye: The eye state containing position and dimensions.
            direction: ``"left"`` for ``<`` or ``"right"`` for ``>``.
        """
        cx: int = eye.x + eye.width_current // 2
        cy: int = eye.y + eye.height_current // 2
        sx: int = min(eye.width_current, eye.height_current) // 2
        sy: int = sx * 2 // 3
        t: int = max(sx // 2, 5)
        br: int = t // 2

        for sign in (-1, 1):
            if direction == "left":
                x1, y1 = cx - sx, cy + sign * sy
                x2, y2 = cx + sx, cy
            else:
                x1, y1 = cx + sx, cy + sign * sy
                x2, y2 = cx - sx, cy

            dx: int = x2 - x1
            dy: int = y2 - y1
            length: int = int(math.hypot(dx, dy))
            angle: float = math.degrees(math.atan2(-dy, dx))

            arm = pygame.Surface((length, t), pygame.SRCALPHA)
            pygame.draw.rect(arm, self.eye_color, (0, 0, length, t), border_radius=br)

            rotated = pygame.transform.rotate(arm, angle)
            mid_x: int = (x1 + x2) // 2
            mid_y: int = (y1 + y2) // 2
            rect = rotated.get_rect(center=(mid_x, mid_y))
            self.surface.blit(rotated, rect)

    def _draw_eyelids(self) -> None:
        """Draws shape-based eyelid overlays (tired, angry, smile)."""
        if self.tired:
            self.eyelids_tired_height_next = self.left.height_current // 2
            self.eyelids_angry_height_next = 0
        elif self.angry:
            self.eyelids_angry_height_next = self.left.height_current // 2
            self.eyelids_tired_height_next = 0
        else:
            self.eyelids_tired_height_next = 0
            self.eyelids_angry_height_next = 0

        if self.happy:
            self.eyelids_happy_bottom_offset_next = self.left.height_current * 2 // 3
        else:
            self.eyelids_happy_bottom_offset_next = 0

        # Tired eyelids
        self.eyelids_tired_height = self._lerp(self.eyelids_tired_height, self.eyelids_tired_height_next)
        if self.eyelids_tired_height > 0:
            if not self.cyclops:
                self._draw_tired_eyelid_pair(self.left, self.right)
            else:
                self._draw_tired_eyelid_cyclops(self.left)

        # Angry eyelids
        self.eyelids_angry_height = self._lerp(self.eyelids_angry_height, self.eyelids_angry_height_next)
        if self.eyelids_angry_height > 0:
            if not self.cyclops:
                self._draw_angry_eyelid_pair(self.left, self.right)
            else:
                self._draw_angry_eyelid_cyclops(self.left)

        # Happy eyelids
        self.eyelids_happy_bottom_offset = self._lerp(
            self.eyelids_happy_bottom_offset, self.eyelids_happy_bottom_offset_next)
        if self.eyelids_happy_bottom_offset > 0:
            self._draw_happy_eyelid(self.left)
            if not self.cyclops:
                self._draw_happy_eyelid(self.right)

    def _draw_tired_eyelid_pair(self, left: EyeState, right: EyeState) -> None:
        """Draws tired eyelid triangles for both eyes in normal mode.

        Args:
            left: Left eye state.
            right: Right eye state.
        """
        h: int = self.eyelids_tired_height
        points_left = [
            (left.x, left.y - 1),
            (left.x + left.width_current, left.y - 1),
            (left.x, left.y + h - 1),
        ]
        pygame.draw.polygon(self.surface, self.bg_color, points_left)

        points_right = [
            (right.x, right.y - 1),
            (right.x + right.width_current, right.y - 1),
            (right.x + right.width_current, right.y + h - 1),
        ]
        pygame.draw.polygon(self.surface, self.bg_color, points_right)

    def _draw_tired_eyelid_cyclops(self, eye: EyeState) -> None:
        """Draws tired eyelid triangles for cyclops mode.

        Args:
            eye: The single eye state.
        """
        h: int = self.eyelids_tired_height
        half_w: int = eye.width_current // 2
        points_left = [
            (eye.x, eye.y - 1),
            (eye.x + half_w, eye.y - 1),
            (eye.x, eye.y + h - 1),
        ]
        pygame.draw.polygon(self.surface, self.bg_color, points_left)

        points_right = [
            (eye.x + half_w, eye.y - 1),
            (eye.x + eye.width_current, eye.y - 1),
            (eye.x + eye.width_current, eye.y + h - 1),
        ]
        pygame.draw.polygon(self.surface, self.bg_color, points_right)

    def _draw_angry_eyelid_pair(self, left: EyeState, right: EyeState) -> None:
        """Draws angry eyelid triangles for both eyes in normal mode.

        Args:
            left: Left eye state.
            right: Right eye state.
        """
        h: int = self.eyelids_angry_height
        points_left = [
            (left.x, left.y - 1),
            (left.x + left.width_current, left.y - 1),
            (left.x + left.width_current, left.y + h - 1),
        ]
        pygame.draw.polygon(self.surface, self.bg_color, points_left)

        points_right = [
            (right.x, right.y - 1),
            (right.x + right.width_current, right.y - 1),
            (right.x, right.y + h - 1),
        ]
        pygame.draw.polygon(self.surface, self.bg_color, points_right)

    def _draw_angry_eyelid_cyclops(self, eye: EyeState) -> None:
        """Draws angry eyelid triangles for cyclops mode.

        Args:
            eye: The single eye state.
        """
        h: int = self.eyelids_angry_height
        half_w: int = eye.width_current // 2
        points_left = [
            (eye.x, eye.y - 1),
            (eye.x + half_w, eye.y - 1),
            (eye.x + half_w, eye.y + h - 1),
        ]
        pygame.draw.polygon(self.surface, self.bg_color, points_left)

        points_right = [
            (eye.x + half_w, eye.y - 1),
            (eye.x + eye.width_current, eye.y - 1),
            (eye.x + half_w, eye.y + h - 1),
        ]
        pygame.draw.polygon(self.surface, self.bg_color, points_right)

    def _draw_happy_eyelid(self, eye: EyeState) -> None:
        """Draws a happy eyelid arc mask on the bottom of an eye.

        Args:
            eye: The eye state to draw the happy eyelid on.
        """
        mask_h: int = self.eyelids_happy_bottom_offset + eye.border_radius_current
        mask_y: int = (eye.y + eye.height_current) - self.eyelids_happy_bottom_offset
        mask_rect = pygame.Rect(eye.x - 2, mask_y,
                                eye.width_current + 4, mask_h)
        pygame.draw.rect(self.surface, self.bg_color, mask_rect,
                         border_radius=eye.border_radius_current)


def parse_color(s: str) -> Color:
    """Parses an ``R,G,B`` string into a color tuple.

    Args:
        s: Comma-separated RGB string (e.g. ``"255,128,0"``).

    Returns:
        A ``(R, G, B)`` tuple of integers.

    Raises:
        argparse.ArgumentTypeError: If the string is not valid ``R,G,B``.
    """
    parts = s.split(",")
    if len(parts) != 3:
        raise argparse.ArgumentTypeError("Color must be R,G,B (e.g. 255,255,255)")
    r, g, b = (int(x) for x in parts)
    return (r, g, b)


def validate_color(value: Any) -> Color | None:
    """Validates a color value from UDP JSON input.

    Args:
        value: The raw value from a parsed JSON command.

    Returns:
        A valid ``(R, G, B)`` tuple, or ``None`` if validation fails.
    """
    if not isinstance(value, list) or len(value) != 3:
        return None
    if not all(isinstance(c, int) and 0 <= c <= 255 for c in value):
        return None
    return (value[0], value[1], value[2])


def handle_command(cmd: Any, robo_eyes: RoboEyes) -> None:
    """Handles a JSON command dict from UDP with input validation.

    Silently ignores malformed or unrecognized fields so that one bad
    field does not prevent the rest of the command from being processed.

    Args:
        cmd: A parsed JSON value (expected to be a dict).
        robo_eyes: The RoboEyes instance to control.
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


_help_overlay_cache: dict[tuple[int, int], pygame.Surface] = {}


def _build_help_overlay(width: int, height: int) -> pygame.Surface:
    """Builds a pre-rendered help overlay surface for the given dimensions.

    Args:
        width: Window width in pixels.
        height: Window height in pixels.

    Returns:
        A transparent surface with the help text and background drawn on it.
    """
    font_size = max(14, height // 25)
    font = pygame.font.SysFont("monospace", font_size)
    line_height = font.get_linesize()

    rendered = [font.render(line, True, (255, 255, 255)) for line in KEY_BINDINGS_LINES]
    max_width = max(s.get_width() for s in rendered)
    total_height = line_height * len(rendered)

    padding = font_size
    box_w = max_width + padding * 2
    box_h = total_height + padding * 2

    overlay = pygame.Surface((width, height), pygame.SRCALPHA)
    box_x = (width - box_w) // 2
    box_y = (height - box_h) // 2

    # Semi-transparent background
    pygame.draw.rect(overlay, (0, 0, 0, 180),
                     (box_x, box_y, box_w, box_h))

    # Draw text lines
    y = box_y + padding
    for text_surface in rendered:
        overlay.blit(text_surface, (box_x + padding, y))
        y += line_height

    return overlay


def draw_help_overlay(surface: pygame.Surface) -> None:
    """Blits the cached key bindings overlay centered on the given surface.

    The overlay is built once per window size and cached for reuse.

    Args:
        surface: The pygame surface to draw the overlay on.
    """
    size = surface.get_size()
    if size not in _help_overlay_cache:
        _help_overlay_cache[size] = _build_help_overlay(*size)
    surface.blit(_help_overlay_cache[size], (0, 0))


def setup_display(
    fullscreen: bool, width: int, height: int, rotate: int,
    bg_color: Color, eye_color: Color,
    desktop_size: tuple[int, int] | None = None,
) -> tuple[pygame.Surface, pygame.Surface, RoboEyes]:
    """Creates the window, draw surface, and RoboEyes instance.

    Args:
        fullscreen: Whether to use fullscreen mode.
        width: Base canvas width in pixels.
        height: Base canvas height in pixels.
        rotate: Rotation angle in degrees (0, 90, 180, 270).
        bg_color: Background color as (R, G, B).
        eye_color: Eye color as (R, G, B).
        desktop_size: Desktop resolution as (width, height), used for
            fullscreen. If None, queries pygame.display.Info().

    Returns:
        A tuple of (window surface, draw surface, RoboEyes instance).
    """
    if fullscreen:
        if desktop_size is None:
            info = pygame.display.Info()
            desk_w, desk_h = info.current_w, info.current_h
        else:
            desk_w, desk_h = desktop_size
        if rotate in (90, 270):
            draw_width, draw_height = desk_h, desk_w
        else:
            draw_width, draw_height = desk_w, desk_h
        window = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
    else:
        draw_width, draw_height = width, height
        if rotate in (90, 270):
            win_w, win_h = draw_height, draw_width
        else:
            win_w, win_h = draw_width, draw_height
        window = pygame.display.set_mode((win_w, win_h))

    pygame.display.set_caption("RoboEyes Simulation")
    draw_surface = pygame.Surface((draw_width, draw_height))

    robo_eyes = RoboEyes(draw_surface, width=draw_width, height=draw_height,
                         bg_color=bg_color, eye_color=eye_color)
    robo_eyes.begin()
    return window, draw_surface, robo_eyes


def main() -> None:
    """Entry point: parses arguments, starts pygame, and runs the main loop."""
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--rotate", type=int, default=0, choices=[0, 90, 180, 270],
                        help="Rotation angle in degrees (default: 0)")
    parser.add_argument("--port", type=int, default=5005,
                        help="UDP port for remote commands (default: 5005)")
    parser.add_argument("--bind", default="127.0.0.1",
                        help="Bind address for UDP (default: 127.0.0.1)")
    parser.add_argument("--color", type=parse_color, default="0,255,255",
                        help="Eye color as R,G,B (default: 0,255,255)")
    parser.add_argument("--bgcolor", type=parse_color, default="0,0,0",
                        help="Background color as R,G,B (default: 0,0,0)")
    parser.add_argument("--width", type=int, default=640,
                        help="Canvas width in pixels (default: 640)")
    parser.add_argument("--height", type=int, default=480,
                        help="Canvas height in pixels (default: 480)")
    parser.add_argument("--fullscreen", action="store_true",
                        help="Run in fullscreen mode")
    args = parser.parse_args()

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.setblocking(False)
        sock.bind((args.bind, args.port))
        print(f"Listening for commands on UDP {args.bind}:{args.port}")

        pygame.init()
        try:
            # Capture desktop resolution before first set_mode call
            info = pygame.display.Info()
            desktop_size: tuple[int, int] = (info.current_w, info.current_h)

            is_fullscreen: bool = args.fullscreen
            window, draw_surface, robo_eyes = setup_display(
                is_fullscreen, args.width, args.height, args.rotate,
                args.bgcolor, args.color, desktop_size,
            )
            robo_eyes.set_shape(Shape.DEFAULT)
            robo_eyes.set_autoblinker(True, interval=2, variation=3)
            robo_eyes.set_idle_mode(True, interval=5, variation=5)
            robo_eyes.set_curiosity(True)

            show_help: bool = False
            clock = pygame.time.Clock()

            while True:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        return
                    if event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_ESCAPE:
                            return
                        elif event.key == pygame.K_1:
                            robo_eyes.set_shape(Shape.TIRED)
                        elif event.key == pygame.K_2:
                            robo_eyes.set_shape(Shape.ANGRY)
                        elif event.key == pygame.K_3:
                            robo_eyes.set_shape(Shape.SMILE)
                        elif event.key == pygame.K_0:
                            robo_eyes.set_shape(Shape.DEFAULT)
                        elif event.key == pygame.K_4:
                            robo_eyes.set_shape(Shape.SQUINT)
                        elif event.key == pygame.K_c:
                            robo_eyes.anim_confused()
                        elif event.key == pygame.K_l:
                            robo_eyes.anim_laugh()
                        elif event.key == pygame.K_b:
                            robo_eyes.blink()
                        elif event.key == pygame.K_q:
                            robo_eyes.wink_left()
                        elif event.key == pygame.K_e:
                            robo_eyes.wink_right()
                        elif event.key == pygame.K_LEFT:
                            robo_eyes.set_position(Position.W)
                        elif event.key == pygame.K_RIGHT:
                            robo_eyes.set_position(Position.E)
                        elif event.key == pygame.K_UP:
                            robo_eyes.set_position(Position.N)
                        elif event.key == pygame.K_DOWN:
                            robo_eyes.set_position(Position.S)
                        elif event.key == pygame.K_SPACE:
                            robo_eyes.set_position(Position.CENTER)
                        elif event.key == pygame.K_f:
                            is_fullscreen = not is_fullscreen
                            _help_overlay_cache.clear()
                            # Preserve current state
                            old = robo_eyes
                            # Recreate at new resolution
                            window, draw_surface, robo_eyes = setup_display(
                                is_fullscreen, args.width, args.height,
                                args.rotate, old.bg_color, old.eye_color,
                                desktop_size,
                            )
                            # Restore state
                            robo_eyes.set_shape(old.current_shape)
                            robo_eyes.set_autoblinker(
                                old.autoblinker,
                                interval=old.blink_interval // 1000,
                                variation=old.blink_interval_variation // 1000,
                            )
                            robo_eyes.set_idle_mode(
                                old.idle,
                                interval=old.idle_interval // 1000,
                                variation=old.idle_interval_variation // 1000,
                            )
                            robo_eyes.set_curiosity(old.curious)
                            robo_eyes.set_cyclops(old.cyclops)
                        elif event.key == pygame.K_SLASH and (event.mod & pygame.KMOD_SHIFT):
                            show_help = not show_help

                # Process UDP commands (bounded per frame)
                for _ in range(MAX_UDP_MESSAGES_PER_FRAME):
                    try:
                        data, _ = sock.recvfrom(1024)
                        try:
                            cmd = json.loads(data.decode())
                            handle_command(cmd, robo_eyes)
                        except (json.JSONDecodeError, ValueError):
                            pass
                    except BlockingIOError:
                        break

                robo_eyes.update()

                if args.rotate:
                    rotated = pygame.transform.rotate(draw_surface, -args.rotate)
                    window.fill(robo_eyes.bg_color)
                    window.blit(rotated, rotated.get_rect(center=window.get_rect().center))
                else:
                    window.blit(draw_surface, (0, 0))

                if show_help:
                    draw_help_overlay(window)

                pygame.display.flip()
                clock.tick(50)
        finally:
            pygame.quit()
    finally:
        sock.close()


if __name__ == "__main__":
    main()
