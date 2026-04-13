"""Low-level drawing routines for eye shapes and eyelid overlays."""

from __future__ import annotations

import math

import pygame

from roboeyes.types import Color, EyeState


class Renderer:
    """Draws eyes and eyelid overlays onto a pygame surface."""

    def __init__(self, surface: pygame.Surface, eye_color: Color, bg_color: Color) -> None:
        self.surface = surface
        self.eye_color = eye_color
        self.bg_color = bg_color

    def draw_eye(self, eye: EyeState) -> None:
        """Draws a single rounded-rectangle eye."""
        rect = pygame.Rect(eye.x, eye.y, eye.width_current, eye.height_current)
        pygame.draw.rect(self.surface, self.eye_color, rect,
                         border_radius=max(eye.border_radius_current, 0))

    def draw_x_eye(self, eye: EyeState, direction: str = "left") -> None:
        """Draws a squint eye as a ``>`` or ``<`` shape."""
        cx = eye.x + eye.width_current // 2
        cy = eye.y + eye.height_current // 2
        sx = min(eye.width_current, eye.height_current) // 2
        sy = sx * 2 // 3
        t = max(sx // 2, 5)
        br = t // 2

        for sign in (-1, 1):
            if direction == "left":
                x1, y1 = cx - sx, cy + sign * sy
                x2, y2 = cx + sx, cy
            else:
                x1, y1 = cx + sx, cy + sign * sy
                x2, y2 = cx - sx, cy

            dx, dy = x2 - x1, y2 - y1
            length = int(math.hypot(dx, dy))
            angle = math.degrees(math.atan2(-dy, dx))

            arm = pygame.Surface((length, t), pygame.SRCALPHA)
            pygame.draw.rect(arm, self.eye_color, (0, 0, length, t), border_radius=br)

            rotated = pygame.transform.rotate(arm, angle)
            rect = rotated.get_rect(center=((x1 + x2) // 2, (y1 + y2) // 2))
            self.surface.blit(rotated, rect)

    def draw_tired_eyelid_pair(self, left: EyeState, right: EyeState, h: int) -> None:
        """Draws tired eyelid triangles for both eyes."""
        pygame.draw.polygon(self.surface, self.bg_color, [
            (left.x, left.y - 1),
            (left.x + left.width_current, left.y - 1),
            (left.x, left.y + h - 1),
        ])
        pygame.draw.polygon(self.surface, self.bg_color, [
            (right.x, right.y - 1),
            (right.x + right.width_current, right.y - 1),
            (right.x + right.width_current, right.y + h - 1),
        ])

    def draw_tired_eyelid_cyclops(self, eye: EyeState, h: int) -> None:
        """Draws tired eyelid triangles for cyclops mode."""
        half_w = eye.width_current // 2
        pygame.draw.polygon(self.surface, self.bg_color, [
            (eye.x, eye.y - 1),
            (eye.x + half_w, eye.y - 1),
            (eye.x, eye.y + h - 1),
        ])
        pygame.draw.polygon(self.surface, self.bg_color, [
            (eye.x + half_w, eye.y - 1),
            (eye.x + eye.width_current, eye.y - 1),
            (eye.x + eye.width_current, eye.y + h - 1),
        ])

    def draw_angry_eyelid_pair(self, left: EyeState, right: EyeState, h: int) -> None:
        """Draws angry eyelid triangles for both eyes."""
        pygame.draw.polygon(self.surface, self.bg_color, [
            (left.x, left.y - 1),
            (left.x + left.width_current, left.y - 1),
            (left.x + left.width_current, left.y + h - 1),
        ])
        pygame.draw.polygon(self.surface, self.bg_color, [
            (right.x, right.y - 1),
            (right.x + right.width_current, right.y - 1),
            (right.x, right.y + h - 1),
        ])

    def draw_angry_eyelid_cyclops(self, eye: EyeState, h: int) -> None:
        """Draws angry eyelid triangles for cyclops mode."""
        half_w = eye.width_current // 2
        pygame.draw.polygon(self.surface, self.bg_color, [
            (eye.x, eye.y - 1),
            (eye.x + half_w, eye.y - 1),
            (eye.x + half_w, eye.y + h - 1),
        ])
        pygame.draw.polygon(self.surface, self.bg_color, [
            (eye.x + half_w, eye.y - 1),
            (eye.x + eye.width_current, eye.y - 1),
            (eye.x + half_w, eye.y + h - 1),
        ])

    def draw_happy_eyelid(self, eye: EyeState, offset: int) -> None:
        """Draws a happy eyelid arc mask on the bottom of an eye."""
        mask_h = offset + eye.border_radius_current
        mask_y = (eye.y + eye.height_current) - offset
        mask_rect = pygame.Rect(eye.x - 2, mask_y, eye.width_current + 4, mask_h)
        pygame.draw.rect(self.surface, self.bg_color, mask_rect,
                         border_radius=eye.border_radius_current)

    def draw_sleep_eyelid(self, eye: EyeState, offset: int) -> None:
        """Draws a sleep eyelid arc mask on the top of an eye (inverted happy)."""
        mask_h = offset + eye.border_radius_current
        mask_y = eye.y - eye.border_radius_current
        mask_rect = pygame.Rect(eye.x - 2, mask_y, eye.width_current + 4, mask_h)
        pygame.draw.rect(self.surface, self.bg_color, mask_rect,
                         border_radius=eye.border_radius_current)
