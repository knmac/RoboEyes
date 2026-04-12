"""Core RoboEyes engine: state management, animation logic, and public API."""

from __future__ import annotations

import math
import random

import pygame

from roboeyes.renderer import Renderer
from roboeyes.types import (
    Color,
    DEFAULT_BGCOLOR,
    DEFAULT_MAINCOLOR,
    EyeState,
    POSITION_FACTORS,
    Position,
    Shape,
)


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
        self.surface = draw_surface
        self.screen_width = width
        self.screen_height = height
        self.bg_color = bg_color
        self.eye_color = eye_color
        self._renderer = Renderer(draw_surface, eye_color, bg_color, self)

        # Temporary color override for animations
        self.temp_color = None

        # Shape flags
        self.current_shape: Shape = Shape.DEFAULT
        self.tired = False
        self.angry = False
        self.happy = False
        self.curious = False
        self.squint = False
        self.sleep = False
        self.cyclops = False

        # Scale factor relative to reference resolution (320x240)
        self.scale = min(width / 320, height / 240)

        # Eye geometry
        self.space_between_default = int(10 * self.scale)
        self.space_between_current = self.space_between_default
        self.space_between_next = self.space_between_default

        eye_w = int(100 * self.scale)
        eye_h = int(100 * self.scale)
        border_r = int(20 * self.scale)

        self.left = EyeState(
            width_default=eye_w, height_default=eye_h,
            width_current=eye_w, height_current=1,
            width_next=eye_w, height_next=eye_h,
            border_radius_default=border_r,
            border_radius_current=border_r, border_radius_next=border_r,
        )
        self.right = EyeState(
            width_default=eye_w, height_default=eye_h,
            width_current=eye_w, height_current=1,
            width_next=eye_w, height_next=eye_h,
            border_radius_default=border_r,
            border_radius_current=border_r, border_radius_next=border_r,
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
        self.eyelids_tired_height = 0
        self.eyelids_tired_height_next = 0
        self.eyelids_angry_height = 0
        self.eyelids_angry_height_next = 0
        self.eyelids_happy_bottom_offset = 0
        self.eyelids_happy_bottom_offset_next = 0
        self.eyelids_sleep_top_offset = 0
        self.eyelids_sleep_top_offset_next = 0

        # Flicker animations
        self.h_flicker = False
        self.h_flicker_alternate = False
        self.h_flicker_amplitude = int(4 * self.scale)
        self.v_flicker = False
        self.v_flicker_alternate = False
        self.v_flicker_amplitude = int(20 * self.scale)

        # Auto-blinker
        self.autoblinker = False
        self.blink_interval = 2000
        self.blink_interval_variation = 4000
        self.blink_timer = pygame.time.get_ticks()

        # Idle mode
        self.idle = False
        self.idle_interval = 5000
        self.idle_interval_variation = 5000
        self.idle_animation_timer = pygame.time.get_ticks()

        # Wink tracking
        self._winking = False

        # Confused animation
        self.confused = False
        self.confused_animation_timer = 0
        self.confused_animation_duration = 500
        self.confused_toggle = True

        # Laugh animation
        self.laugh = False
        self.laugh_animation_timer = 0
        self.laugh_animation_duration = 500
        self.laugh_toggle = True

        # Breathing (sleep) animation
        self.breathing = False

    # -- Public API --

    def begin(self) -> None:
        """Initializes the display and starts with eyes closed."""
        self.clear_display()
        self.left.height_current = 1
        self.right.height_current = 1

    def update(self) -> None:
        """Runs one frame of the eye animation loop."""
        self._draw_eyes()

    def set_width(self, left_eye: int, right_eye: int) -> None:
        self.left.width_next = self.left.width_default = left_eye
        self.right.width_next = self.right.width_default = right_eye

    def set_height(self, left_eye: int, right_eye: int) -> None:
        self.left.height_next = self.left.height_default = left_eye
        self.right.height_next = self.right.height_default = right_eye

    def set_border_radius(self, left_eye: int, right_eye: int) -> None:
        self.left.border_radius_next = self.left.border_radius_default = left_eye
        self.right.border_radius_next = self.right.border_radius_default = right_eye

    def set_space_between(self, space: int) -> None:
        self.space_between_next = self.space_between_default = space

    def set_shape(self, shape: Shape) -> None:
        self.current_shape = shape
        self.tired = shape == Shape.DROOPY
        self.angry = shape == Shape.FROWN
        self.happy = shape == Shape.CHEERFUL
        self.squint = shape == Shape.SQUINT
        self.sleep = shape == Shape.CLOSED

    def set_position(self, position: Position) -> None:
        fx, fy = POSITION_FACTORS[position]
        self.left.x_next = int(self._screen_constraint_x() * fx)
        self.left.y_next = int(self._screen_constraint_y() * fy)

    def set_autoblinker(self, active: bool, interval: int = 2, variation: int = 4) -> None:
        self.autoblinker = active
        self.blink_interval = interval * 1000
        self.blink_interval_variation = variation * 1000

    def set_idle_mode(self, active: bool, interval: int = 5, variation: int = 5) -> None:
        self.idle = active
        self.idle_interval = interval * 1000
        self.idle_interval_variation = variation * 1000

    def set_curiosity(self, curious_bit: bool) -> None:
        self.curious = curious_bit

    def set_cyclops(self, cyclops_bit: bool) -> None:
        self.cyclops = cyclops_bit

    def set_h_flicker(self, flicker_bit: bool, amplitude: int = 4) -> None:
        self.h_flicker = flicker_bit
        self.h_flicker_amplitude = amplitude

    def set_v_flicker(self, flicker_bit: bool, amplitude: int = 20) -> None:
        self.v_flicker = flicker_bit
        self.v_flicker_amplitude = amplitude

    def close(self, left: bool = True, right: bool = True) -> None:
        if left:
            self.left.height_next = 1
            self.left.is_open = False
        if right:
            self.right.height_next = 1
            self.right.is_open = False

    def open_eyes(self, left: bool = True, right: bool = True) -> None:
        if left:
            self.left.is_open = True
        if right:
            self.right.is_open = True

    def blink(self, left: bool = True, right: bool = True) -> None:
        self.close(left, right)
        self.open_eyes(left, right)

    def wink_left(self) -> None:
        self._winking = True
        self.blink(left=True, right=False)

    def wink_right(self) -> None:
        self._winking = True
        self.blink(left=False, right=True)

    def anim_confused(self) -> None:
        self.confused = True

    def anim_laugh(self) -> None:
        self.laugh = True
        self.set_temp_color(Color(255, 100, 100))  # Temporary red tint for laugh

    def anim_sleep(self) -> None:
        """Triggers the breathing (snoring) animation with sleep shape."""
        self.set_shape(Shape.CLOSED)
        self.set_position(Position.CENTER)
        self.breathing = True

    def anim_breathing(self) -> None:
        """Toggles the breathing animation (works with any shape)."""
        self.breathing = not self.breathing

    # TODO: Add special FX animations for anime chibi style:
    # def anim_bounce(self) -> None:
    #     """Cheerful bounce effect for happy emotions (👍, ❤️, 🤩, 🥰)"""
    #     pass
    # def anim_sway(self) -> None:
    #     """Affectionate sway for love emotions (😘, ❤️, 🤗)"""
    #     pass
    # def anim_sparkle(self) -> None:
    #     """Star twinkle effect for excited emotions (👌, 🥳, 🌹)"""
    #     pass
    # def anim_wave(self) -> None:
    #     """Greeting wave effect (👋)"""
    #     pass
    # def anim_peace(self) -> None:
    #     """Victory peace sign (✌️)"""
    #     pass
    # def anim_glow(self) -> None:
    #     """Angelic halo ring effect (🌹)"""
    #     pass
    # def anim_tears(self) -> None:
    #     """Tear drops falling effect (😭)"""
    #     pass
    # def anim_dizzy(self) -> None:
    #     """Confused dizzy spin effect (💩)"""
    #     pass

    def clear_display(self) -> None:
        self.surface.fill(self.bg_color)

    # -- Private helpers --

    @staticmethod
    def _lerp(current: int, target: int) -> int:
        if current == target:
            return current
        mid = (current + target) // 2
        return target if mid == current else mid

    def _screen_constraint_x(self) -> int:
        return self.screen_width - self.left.width_current - self.space_between_current - self.right.width_current

    def _screen_constraint_y(self) -> int:
        return self.screen_height - self.left.height_default

    # Temporary color management for animations
    def set_temp_color(self, color: Color) -> None:
        """Set temporary eye color for animation. Overrides self.eye_color."""
        self.temp_color = color

    def clear_temp_color(self) -> None:
        """Clear temporary color and restore to self.eye_color."""
        self.temp_color = None

    def _update_eye_geometry(self, eye: EyeState) -> None:
        eye.height_current = self._lerp(eye.height_current, eye.height_next + eye.height_offset)
        eye.width_current = self._lerp(eye.width_current, eye.width_next)
        eye.border_radius_current = self._lerp(eye.border_radius_current, eye.border_radius_next)

        target_y = eye.y_next + (eye.height_default - eye.height_current) // 2 - eye.height_offset // 2
        eye.y = self._lerp(eye.y, target_y)
        eye.x = self._lerp(eye.x, eye.x_next)

        if eye.is_open and eye.height_current <= 1 + eye.height_offset:
            eye.height_next = eye.height_default

    def _compute_curiosity_offsets(self) -> None:
        threshold = int(20 * self.scale)
        offset = int(16 * self.scale)

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

    def _sync_renderer(self) -> None:
        """Keep renderer colors in sync with our state."""
        self._renderer.eye_color = self.eye_color
        self._renderer.bg_color = self.bg_color

    def _draw_eyes(self) -> None:
        """Main drawing routine that updates state and renders one frame."""
        current_time = pygame.time.get_ticks()
        self._sync_renderer()
        self._compute_curiosity_offsets()

        # Update geometry
        self._update_eye_geometry(self.left)
        self.right.x_next = self.left.x_next + self.left.width_current + self.space_between_current
        self.right.y_next = self.left.y_next
        self._update_eye_geometry(self.right)
        self.space_between_current = self._lerp(self.space_between_current, self.space_between_next)

        # Auto-blinker (skip during sleep shape)
        if self.autoblinker and not self.sleep and current_time >= self.blink_timer:
            self.blink()
            self.blink_timer = current_time + self.blink_interval + random.randint(0, self.blink_interval_variation)

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
                self.clear_temp_color()  # Clear temporary color after laugh animation

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
                self.clear_temp_color()  # Clear temporary color after confused animation

        # Breathing animation
        if self.breathing:
            amp = int(6 * self.scale)
            offset = int(amp * math.sin(current_time / 600.0))
            self.left.y_next = self.left.y_default + offset
            self.right.y_next = self.right.y_default + offset
            self.clear_temp_color()  # Always clear temp color for breathing

        # Idle animation
        if self.idle and current_time >= self.idle_animation_timer:
            self.left.x_next = random.randint(0, self._screen_constraint_x())
            self.left.y_next = random.randint(0, self._screen_constraint_y())
            self.idle_animation_timer = current_time + self.idle_interval + random.randint(0, self.idle_interval_variation)

        # Flicker
        if self.h_flicker:
            amp = self.h_flicker_amplitude if self.h_flicker_alternate else -self.h_flicker_amplitude
            self.left.x += amp
            self.right.x += amp
            self.h_flicker_alternate = not self.h_flicker_alternate
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
        left_blinking = self.left.height_current < self.left.height_default - 2
        right_blinking = self.right.height_current < self.right.height_default - 2
        left_use_squint = self.squint and not left_blinking
        right_use_squint = self.squint and not right_blinking

        if self._winking and left_blinking != right_blinking and not self.squint:
            left_use_squint = not left_blinking
            right_use_squint = not right_blinking
        if self._winking and not left_blinking and not right_blinking:
            self._winking = False

        # Draw eyes
        r = self._renderer
        if left_use_squint:
            r.draw_x_eye(self.left, "left")
        else:
            r.draw_eye(self.left)

        if not self.cyclops:
            if right_use_squint:
                r.draw_x_eye(self.right, "right")
            else:
                r.draw_eye(self.right)

        # Eyelid overlays (skip when squint is active)
        if not left_use_squint and not right_use_squint:
            self._draw_eyelids()

    def _draw_eyelids(self) -> None:
        r = self._renderer

        # Compute targets
        if self.tired:
            self.eyelids_tired_height_next = self.left.height_current // 2
            self.eyelids_angry_height_next = 0
        elif self.angry:
            self.eyelids_angry_height_next = self.left.height_current // 2
            self.eyelids_tired_height_next = 0
        else:
            self.eyelids_tired_height_next = 0
            self.eyelids_angry_height_next = 0

        self.eyelids_happy_bottom_offset_next = self.left.height_current * 2 // 3 if self.happy else 0
        self.eyelids_sleep_top_offset_next = self.left.height_current * 5 // 6 if self.sleep else 0

        # Tired
        self.eyelids_tired_height = self._lerp(self.eyelids_tired_height, self.eyelids_tired_height_next)
        if self.eyelids_tired_height > 0:
            if self.cyclops:
                r.draw_tired_eyelid_cyclops(self.left, self.eyelids_tired_height)
            else:
                r.draw_tired_eyelid_pair(self.left, self.right, self.eyelids_tired_height)

        # Angry
        self.eyelids_angry_height = self._lerp(self.eyelids_angry_height, self.eyelids_angry_height_next)
        if self.eyelids_angry_height > 0:
            if self.cyclops:
                r.draw_angry_eyelid_cyclops(self.left, self.eyelids_angry_height)
            else:
                r.draw_angry_eyelid_pair(self.left, self.right, self.eyelids_angry_height)

        # Happy
        self.eyelids_happy_bottom_offset = self._lerp(self.eyelids_happy_bottom_offset, self.eyelids_happy_bottom_offset_next)
        if self.eyelids_happy_bottom_offset > 0:
            r.draw_happy_eyelid(self.left, self.eyelids_happy_bottom_offset)
            if not self.cyclops:
                r.draw_happy_eyelid(self.right, self.eyelids_happy_bottom_offset)

        # Sleep
        self.eyelids_sleep_top_offset = self._lerp(self.eyelids_sleep_top_offset, self.eyelids_sleep_top_offset_next)
        if self.eyelids_sleep_top_offset > 0:
            r.draw_sleep_eyelid(self.left, self.eyelids_sleep_top_offset)
            if not self.cyclops:
                r.draw_sleep_eyelid(self.right, self.eyelids_sleep_top_offset)
